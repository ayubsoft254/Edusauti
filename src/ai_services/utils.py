import logging
from typing import Dict, Any
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .models import AIServiceUsage, AIServiceLog
from django.db import models

User = get_user_model()
logger = logging.getLogger(__name__)


def get_user_daily_usage(user, service_type: str, date=None) -> AIServiceUsage:
    """Get or create daily usage record for user and service"""
    if not date:
        date = timezone.now().date()
    
    usage, created = AIServiceUsage.objects.get_or_create(
        user=user,
        service_type=service_type,
        date=date,
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
    
    return usage


def check_service_availability(service_type: str) -> bool:
    """Check if a service is available and configured"""
    
    service_configs = {
        'document_intelligence': [
            'AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT',
            'AZURE_DOCUMENT_INTELLIGENCE_KEY'
        ],
        'openai_chat': [
            'AZURE_OPENAI_ENDPOINT',
            'AZURE_OPENAI_KEY',
            'AZURE_OPENAI_DEPLOYMENT_NAME'
        ],
        'speech_synthesis': [
            'AZURE_SPEECH_KEY',
            'AZURE_SPEECH_REGION'
        ],
        'speech_recognition': [
            'AZURE_SPEECH_KEY',
            'AZURE_SPEECH_REGION'
        ]
    }
    
    required_settings = service_configs.get(service_type, [])
    
    for setting_name in required_settings:
        if not getattr(settings, setting_name, None):
            logger.warning(f"Missing configuration for {service_type}: {setting_name}")
            return False
    
    return True


def get_service_health_status() -> Dict[str, Any]:
    """Get health status of all AI services"""
    
    services = [
        'document_intelligence',
        'openai_chat', 
        'speech_synthesis',
        'speech_recognition'
    ]
    
    health_status = {}
    
    for service in services:
        # Check configuration
        is_configured = check_service_availability(service)
        
        # Check recent error rate
        week_ago = timezone.now() - timedelta(days=7)
        recent_logs = AIServiceLog.objects.filter(
            service_type=service,
            created_at__gte=week_ago
        )
        
        total_requests = recent_logs.count()
        failed_requests = recent_logs.filter(status='failed').count()
        
        error_rate = 0
        if total_requests > 0:
            error_rate = (failed_requests / total_requests) * 100
        
        # Determine status
        if not is_configured:
            status = 'not_configured'
        elif error_rate > 10:
            status = 'degraded'
        elif error_rate > 5:
            status = 'warning'
        else:
            status = 'healthy'
        
        health_status[service] = {
            'status': status,
            'is_configured': is_configured,
            'error_rate': round(error_rate, 2),
            'total_requests_7d': total_requests,
            'failed_requests_7d': failed_requests
        }
    
    return health_status


def get_user_service_limits(user) -> Dict[str, Dict[str, int]]:
    """Get service limits based on user's subscription tier"""
    
    limits = {
        'free': {
            'document_intelligence': {'daily': 50, 'monthly': 200},
            'openai_chat': {'daily': 100, 'monthly': 500},
            'speech_synthesis': {'daily': 50, 'monthly': 200},
            'speech_recognition': {'daily': 30, 'monthly': 100},
        },
        'pro': {
            'document_intelligence': {'daily': 500, 'monthly': 5000},
            'openai_chat': {'daily': 1000, 'monthly': 10000},
            'speech_synthesis': {'daily': 500, 'monthly': 5000},
            'speech_recognition': {'daily': 300, 'monthly': 3000},
        },
        'edu': {
            'document_intelligence': {'daily': 1000, 'monthly': 15000},
            'openai_chat': {'daily': 2000, 'monthly': 25000},
            'speech_synthesis': {'daily': 1000, 'monthly': 15000},
            'speech_recognition': {'daily': 500, 'monthly': 7500},
        },
        'enterprise': {
            'document_intelligence': {'daily': 10000, 'monthly': 100000},
            'openai_chat': {'daily': 20000, 'monthly': 200000},
            'speech_synthesis': {'daily': 10000, 'monthly': 100000},
            'speech_recognition': {'daily': 5000, 'monthly': 50000},
        }
    }
    
    return limits.get(user.subscription_tier, limits['free'])


def calculate_monthly_cost(user, month=None, year=None) -> Dict[str, Any]:
    """Calculate monthly costs for a user across all services"""
    
    if not month:
        month = timezone.now().month
    if not year:
        year = timezone.now().year
    
    # Get all usage records for the month
    monthly_usage = AIServiceUsage.objects.filter(
        user=user,
        date__month=month,
        date__year=year
    )
    
    costs_by_service = {}
    total_cost = 0
    total_requests = 0
    
    for usage in monthly_usage:
        service = usage.service_type
        if service not in costs_by_service:
            costs_by_service[service] = {
                'cost': 0,
                'requests': 0,
                'tokens': 0,
                'characters': 0
            }
        
        costs_by_service[service]['cost'] += float(usage.total_cost)
        costs_by_service[service]['requests'] += usage.total_requests
        costs_by_service[service]['tokens'] += usage.total_tokens
        costs_by_service[service]['characters'] += usage.total_characters
        
        total_cost += float(usage.total_cost)
        total_requests += usage.total_requests
    
    return {
        'total_cost': round(total_cost, 4),
        'total_requests': total_requests,
        'costs_by_service': costs_by_service,
        'month': month,
        'year': year
    }


def get_service_performance_metrics(service_type: str, days: int = 7) -> Dict[str, Any]:
    """Get performance metrics for a service over the specified period"""
    
    start_date = timezone.now() - timedelta(days=days)
    
    # Get logs for the period
    logs = AIServiceLog.objects.filter(
        service_type=service_type,
        created_at__gte=start_date
    )
    
    total_requests = logs.count()
    successful_requests = logs.filter(status='success').count()
    failed_requests = logs.filter(status='failed').count()
    
    # Calculate response times
    completed_logs = logs.filter(response_time__isnull=False)
    if completed_logs.exists():
        avg_response_time = completed_logs.aggregate(
            avg_time=models.Avg('response_time')
        )['avg_time']
        
        response_times = list(completed_logs.values_list('response_time', flat=True))
        response_times.sort()
        
        # Calculate percentiles
        p50_index = int(len(response_times) * 0.5)
        p95_index = int(len(response_times) * 0.95)
        p99_index = int(len(response_times) * 0.99)
        
        p50_response_time = response_times[p50_index] if response_times else 0
        p95_response_time = response_times[p95_index] if response_times else 0
        p99_response_time = response_times[p99_index] if response_times else 0
    else:
        avg_response_time = 0
        p50_response_time = 0
        p95_response_time = 0
        p99_response_time = 0
    
    # Calculate success rate
    success_rate = 0
    if total_requests > 0:
        success_rate = (successful_requests / total_requests) * 100
    
    # Get total cost and tokens
    total_cost = logs.aggregate(
        total_cost=models.Sum('estimated_cost')
    )['total_cost'] or 0
    
    total_tokens = logs.aggregate(
        total_tokens=models.Sum('tokens_used')
    )['total_tokens'] or 0
    
    return {
        'service_type': service_type,
        'period_days': days,
        'total_requests': total_requests,
        'successful_requests': successful_requests,
        'failed_requests': failed_requests,
        'success_rate': round(success_rate, 2),
        'avg_response_time': round(avg_response_time, 2) if avg_response_time else 0,
        'p50_response_time': p50_response_time,
        'p95_response_time': p95_response_time,
        'p99_response_time': p99_response_time,
        'total_cost': float(total_cost),
        'total_tokens': total_tokens
    }


def cleanup_old_logs(days_to_keep: int = 90):
    """Clean up old AI service logs to manage database size"""
    
    cutoff_date = timezone.now() - timedelta(days=days_to_keep)
    
    # Delete old logs
    deleted_count = AIServiceLog.objects.filter(
        created_at__lt=cutoff_date
    ).delete()[0]
    
    logger.info(f"Cleaned up {deleted_count} old AI service logs older than {days_to_keep} days")
    
    return deleted_count


def validate_azure_configuration() -> Dict[str, Any]:
    """Validate that all Azure services are properly configured"""
    
    validation_results = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    # Check Document Intelligence
    if not getattr(settings, 'AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT', None):
        validation_results['errors'].append('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT not configured')
        validation_results['valid'] = False
    
    if not getattr(settings, 'AZURE_DOCUMENT_INTELLIGENCE_KEY', None):
        validation_results['errors'].append('AZURE_DOCUMENT_INTELLIGENCE_KEY not configured')
        validation_results['valid'] = False
    
    # Check OpenAI
    if not getattr(settings, 'AZURE_OPENAI_ENDPOINT', None):
        validation_results['errors'].append('AZURE_OPENAI_ENDPOINT not configured')
        validation_results['valid'] = False
    
    if not getattr(settings, 'AZURE_OPENAI_KEY', None):
        validation_results['errors'].append('AZURE_OPENAI_KEY not configured')
        validation_results['valid'] = False
    
    if not getattr(settings, 'AZURE_OPENAI_DEPLOYMENT_NAME', None):
        validation_results['warnings'].append('AZURE_OPENAI_DEPLOYMENT_NAME not configured, using default')
    
    # Check Speech Service
    if not getattr(settings, 'AZURE_SPEECH_KEY', None):
        validation_results['errors'].append('AZURE_SPEECH_KEY not configured')
        validation_results['valid'] = False
    
    if not getattr(settings, 'AZURE_SPEECH_REGION', None):
        validation_results['errors'].append('AZURE_SPEECH_REGION not configured')
        validation_results['valid'] = False
    
    return validation_results