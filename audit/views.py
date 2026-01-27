from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from .models import AuditLog
from django.db.models import Q
import json
from django.http import HttpResponse
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from django.template.loader import render_to_string
from xhtml2pdf import pisa
import logging
from audit.utils import audit_log



# Add logging for debugging
logger = logging.getLogger(__name__)

def is_manager(user):
   return (user.is_staff or 
            user.groups.filter(name__in=['Manager', 'Administrator', 'Auditor']).exists())

@login_required
@user_passes_test(is_manager)
def audit_logs(request):
    """
    View all audit logs with filters
    """
    logs = AuditLog.objects.select_related('user').all()
    
    # Get filter parameters
    user_filter = request.GET.get('user', '')
    module_filter = request.GET.get('module', '')
    action_filter = request.GET.get('action', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search_query = request.GET.get('q', '')
    time_period = request.GET.get('time_period', '')
    
    # Apply time period filter if specified
    if time_period:
        today = datetime.now().date()
        if time_period == 'today':
            logs = logs.filter(timestamp__date=today)
        elif time_period == 'yesterday':
            yesterday = today - timedelta(days=1)
            logs = logs.filter(timestamp__date=yesterday)
        elif time_period == 'week':
            week_ago = today - timedelta(days=7)
            logs = logs.filter(timestamp__date__gte=week_ago)
        elif time_period == 'month':
            month_ago = today - timedelta(days=30)
            logs = logs.filter(timestamp__date__gte=month_ago)
        elif time_period == 'quarter':
            quarter_ago = today - timedelta(days=90)
            logs = logs.filter(timestamp__date__gte=quarter_ago)
        elif time_period == 'year':
            year_ago = today - timedelta(days=365)
            logs = logs.filter(timestamp__date__gte=year_ago)

    
    # Apply filters
    if user_filter:
        logs = logs.filter(user__username__icontains=user_filter)
    
    if module_filter:
        logs = logs.filter(module=module_filter)
    
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    if date_from:
        logs = logs.filter(timestamp__date__gte=date_from)
    
    if date_to:
        logs = logs.filter(timestamp__date__lte=date_to)
    
    if search_query:
        logs = logs.filter(
            Q(description__icontains=search_query) |
            Q(object_type__icontains=search_query) |
            Q(object_id__icontains=search_query)
        )
    
    # Check if PDF export is requested - SIMPLIFIED
    if 'export' in request.GET and request.GET.get('export') == 'pdf':
        return export_audit_logs_pdf_simple(request, logs)
    
    # Get summary statistics
    today_logs = logs.filter(timestamp__date=datetime.now().date()).count()
    unique_users = logs.values('user').distinct().count()
    modules_count = logs.values('module').distinct().count()
    
    # Pagination
    paginator = Paginator(logs, 50)  # 50 logs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'logs': page_obj,
        'module_choices': AuditLog.MODULE_CHOICES,
        'action_choices': AuditLog.ACTION_CHOICES,
        'filter_values': {
            'user': user_filter,
            'module': module_filter,
            'action': action_filter,
            'date_from': date_from,
            'date_to': date_to,
            'q': search_query,
            'time_period': time_period,
        },
        'today_logs': today_logs,
        'unique_users': unique_users,
        'modules_count': modules_count,
        'total_count': paginator.count,
    }
    
    return render(request, 'audit/audit_logs.html', context)

@login_required
@user_passes_test(is_manager)
def audit_log_detail(request, log_id):
    """
    View details of a specific audit log
    """
    log = get_object_or_404(AuditLog, id=log_id)
    
    # Try to format old/new values as JSON if they are JSON strings
    old_values = log.old_values
    new_values = log.new_values
    
    try:
        if old_values:
            old_values = json.loads(old_values)
    except:
        pass
    
    try:
        if new_values:
            new_values = json.loads(new_values)
    except:
        pass
    
    # Get related logs
    related_logs = AuditLog.objects.filter(
        Q(user=log.user) | 
        Q(object_type=log.object_type, object_id=log.object_id)
    ).exclude(id=log.id).order_by('-timestamp')[:5]
    
    # Get user statistics
    user_total_actions = AuditLog.objects.filter(user=log.user).count()
    user_today_actions = AuditLog.objects.filter(
        user=log.user,
        timestamp__date=datetime.now().date()
    ).count() if log.user else 0
    
    # Check if PDF download is requested - SIMPLIFIED
    if 'download' in request.GET and request.GET.get('download') == 'pdf':
        return download_audit_log_pdf_simple(request, log, old_values, new_values)
    
    context = {
        'log': log,
        'old_values': old_values,
        'new_values': new_values,
        'related_logs': related_logs,
        'user_total_actions': user_total_actions,
        'user_today_actions': user_today_actions,
    }
    
    return render(request, 'audit/audit_log_detail.html', context)

# ================= SIMPLIFIED PDF FUNCTIONS =================

def export_audit_logs_pdf_simple(request, queryset):
    """Simple and reliable PDF export for production"""
    try: 
        audit_log(
    user=request.user,
    action='EXPORT',
    module='AUDIT',
    description='Exported audit logs to PDF',
    request=request
)

        # Log for debugging
        logger.info(f"PDF export requested, {queryset.count()} records")
        
        response = HttpResponse(content_type='application/pdf')
        filename = f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Create the PDF using reportlab directly (no xhtml2pdf)
        buffer = BytesIO()
        
        # Use A4 landscape
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
        elements = []
        
        # Simple styles
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph("Audit Logs Report - Cornel Simba", styles['Title'])
        elements.append(title)
        
        # Generation date
        date_str = Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal'])
        elements.append(date_str)
        elements.append(Spacer(1, 20))
        
        # Basic table with limited columns for reliability
        data = [['Timestamp', 'User', 'Action', 'Module', 'Description']]
        
        # Limit to 100 records for performance
        for log in queryset[:100]:
            # Clean and truncate description
            desc = (log.description or '')[:80]
            if len(log.description or '') > 80:
                desc = desc + "..."
                
            data.append([
                log.timestamp.strftime('%Y-%m-%d %H:%M'),
                log.user.username[:15] if log.user else 'System',
                log.get_action_display(),
                log.get_module_display(),
                desc
            ])
        
        # Create table
        table = Table(data, colWidths=[2*inch, 1.5*inch, 1*inch, 1.5*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 20))
        
        # Footer with count
        footer = Paragraph(f"Total records found: {queryset.count()}", styles['Normal'])
        elements.append(footer)
        
        # Build PDF
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()
        
        response.write(pdf)
        logger.info(f"PDF generated successfully: {filename}")
        return response
        
    except Exception as e:
        logger.error(f"PDF export error: {str(e)}")
        # Return simple error
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)

def download_audit_log_pdf_simple(request, log, old_values, new_values):
    """Simple PDF download for single log"""
    try:
        logger.info(f"Single log PDF requested for log ID: {log.id}")
        
        response = HttpResponse(content_type='application/pdf')
        filename = f"audit_log_{log.id}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Create PDF directly with reportlab (no HTML template)
        buffer = BytesIO()
        
        # Create canvas
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, "Audit Log Details - Cornel Simba")
        
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 70, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Log details
        y_position = height - 100
        
        details = [
            f"Log ID: {log.id}",
            f"Timestamp: {log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"User: {log.user.username if log.user else 'System'}",
            f"Module: {log.get_module_display()}",
            f"Action: {log.get_action_display()}",
            f"Object Type: {log.object_type or 'N/A'}",
            f"Object ID: {log.object_id or 'N/A'}",
            f"IP Address: {log.ip_address or 'N/A'}",
            f"Browser: {log.browser_info or 'N/A'}",
        ]
        
        # Add details
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_position, "Log Information:")
        y_position -= 20
        
        c.setFont("Helvetica", 10)
        for detail in details:
            if y_position < 100:  # Check if we need new page
                c.showPage()
                y_position = height - 50
                c.setFont("Helvetica", 10)
            
            c.drawString(70, y_position, detail)
            y_position -= 15
        
        # Description
        y_position -= 10
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_position, "Description:")
        y_position -= 20
        
        c.setFont("Helvetica", 10)
        # Split description into multiple lines if too long
        desc = log.description or "No description"
        lines = []
        while len(desc) > 100:
            lines.append(desc[:100])
            desc = desc[100:]
        if desc:
            lines.append(desc)
        
        for line in lines:
            if y_position < 100:
                c.showPage()
                y_position = height - 50
                c.setFont("Helvetica", 10)
            c.drawString(70, y_position, line)
            y_position -= 15
        
        # Save PDF
        c.save()
        pdf = buffer.getvalue()
        buffer.close()
        
        response.write(pdf)
        logger.info(f"Single log PDF generated: {filename}")
        return response
        
    except Exception as e:
        logger.error(f"Single log PDF error: {str(e)}")
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)