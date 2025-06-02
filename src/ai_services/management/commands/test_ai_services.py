from django.core.management.base import BaseCommand
from ai_services.document_intelligence import DocumentIntelligenceService
from ai_services.openai_service import OpenAIService
from ai_services.speech_service import SpeechService
from ai_services.utils import validate_azure_configuration, get_service_health_status


class Command(BaseCommand):
    help = 'Test AI services connectivity and configuration'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--service',
            type=str,
            choices=['all', 'document', 'openai', 'speech'],
            default='all',
            help='Which service to test'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing AI Services Configuration'))
        self.stdout.write('=' * 50)
        
        # Validate configuration first
        validation = validate_azure_configuration()
        if not validation['valid']:
            self.stdout.write(self.style.ERROR('Configuration Validation Failed:'))
            for error in validation['errors']:
                self.stdout.write(self.style.ERROR(f'  - {error}'))
            return
        
        if validation['warnings']:
            self.stdout.write(self.style.WARNING('Configuration Warnings:'))
            for warning in validation['warnings']:
                self.stdout.write(self.style.WARNING(f'  - {warning}'))
        
        service_to_test = options['service']
        verbose = options['verbose']
        
        if service_to_test in ['all', 'document']:
            self._test_document_intelligence(verbose)
        
        if service_to_test in ['all', 'openai']:
            self._test_openai_service(verbose)
        
        if service_to_test in ['all', 'speech']:
            self._test_speech_service(verbose)
        
        # Show health status
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('Service Health Status:'))
        health = get_service_health_status()
        
        for service, status in health.items():
            status_color = self.style.SUCCESS if status['status'] == 'healthy' else self.style.WARNING
            self.stdout.write(f"  {service}: {status_color(status['status'])}")
            if verbose:
                self.stdout.write(f"    Error rate: {status['error_rate']}%")
                self.stdout.write(f"    Requests (7d): {status['total_requests_7d']}")
    
    def _test_document_intelligence(self, verbose):
        self.stdout.write('\nTesting Document Intelligence Service...')
        try:
            service = DocumentIntelligenceService()
            self.stdout.write(self.style.SUCCESS('  ✓ Service initialized successfully'))
            
            if verbose:
                self.stdout.write(f"  Endpoint: {service.endpoint}")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Service initialization failed: {e}'))
    
    def _test_openai_service(self, verbose):
        self.stdout.write('\nTesting OpenAI Service...')
        try:
            service = OpenAIService()
            self.stdout.write(self.style.SUCCESS('  ✓ Service initialized successfully'))
            
            if verbose:
                self.stdout.write(f"  Endpoint: {service.endpoint}")
                self.stdout.write(f"  Deployment: {service.deployment_name}")
                
            # Test with a simple summarization
            self.stdout.write('  Testing text summarization...')
            result = service.generate_summary(
                text="This is a test document. It contains some sample text for testing the AI summarization service.",
                style='simple',
                length='short'
            )
            self.stdout.write(self.style.SUCCESS('  ✓ Summarization test passed'))
            
            if verbose:
                self.stdout.write(f"  Summary: {result['summary'][:100]}...")
                self.stdout.write(f"  Tokens used: {result['total_tokens']}")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Service test failed: {e}'))
    
    def _test_speech_service(self, verbose):
        self.stdout.write('\nTesting Speech Service...')
        try:
            service = SpeechService()
            self.stdout.write(self.style.SUCCESS('  ✓ Service initialized successfully'))
            
            if verbose:
                self.stdout.write(f"  Region: {service.speech_region}")
                
            # Test getting available voices
            voices = service.get_available_voices()
            self.stdout.write(self.style.SUCCESS(f'  ✓ Retrieved {len(voices)} available voices'))
            
            if verbose:
                for voice in voices[:3]:  # Show first 3 voices
                    self.stdout.write(f"    - {voice['name']} ({voice['gender']})")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Service test failed: {e}'))