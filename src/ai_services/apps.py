from django.apps import AppConfig


class AiServicesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai_services'
    verbose_name = 'AI Services'
    
    def ready(self):
        # Import signals when app is ready
        pass
