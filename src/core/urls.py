"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views


urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Health check endpoint
    path('health/', views.health_check, name='health-check'),
    
    # Home and landing pages
    path('', views.home, name='home'),
    path('landing/', views.landing_page, name='landing'),
    path('dashboard/', views.dashboard_redirect, name='dashboard-redirect'),
    
    # Authentication (allauth)
    path('accounts/', include('allauth.urls')),
    
    # Users app (web interface)
    path('profile/', include('users.urls')),
    
    # Documents app (web interface)
    path('documents/', include('documents.urls')),
    
    # API endpoints
    path('api/auth/', include('users.urls')),  # User API endpoints
    path('api/documents/', include('documents.urls')),  # Document API endpoints
    
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Add debug toolbar if available
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
