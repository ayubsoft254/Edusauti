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
        
        parser.add_argument(
            '--skip-api-calls',
            action='store_true',
            help='Skip actual API calls (only test configuration)'
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
            if not options['verbose']:
                self.stdout.write(self.style.WARNING('Use --verbose to see all configuration issues'))
            return
        
        if validation['warnings']:
            self.stdout.write(self.style.WARNING('Configuration Warnings:'))
            for warning in validation['warnings']:
                self.stdout.write(self.style.WARNING(f'  - {warning}'))
        
        service_to_test = options['service']
        verbose = options['verbose']
        skip_api_calls = options['skip_api_calls']
        
        if service_to_test in ['all', 'document']:
            self._test_document_intelligence(verbose, skip_api_calls)
        
        if service_to_test in ['all', 'openai']:
            self._test_openai_service(verbose, skip_api_calls)
        
        if service_to_test in ['all', 'speech']:
            self._test_speech_service(verbose, skip_api_calls)
        
        # Show health status
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('Service Health Status:'))
        
        try:
            health = get_service_health_status()
            
            for service, status in health.items():
                if status['status'] == 'healthy':
                    status_color = self.style.SUCCESS
                elif status['status'] == 'warning':
                    status_color = self.style.WARNING
                else:
                    status_color = self.style.ERROR
                    
                self.stdout.write(f"  {service}: {status_color(status['status'])}")
                if verbose:
                    self.stdout.write(f"    Error rate: {status['error_rate']}%")
                    self.stdout.write(f"    Requests (7d): {status['total_requests_7d']}")
                    self.stdout.write(f"    Configured: {'Yes' if status['is_configured'] else 'No'}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  Error getting health status: {e}'))
    
    def _test_document_intelligence(self, verbose, skip_api_calls):
        self.stdout.write('\nTesting Document Intelligence Service...')
        try:
            service = DocumentIntelligenceService()
            self.stdout.write(self.style.SUCCESS('  ✓ Service initialized successfully'))
            
            if verbose:
                self.stdout.write(f"  Endpoint: {service.endpoint}")
                
            if not skip_api_calls:
                # Test validation method
                try:
                    validation_result = service.validate_input(file_path="/nonexistent/file.pdf")
                    if validation_result and validation_result.get('valid', True):
                        self.stdout.write(self.style.WARNING('  ⚠ Validation should have failed for non-existent file'))
                    else:
                        self.stdout.write(self.style.SUCCESS('  ✓ Input validation working correctly'))
                except Exception:
                    self.stdout.write(self.style.SUCCESS('  ✓ Input validation working correctly'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Service initialization failed: {e}'))
            if verbose:
                import traceback
                self.stdout.write(f"  Full error: {traceback.format_exc()}")
    
    def _test_openai_service(self, verbose, skip_api_calls):
        self.stdout.write('\nTesting OpenAI Service...')
        try:
            # Check if deployment name is configured
            from django.conf import settings
            if not getattr(settings, 'AZURE_OPENAI_DEPLOYMENT_NAME', None):
                self.stdout.write(self.style.ERROR('  ✗ AZURE_OPENAI_DEPLOYMENT_NAME not configured'))
                return
                
            service = OpenAIService()
            self.stdout.write(self.style.SUCCESS('  ✓ Service initialized successfully'))
            
            if verbose:
                self.stdout.write(f"  Endpoint: {service.endpoint}")
                self.stdout.write(f"  Deployment: {service.deployment_name}")
                self.stdout.write(f"  API Version: {service.api_version}")
                
            if not skip_api_calls:
                # Test with a simple summarization
                self.stdout.write('  Testing text summarization (this will make an API call)...')
                try:
                    result = service.generate_summary(
                        text="This is a test document. It contains some sample text for testing the AI summarization service.",
                        style='simple',
                        length='short'
                    )
                    self.stdout.write(self.style.SUCCESS('  ✓ Summarization test passed'))
                    
                    if verbose:
                        self.stdout.write(f"  Summary: {result['summary'][:100]}...")
                        self.stdout.write(f"  Tokens used: {result['total_tokens']}")
                        self.stdout.write(f"  Response time: {result['response_time']:.2f}s")
                        self.stdout.write(f"  Estimated cost: ${result['estimated_cost']:.4f}")
                        
                except Exception as api_error:
                    self.stdout.write(self.style.ERROR(f'  ✗ API call failed: {api_error}'))
                    if verbose:
                        import traceback
                        self.stdout.write(f"  Full error: {traceback.format_exc()}")
            else:
                self.stdout.write('  Skipping API calls (use without --skip-api-calls to test)')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Service initialization failed: {e}'))
            if verbose:
                import traceback
                self.stdout.write(f"  Full error: {traceback.format_exc()}")
    
    def _test_speech_service(self, verbose, skip_api_calls):
        self.stdout.write('\nTesting Speech Service...')
        try:
            service = SpeechService()
            self.stdout.write(self.style.SUCCESS('  ✓ Service initialized successfully'))
            
            if verbose:
                self.stdout.write(f"  Region: {service.speech_region}")
                
            # Test getting available voices (this doesn't make API calls)
            try:
                voices = service.get_available_voices()
                self.stdout.write(self.style.SUCCESS(f'  ✓ Retrieved {len(voices)} available voices'))
                
                if verbose and voices:
                    self.stdout.write('  Available voices:')
                    for voice in voices[:3]:  # Show first 3 voices
                        self.stdout.write(f"    - {voice['name']} ({voice['gender']}) - {voice['description']}")
                    if len(voices) > 3:
                        self.stdout.write(f"    ... and {len(voices) - 3} more voices")
            except Exception as voice_error:
                self.stdout.write(self.style.WARNING(f'  ⚠ Could not get voices: {voice_error}'))
            
            if not skip_api_calls:
                # Test text-to-speech with a small sample
                self.stdout.write('  Testing text-to-speech (this will make an API call)...')
                try:
                    result = service.text_to_speech(
                        text="Hello, this is a test of the speech synthesis service.",
                        voice_name='en-US-JennyNeural'
                    )
                    self.stdout.write(self.style.SUCCESS('  ✓ Text-to-speech test passed'))
                    
                    if verbose:
                        self.stdout.write(f"  Audio duration: {result['duration']} seconds")
                        self.stdout.write(f"  Audio size: {len(result['audio_data'])} bytes")
                        self.stdout.write(f"  Estimated cost: ${result['estimated_cost']:.4f}")
                        
                except Exception as tts_error:
                    self.stdout.write(self.style.ERROR(f'  ✗ Text-to-speech failed: {tts_error}'))
            else:
                self.stdout.write('  Skipping API calls (use without --skip-api-calls to test)')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Service initialization failed: {e}'))
            if verbose:
                import traceback
                self.stdout.write(f"  Full error: {traceback.format_exc()}")