import uuid
import time
from django.db import models
from django.conf import settings
from django.utils import timezone


class AIServiceLog(models.Model):
    """Log all AI service calls for monitoring and billing"""
    
    SERVICE_TYPES = [
        ('document_intelligence', 'Document Intelligence'),
        ('openai_chat', 'OpenAI Chat Completion'),
        ('openai_embedding', 'OpenAI Embeddings'),
        ('speech_synthesis', 'Speech Synthesis'),
        ('speech_recognition', 'Speech Recognition'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('timeout', 'Timeout'),
    ]
    
    # Request identification
    request_id = models.UUIDField(default=uuid.uuid4, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    service_type = models.CharField(max_length=30, choices=SERVICE_TYPES)
    
    # Request details
    endpoint = models.CharField(max_length=200)
    method = models.CharField(max_length=10, default='POST')
    request_size = models.PositiveIntegerField(help_text="Request size in bytes")
    
    # Response details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    response_size = models.PositiveIntegerField(null=True, blank=True, help_text="Response size in bytes")
    response_time = models.FloatField(null=True, blank=True)  # Make it nullable temporarily
    
    # Azure specific
    azure_request_id = models.CharField(max_length=100, blank=True)
    azure_operation_id = models.CharField(max_length=100, blank=True)
    
    # Billing and usage
    tokens_used = models.PositiveIntegerField(null=True, blank=True)
    characters_processed = models.PositiveIntegerField(null=True, blank=True)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    
    # Error handling
    error_code = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)
    
    # Metadata
    additional_data = models.JSONField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'AI Service Log'
        verbose_name_plural = 'AI Service Logs'
    
    def __str__(self):
        return f"{self.service_type} - {self.status} - {self.created_at}"
    
    def mark_completed(self, status='success', response_size=None, error_message=None):
        """Mark the log entry as completed"""
        self.status = status
        self.completed_at = timezone.now()
        if response_size:
            self.response_size = response_size
        if error_message:
            self.error_message = error_message
        
        # Calculate response time
        if self.created_at:
            self.response_time = int((self.completed_at - self.created_at).total_seconds() * 1000)
        
        self.save()
    
    @classmethod
    def log_request(cls, service_type, operation, success=True, error_message=None, **kwargs):
        """Helper method to create log entries with proper response_time"""
        return cls.objects.create(
            service_type=service_type,
            operation=operation,
            success=success,
            error_message=error_message,
            response_time=kwargs.get('response_time', 0.0),  # Default to 0.0 if not provided
            tokens_used=kwargs.get('tokens_used', 0),
            estimated_cost=kwargs.get('estimated_cost', 0.0),
            **{k: v for k, v in kwargs.items() if k not in ['response_time', 'tokens_used', 'estimated_cost']}
        )


class AIServiceUsage(models.Model):
    """Track daily usage statistics for each service"""
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    service_type = models.CharField(max_length=30, choices=AIServiceLog.SERVICE_TYPES)
    
    # Usage metrics
    total_requests = models.PositiveIntegerField(default=0)
    successful_requests = models.PositiveIntegerField(default=0)
    failed_requests = models.PositiveIntegerField(default=0)
    
    # Resource usage
    total_tokens = models.PositiveIntegerField(default=0)
    total_characters = models.PositiveIntegerField(default=0)
    total_response_time = models.PositiveIntegerField(default=0)  # in milliseconds
    
    # Cost tracking
    total_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'date', 'service_type']
        ordering = ['-date']
        verbose_name = 'AI Service Usage'
        verbose_name_plural = 'AI Service Usage'
    
    def __str__(self):
        return f"{self.user} - {self.service_type} - {self.date}"


class ServiceConfiguration(models.Model):
    """Store configuration for different AI services"""
    
    service_name = models.CharField(max_length=50, unique=True)
    endpoint_url = models.URLField()
    api_version = models.CharField(max_length=20, default='2024-02-01')
    
    # Rate limiting
    requests_per_minute = models.PositiveIntegerField(default=60)
    requests_per_day = models.PositiveIntegerField(default=1000)
    
    # Configuration settings
    default_settings = models.JSONField(default=dict)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Service Configuration'
        verbose_name_plural = 'Service Configurations'
    
    def __str__(self):
        return f"{self.service_name} - {'Active' if self.is_active else 'Inactive'}"
