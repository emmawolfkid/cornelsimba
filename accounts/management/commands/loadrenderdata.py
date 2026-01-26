from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Load database dump into deployed Render database'

    def handle(self, *args, **kwargs):
        call_command('loaddata', 'db.json')
        self.stdout.write(self.style.SUCCESS('Database loaded successfully!'))
