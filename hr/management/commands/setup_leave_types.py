# hr/management/commands/setup_leave_types.py
from django.core.management.base import BaseCommand
from hr.models import LeaveType

class Command(BaseCommand):
    help = 'Setup default leave types'
    
    def handle(self, *args, **kwargs):
        leave_types = [
            {'name': 'Annual Leave', 'max_days': 21, 'is_paid': True, 'requires_approval': True},
            {'name': 'Sick Leave', 'max_days': 14, 'is_paid': True, 'requires_approval': False},
            {'name': 'Bereavement Leave', 'max_days': 5, 'is_paid': True, 'requires_approval': False},
            {'name': 'Emergency Leave', 'max_days': 3, 'is_paid': True, 'requires_approval': False},
            {'name': 'Maternity Leave', 'max_days': 90, 'is_paid': True, 'requires_approval': True},
            {'name': 'Paternity Leave', 'max_days': 14, 'is_paid': True, 'requires_approval': True},
            {'name': 'Unpaid Leave', 'max_days': 0, 'is_paid': False, 'requires_approval': True},
        ]
        
        for lt in leave_types:
            obj, created = LeaveType.objects.get_or_create(
                name=lt['name'],
                defaults=lt
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created: {lt["name"]}'))
            else:
                self.stdout.write(self.style.WARNING(f'Already exists: {lt["name"]}'))