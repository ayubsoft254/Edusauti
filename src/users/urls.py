from django.urls import path, include
from . import views

# Web URLs
web_urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile_edit'),
    path('settings/', views.settings_view, name='settings'),
    path('subscription/', views.subscription_view, name='subscription'),
    path('subscription/upgrade/', views.upgrade_subscription, name='upgrade_subscription'),
    path('usage/', views.usage_stats_view, name='usage_stats'),
]

# API URLs
api_urlpatterns = [
    path('auth/register/', views.UserRegistrationAPIView.as_view(), name='api_register'),
    path('auth/login/', views.UserLoginAPIView.as_view(), name='api_login'),
    path('auth/logout/', views.UserLogoutAPIView.as_view(), name='api_logout'),
    path('profile/', views.UserProfileAPIView.as_view(), name='api_profile'),
    path('profile/extended/', views.ExtendedProfileAPIView.as_view(), name='api_extended_profile'),
    path('subscription/history/', views.SubscriptionHistoryAPIView.as_view(), name='api_subscription_history'),
    path('subscription/upgrade/', views.SubscriptionUpgradeAPIView.as_view(), name='api_subscription_upgrade'),
    path('usage/stats/', views.UsageStatsAPIView.as_view(), name='api_usage_stats'),
    path('auth/password/change/', views.PasswordChangeAPIView.as_view(), name='api_password_change'),
    path('account/deactivate/', views.AccountDeactivationAPIView.as_view(), name='api_account_deactivate'),
    path('limits/check/', views.check_limits_api, name='api_check_limits'),
    path('usage/increment/', views.increment_usage_api, name='api_increment_usage'),
]

urlpatterns = [
    # Include web URLs
    path('', include(web_urlpatterns)),
    
    # Include API URLs under /api/
    path('api/', include(api_urlpatterns)),
    
    # Include allauth URLs
    path('accounts/', include('allauth.urls')),
]
