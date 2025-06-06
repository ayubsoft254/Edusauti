from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from ai_services.models import AIServiceLog

class Command(BaseCommand):
    help = 'Clean up old or test AI service logs'
    
    def add_arguments(self, parser):
        parser.add_argument('--test-only', action='store_true', help='Only remove test logs')
        parser.add_argument('--days', type=int, default=1, help='Remove logs older than N days')
    
    def handle(self, *args, **options):
        if options['test_only']:
            # Remove logs that look like test requests
            test_logs = AIServiceLog.objects.filter(
                request_size__lt=100,  # Small test requests
                service_type='speech_synthesis'
            )
            count = test_logs.count()
            test_logs.delete()
            self.stdout.write(f"Deleted {count} test logs")
        else:
            cutoff_date = timezone.now() - timedelta(days=options['days'])
            old_logs = AIServiceLog.objects.filter(created_at__lt=cutoff_date)
            count = old_logs.count()
            old_logs.delete()
            self.stdout.write(f"Deleted {count} logs older than {options['days']} days")