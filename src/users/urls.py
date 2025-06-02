from django.urls import path, include
from . import views

# Web URLs (for /profile/)
web_urlpatterns = [
    path('', views.profile_view, name='profile'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('settings/', views.profile_settings, name='settings'),
    path('subscription/', views.subscription_view, name='subscription'),
    path('billing/', views.billing_view, name='billing'),
]

# API URLs (for /api/auth/)
api_urlpatterns = [
    # Authentication
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    
    # Profile management
    path('profile/', views.UserProfileView.as_view(), name='profile-api'),
    path('profile/update/', views.UserProfileUpdateView.as_view(), name='profile-update'),
    
    # Subscription management
    path('subscription/', views.UserSubscriptionView.as_view(), name='subscription-api'),
    path('subscription/update/', views.update_subscription, name='subscription-update'),
    path('subscription/cancel/', views.cancel_subscription, name='subscription-cancel'),
    
    # Usage statistics
    path('usage/', views.user_usage_stats, name='usage-stats'),
    
    # Settings
    path('settings/', views.UserSettingsView.as_view(), name='settings-api'),
]

urlpatterns = [
    path('', include(web_urlpatterns)),
    path('api/', include(api_urlpatterns)),
]
