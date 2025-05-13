import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import Document, Question

logger = logging.getLogger(__name__)

class MonitoringService:
    @staticmethod
    def track_document_upload(document):
        logger.info(f"Document uploaded: {document.id} - {document.title}")
    
    @staticmethod
    def track_question_asked(question):
        logger.info(f"Question asked: {question.id} - {question.question_text[:50]}")
    
    @staticmethod
    def generate_usage_report():
        # Daily usage stats
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        documents_uploaded = Document.objects.filter(
            upload_date__date=today
        ).count()
        
        questions_asked = Question.objects.filter(
            timestamp__date=today
        ).count()
        
        report = {
            'date': today,
            'documents_uploaded': documents_uploaded,
            'questions_asked': questions_asked,
        }
        
        logger.info(f"Daily usage report: {report}")
        return report

class Command(BaseCommand):
    help = 'Generate daily usage report'
    
    def handle(self, *args, **options):
        MonitoringService.generate_usage_report()