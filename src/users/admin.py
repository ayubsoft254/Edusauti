from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import User, UserProfile, SubscriptionHistory


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model"""
    
    list_display = [
        'email', 'full_name', 'subscription_tier', 'is_subscription_active',
        'documents_uploaded_this_month', 'questions_asked_this_month',
        'is_active', 'date_joined'
    ]
    list_filter = [
        'subscription_tier', 'is_subscription_active', 'is_active',
        'date_joined', 'last_login'
    ]
    search_fields = ['email', 'first_name', 'last_name', 'organization']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        ('Personal info', {
            'fields': (
                'first_name', 'last_name', 'avatar', 'bio',
                'organization', 'role'
            )
        }),
        ('Subscription', {
            'fields': (
                'subscription_tier', 'subscription_start_date',
                'subscription_end_date', 'is_subscription_active'
            )
        }),
        ('Usage', {
            'fields': (
                'documents_uploaded_this_month', 'questions_asked_this_month',
                'last_usage_reset'
            )
        }),
        ('Preferences', {
            'fields': (
                'preferred_voice', 'preferred_language',
                'auto_play_summaries', 'email_notifications'
            )
        }),
        ('Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions'
            )
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'first_name', 'last_name',
                'password1', 'password2'
            ),
        }),
    )
    
    readonly_fields = ['date_joined', 'last_login', 'last_usage_reset']
    
    def full_name(self, obj):
        return obj.get_full_name() or obj.email
    full_name.short_description = 'Name'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile')
    
    actions = ['reset_monthly_usage', 'upgrade_to_pro', 'downgrade_to_free']
    
    def reset_monthly_usage(self, request, queryset):
        """Reset monthly usage for selected users"""
        count = 0
        for user in queryset:
            user.documents_uploaded_this_month = 0
            user.questions_asked_this_month = 0
            user.save(update_fields=['documents_uploaded_this_month', 'questions_asked_this_month'])
            count += 1
        
        self.message_user(request, f'Reset monthly usage for {count} users.')
    reset_monthly_usage.short_description = 'Reset monthly usage'
    
    def upgrade_to_pro(self, request, queryset):
        """Upgrade selected users to Pro tier"""
        count = queryset.filter(subscription_tier='free').update(
            subscription_tier='pro',
            is_subscription_active=True
        )
        self.message_user(request, f'Upgraded {count} users to Pro tier.')
    upgrade_to_pro.short_description = 'Upgrade to Pro tier'
    
    def downgrade_to_free(self, request, queryset):
        """Downgrade selected users to Free tier"""
        count = queryset.exclude(subscription_tier='free').update(
            subscription_tier='free',
            is_subscription_active=False
        )
        self.message_user(request, f'Downgraded {count} users to Free tier.')
    downgrade_to_free.short_description = 'Downgrade to Free tier'


class SubscriptionHistoryInline(admin.TabularInline):
    """Inline admin for subscription history"""
    model = SubscriptionHistory
    extra = 0
    readonly_fields = ['created_at']
    fields = ['tier', 'start_date', 'end_date', 'amount_paid', 'payment_method', 'is_active', 'created_at']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin interface for UserProfile model"""
    
    list_display = [
        'user', 'phone_number', 'country', 'timezone',
        'total_documents_processed', 'total_questions_asked',
        'created_at'
    ]
    list_filter = [
        'country', 'timezone', 'default_summary_length',
        'preferred_explanation_style', 'created_at'
    ]
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'phone_number']
    readonly_fields = [
        'total_documents_processed', 'total_questions_asked',
        'total_audio_time_listened', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Contact Information', {
            'fields': ('phone_number', 'date_of_birth', 'country', 'timezone')
        }),
        ('Learning Preferences', {
            'fields': ('default_summary_length', 'preferred_explanation_style')
        }),
        ('Analytics', {
            'fields': (
                'total_documents_processed', 'total_questions_asked',
                'total_audio_time_listened'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    inlines = [SubscriptionHistoryInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(SubscriptionHistory)
class SubscriptionHistoryAdmin(admin.ModelAdmin):
    """Admin interface for SubscriptionHistory model"""
    
    list_display = [
        'user', 'tier', 'start_date', 'end_date',
        'amount_paid', 'payment_method', 'is_active', 'created_at'
    ]
    list_filter = [
        'tier', 'payment_method', 'is_active', 'created_at', 'start_date'
    ]
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Subscription Info', {
            'fields': ('user', 'tier', 'start_date', 'end_date', 'is_active')
        }),
        ('Payment Info', {
            'fields': ('amount_paid', 'payment_method')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    actions = ['mark_as_active', 'mark_as_inactive']
    
    def mark_as_active(self, request, queryset):
        """Mark selected subscriptions as active"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'Marked {count} subscriptions as active.')
    mark_as_active.short_description = 'Mark as active'
    
    def mark_as_inactive(self, request, queryset):
        """Mark selected subscriptions as inactive"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'Marked {count} subscriptions as inactive.')
    mark_as_inactive.short_description = 'Mark as inactive'


# Custom admin site title
admin.site.site_header = 'EduSauti Admin'
admin.site.site_title = 'EduSauti Admin Portal'
admin.site.index_title = 'Welcome to EduSauti Administration'
