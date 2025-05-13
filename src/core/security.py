from django.middleware.security import SecurityMiddleware
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class EnhancedSecurityMiddleware(SecurityMiddleware):
    def process_request(self, request):
        # Log suspicious activity
        if request.method == 'POST' and not request.user.is_authenticated:
            logger.warning(f"Unauthenticated POST request from {request.META.get('REMOTE_ADDR')}")
        
        # Add additional security headers
        response = super().process_request(request)
        if response:
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Frame-Options'] = 'DENY'
            response['X-XSS-Protection'] = '1; mode=block'
        
        return response