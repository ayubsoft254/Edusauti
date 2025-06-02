from django.urls import path, include
from . import views

app_name = 'users'

# API URLs
api_urlpatterns = [
    # Authentication
    path('register/', views.UserRegistrationView.as_view(), name='api_register'),
    path('login/', views.UserLoginView.as_view(), name='api_login'),
    path('logout/', views.UserLogoutView.as_view(), name='api_logout'),
    
    # User Profile
    path('profile/', views.UserProfileView.as_view(), name='api_profile'),
    path('profile/details/', views.UserProfileDetailView.as_view(), name='api_profile_details'),
    path('password/change/', views.PasswordChangeView.as_view(), name='api_password_change'),
    
    # Dashboard
    path('dashboard/', views.UserDashboardView.as_view(), name='api_dashboard'),
    path('usage/', views.usage_stats, name='api_usage_stats'),
    
    # Subscriptions
    path('subscriptions/', views.SubscriptionListView.as_view(), name='api_subscriptions'),
    path('subscriptions/<int:pk>/', views.SubscriptionDetailView.as_view(), name='api_subscription_detail'),
    path('subscriptions/<int:subscription_id>/cancel/', views.cancel_subscription, name='api_cancel_subscription'),
]

# Template URLs
template_urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('pricing/', views.pricing_view, name='pricing'),
]

urlpatterns = [
    path('api/', include(api_urlpatterns)),
    path('', include(template_urlpatterns)),
]
