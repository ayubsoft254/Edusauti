from django.urls import path, include
from . import views

app_name = 'users'

# Web URLs (for /profile/)
web_urlpatterns = [
    path('', views.ProfileView.as_view(), name='profile'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('settings/', views.settings_view, name='settings'),
    path('subscription/', views.subscription_view, name='subscription'),
    path('subscription/upgrade/', views.upgrade_subscription, name='subscription-upgrade'),
    path('subscription/cancel/', views.cancel_subscription, name='subscription-cancel'),
    path('usage/', views.usage_stats_view, name='usage-stats'),
    
    # Billing URLs
    path('billing/', views.billing_view, name='billing'),
    path('billing/history/', views.billing_history_view, name='billing-history'),
    path('billing/update/', views.update_billing_info, name='update-billing'),
    path('billing/invoice/<int:invoice_id>/download/', views.download_invoice, name='download-invoice'),
]

# API URLs (for /api/auth/)
api_urlpatterns = [
    # Authentication
    path('register/', views.UserRegistrationAPIView.as_view(), name='register-api'),
    path('login/', views.UserLoginAPIView.as_view(), name='login-api'),
    path('logout/', views.UserLogoutAPIView.as_view(), name='logout-api'),
    
    # Profile management
    path('profile/', views.UserProfileAPIView.as_view(), name='profile-api'),
    path('profile/extended/', views.ExtendedProfileAPIView.as_view(), name='profile-extended-api'),
    
    # Subscription management
    path('subscription/', views.CurrentSubscriptionAPIView.as_view(), name='current-subscription-api'),
    path('subscription/history/', views.SubscriptionHistoryAPIView.as_view(), name='subscription-history-api'),
    path('subscription/upgrade/', views.SubscriptionUpgradeAPIView.as_view(), name='subscription-upgrade-api'),
    path('subscription/cancel/', views.cancel_subscription_api, name='subscription-cancel-api'),
    
    # Usage statistics
    path('usage/', views.UsageStatsAPIView.as_view(), name='usage-stats-api'),
    path('usage/check-limits/', views.check_limits_api, name='check-limits-api'),
    path('usage/increment/', views.increment_usage_api, name='increment-usage-api'),
    
    # Account management
    path('password/change/', views.PasswordChangeAPIView.as_view(), name='password-change-api'),
    path('account/deactivate/', views.AccountDeactivationAPIView.as_view(), name='account-deactivate-api'),
    
    # Billing APIs
    path('billing/', views.BillingInfoAPIView.as_view(), name='billing-info-api'),
    path('billing/history/', views.BillingHistoryAPIView.as_view(), name='billing-history-api'),
    path('billing/summary/', views.billing_summary_api, name='billing-summary-api'),
    path('billing/costs/', views.UsageCostsAPIView.as_view(), name='usage-costs-api'),
]

urlpatterns = [
    path('', include(web_urlpatterns)),
    path('api/', include(api_urlpatterns)),
]
