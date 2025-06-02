from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, UserProfile, Subscription


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User Admin"""
    list_display = [
        'email', 'full_name', 'subscription_tier', 'is_subscription_active',
        'documents_uploaded_this_month', 'questions_asked_this_month',
        'is_active', 'date_joined'
    ]
    list_filter = [
        'subscription_tier', 'is_subscription_active', 'is_active',
        'is_verified', 'date_joined', 'preferred_language'
    ]
    search_fields = ['email', 'first_name', 'last_name', 'organization']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {
            'fields': ('username', 'email', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'phone_number', 'organization')
        }),
        ('Preferences', {
            'fields': ('preferred_language', 'preferred_voice', 'email_notifications')
        }),
        ('Subscription', {
            'fields': (
                'subscription_tier', 'subscription_start_date', 'subscription_end_date',
                'is_subscription_active'
            )
        }),
        ('Usage Tracking', {
            'fields': (
                'documents_uploaded_this_month', 'questions_asked_this_month',
                'last_usage_reset'
            )
        }),
        ('Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser', 'is_verified',
                'groups', 'user_permissions'
            )
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ['date_joined', 'last_login', 'created_at', 'updated_at']
    
    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Full Name'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile')


class UserProfileInline(admin.StackedInline):
    """Inline admin for UserProfile"""
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = [
        'avatar', 'bio', 'institution', 'department', 'role',
        'timezone', 'allow_analytics', 'allow_marketing_emails'
    ]


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """UserProfile Admin"""
    list_display = ['user', 'institution', 'department', 'role', 'created_at']
    list_filter = ['role', 'institution', 'allow_analytics', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'institution']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Subscription Admin"""
    list_display = [
        'user', 'tier', 'amount', 'billing_cycle', 'start_date',
        'end_date', 'is_active', 'is_expired_status'
    ]
    list_filter = [
        'tier', 'is_active', 'billing_cycle', 'currency',
        'start_date', 'end_date', 'auto_renew'
    ]
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'transaction_id'
    ]
    readonly_fields = ['created_at', 'updated_at', 'is_expired']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('User & Tier', {
            'fields': ('user', 'tier')
        }),
        ('Billing', {
            'fields': ('amount', 'currency', 'billing_cycle', 'payment_method', 'transaction_id')
        }),
        ('Subscription Period', {
            'fields': ('start_date', 'end_date', 'is_active', 'auto_renew')
        }),
        ('Cancellation', {
            'fields': ('cancelled_at',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def is_expired_status(self, obj):
        if obj.is_expired:
            return format_html('<span style="color: red;">Expired</span>')
        return format_html('<span style="color: green;">Active</span>')
    is_expired_status.short_description = 'Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


# Add UserProfile inline to UserAdmin
UserAdmin.inlines = [UserProfileInline]
