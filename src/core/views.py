from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


def home(request):
    """Home page view"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'home.html')


def landing_page(request):
    """Landing page with features and pricing"""
    return render(request, 'landing.html')


@login_required
def dashboard_redirect(request):
    """Redirect to appropriate dashboard based on user type"""
    user = request.user
    context = {
        'user': user,
    }
    return redirect('dashboard', context)


def health_check(request):
    """Health check endpoint for Docker and load balancers"""
    status = {
        'status': 'healthy',
        'database': 'unknown',
        'redis': 'unknown',
        'services': []
    }
    
    try:
        # Check database connection (SQLite)
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            status['database'] = 'healthy'
            status['services'].append('database')
    except Exception as e:
        status['database'] = 'unhealthy'
        status['status'] = 'unhealthy'
        logger.error(f"Database health check failed: {e}")
    
    try:
        # Check Redis connection
        cache.set('health_check', 'test', 30)
        if cache.get('health_check') == 'test':
            status['redis'] = 'healthy'
            status['services'].append('redis')
        else:
            status['redis'] = 'unhealthy'
            status['status'] = 'unhealthy'
    except Exception as e:
        status['redis'] = 'unhealthy'
        status['status'] = 'unhealthy'
        logger.error(f"Redis health check failed: {e}")
    
    http_status = 200 if status['status'] == 'healthy' else 503
    return JsonResponse(status, status=http_status)