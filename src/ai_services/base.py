import logging
from abc import ABC, abstractmethod
from django.utils import timezone
from .models import AIServiceLog, AIServiceUsage

logger = logging.getLogger(__name__)


class BaseAIService(ABC):
    """Base class for all AI services"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.service_type = self.get_service_type()
    
    @abstractmethod
    def get_service_type(self) -> str:
        """Return the service type identifier"""
        pass
    
    def create_log_entry(self, user=None, endpoint='', method='POST', request_size=0, **kwargs) -> AIServiceLog:
        """Create a new log entry for the service call"""
        return AIServiceLog.objects.create(
            user=user,
            service_type=self.service_type,
            endpoint=endpoint,
            method=method,
            request_size=request_size,
            **kwargs
        )
    
    def update_usage_stats(self, user, tokens=0, characters=0, cost=0, success=True):
        """Update daily usage statistics"""
        if not user:
            return
        
        today = timezone.now().date()
        usage, created = AIServiceUsage.objects.get_or_create(
            user=user,
            date=today,
            service_type=self.service_type,
            defaults={
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'total_tokens': 0,
                'total_characters': 0,
                'total_response_time': 0,
                'total_cost': 0,
            }
        )
        
        # Update counters
        usage.total_requests += 1
        if success:
            usage.successful_requests += 1
        else:
            usage.failed_requests += 1
        
        usage.total_tokens += tokens
        usage.total_characters += characters
        usage.total_cost += cost
        
        usage.save()
    
    def check_rate_limits(self, user) -> bool:
        """Check if user has exceeded rate limits"""
        if not user:
            return True
        
        today = timezone.now().date()
        try:
            usage = AIServiceUsage.objects.get(
                user=user,
                date=today,
                service_type=self.service_type
            )
            
            # Check daily limits based on subscription tier
            daily_limits = {
                'free': 50,
                'pro': 500,
                'edu': 1000,
                'enterprise': 10000,
            }
            
            limit = daily_limits.get(user.subscription_tier, 50)
            return usage.total_requests < limit
            
        except AIServiceUsage.DoesNotExist:
            return True
    
    def estimate_cost(self, tokens=0, characters=0, **kwargs) -> float:
        """Estimate the cost for the operation"""
        # Override in subclasses with service-specific pricing
        return 0.0
    
    def handle_error(self, log_entry: AIServiceLog, error: Exception, error_code: str = None):
        """Handle and log errors consistently"""
        error_message = str(error)
        self.logger.error(f"{self.service_type} error: {error_message}")
        
        log_entry.mark_completed(
            status='failed',
            error_message=error_message
        )
        
        if error_code:
            log_entry.error_code = error_code
            log_entry.save()
    
    def validate_input(self, **kwargs) -> bool:
        """Validate input parameters"""
        # Override in subclasses for service-specific validation
        return True


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded"""
    pass


class ServiceUnavailable(Exception):
    """Exception raised when service is unavailable"""
    pass


class InvalidInput(Exception):
    """Exception raised when input validation fails"""
    pass