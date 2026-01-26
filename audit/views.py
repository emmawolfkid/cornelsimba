from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from .models import AuditLog
from django.db.models import Q
import json
from django.http import HttpResponse
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from django.db.models import Count
from django.utils.timezone import now
from datetime import timedelta
import tempfile


def is_manager(user):
   return (user.is_staff or 
            user.groups.filter(name__in=['Manager', 'Administrator', 'Auditor']).exists())

@login_required
@user_passes_test(is_manager)
def audit_logs(request):
    """
    View all audit logs with filters
    """
    logs = AuditLog.objects.all()
    
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
    
    # Check if PDF export is requested
    if 'export' in request.GET and request.GET.get('export') == 'pdf':
        return export_audit_logs_pdf(request, logs)
    
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
    
    # Check if PDF download is requested
    if 'download' in request.GET and request.GET.get('download') == 'pdf':
        return download_audit_log_pdf(request, log, old_values, new_values)
    
    context = {
        'log': log,
        'old_values': old_values,
        'new_values': new_values,
        'related_logs': related_logs,
        'user_total_actions': user_total_actions,
        'user_today_actions': user_today_actions,
    }
    
    return render(request, 'audit/audit_log_detail.html', context)

def export_audit_logs_pdf(request, queryset):
    """Export audit logs to PDF with filters preserved"""
    response = HttpResponse(content_type='application/pdf')
    filename = f"audit_logs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Get filter parameters for the PDF header
    user_filter = request.GET.get('user', '')
    module_filter = request.GET.get('module', '')
    action_filter = request.GET.get('action', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    time_period = request.GET.get('time_period', '')
    
    # Create the PDF object
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=20,
        alignment=1  # Center aligned
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=15,
        alignment=1
    )
    filter_style = ParagraphStyle(
        'FilterStyle',
        parent=styles['Normal'],
        fontSize=9,
        spaceAfter=10,
        alignment=0
    )
    
    # Add title
    elements.append(Paragraph("Audit Logs Export - Cornel Simba", title_style))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", subtitle_style))
    
    # Add filter information
    filter_info = []
    if time_period:
        period_map = {
            'today': 'Today',
            'yesterday': 'Yesterday',
            'week': 'Last 7 days',
            'month': 'Last 30 days',
            'quarter': 'Last 90 days',
            'year': 'Last 365 days'
        }
        filter_info.append(f"Time Period: {period_map.get(time_period, time_period)}")
    if user_filter:
        filter_info.append(f"User: {user_filter}")
    if module_filter:
        filter_info.append(f"Module: {module_filter}")
    if action_filter:
        filter_info.append(f"Action: {action_filter}")
    if date_from:
        filter_info.append(f"From: {date_from}")
    if date_to:
        filter_info.append(f"To: {date_to}")
    
    if filter_info:
        elements.append(Paragraph("Filters Applied: " + " | ".join(filter_info), filter_style))
    
    elements.append(Spacer(1, 0.2*inch))
    
    # Prepare table data
    data = [['ID', 'Date & Time', 'User', 'Action', 'Module', 'Object Type', 'Object ID', 'Description', 'IP Address']]
    
    for log in queryset:
        data.append([
            str(log.id),
            log.timestamp.strftime('%Y-%m-%d %H:%M'),
            log.user.username if log.user else 'System',
            log.get_action_display(),
            log.get_module_display(),
            log.object_type or '-',
            str(log.object_id) if log.object_id else '-',
            (log.description or '-')[:50] + '...' if len(log.description or '') > 50 else (log.description or '-'),
            log.ip_address or '-'
        ])
    
    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph(f"Total Records: {queryset.count()}", styles['Normal']))
    elements.append(Paragraph(f"Page 1 of 1", styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    
    response.write(pdf)
    return response

def download_audit_log_pdf(request, log, old_values, new_values):
    """
    Safe PDF download for single audit log.
    Ensures ReportLab only gets strings, no dicts or objects.
    """

    response = HttpResponse(content_type='application/pdf')
    filename = f"audit_log_{log.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph(f"Audit Log Detail - Cornel Simba", styles['Heading1']))
    elements.append(Spacer(1, 12))

    # Log basic info
    basic_info = [
        f"<b>Log ID:</b> {log.id}",
        f"<b>Date:</b> {log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
        f"<b>User:</b> {log.user.username if log.user else 'System'}",
        f"<b>Action:</b> {log.get_action_display()}",
        f"<b>Module:</b> {log.get_module_display()}",
        f"<b>Object Type:</b> {log.object_type or '-'}",
        f"<b>Object ID:</b> {str(log.object_id) if log.object_id else '-'}",
        f"<b>IP Address:</b> {log.ip_address or '-'}",
        f"<b>Description:</b> {log.description or '-'}",
    ]
    for info in basic_info:
        elements.append(Paragraph(info, styles['Normal']))
        elements.append(Spacer(1, 6))

    # Old values
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("<b>Old Values:</b>", styles['Heading2']))
    if old_values:
        try:
            old_text = json.dumps(old_values, indent=2) if isinstance(old_values, dict) else str(old_values)
        except:
            old_text = str(old_values)
    else:
        old_text = "-"
    elements.append(Paragraph(old_text.replace('\n', '<br/>'), styles['Normal']))

    # New values
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("<b>New Values:</b>", styles['Heading2']))
    if new_values:
        try:
            new_text = json.dumps(new_values, indent=2) if isinstance(new_values, dict) else str(new_values)
        except:
            new_text = str(new_values)
    else:
        new_text = "-"
    elements.append(Paragraph(new_text.replace('\n', '<br/>'), styles['Normal']))

    # Footer
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Italic']))

    try:
        doc.build(elements)
    except Exception as e:
        # Debugging: write error to response (remove in production)
        response = HttpResponse(f"PDF generation failed: {e}", content_type='text/plain')
        return response

    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response