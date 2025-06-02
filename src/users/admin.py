from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, UserProfile, SubscriptionHistory


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = (
        'phone_number', 'date_of_birth', 'country', 'timezone',
        'default_summary_length', 'preferred_explanation_style',
        'total_documents_processed', 'total_questions_asked', 'total_audio_time_listened'
    )


class SubscriptionHistoryInline(admin.TabularInline):
    model = SubscriptionHistory
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('tier', 'start_date', 'end_date', 'amount_paid', 'payment_method', 'is_active', 'created_at')


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline, SubscriptionHistoryInline)  # Both inlines should be on User, not UserProfile
    list_display = (
        'email', 'first_name', 'last_name', 'subscription_tier', 
        'is_subscription_active', 'documents_uploaded_this_month', 
        'questions_asked_this_month', 'is_staff', 'is_active', 'date_joined'
    )
    list_filter = (
        'subscription_tier', 'is_subscription_active', 'is_staff', 
        'is_active', 'date_joined', 'last_login'
    )
    search_fields = ('email', 'first_name', 'last_name', 'organization')
    ordering = ('-date_joined',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Subscription Info', {
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
        ('Preferences', {
            'fields': (
                'preferred_voice', 'preferred_language', 'auto_play_summaries', 
                'email_notifications'
            )
        }),
        ('Profile', {
            'fields': ('avatar', 'bio', 'organization', 'role')
        }),
        ('Tracking', {
            'fields': ('last_login_ip', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'last_usage_reset')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'phone_number', 'country', 'default_summary_length', 
        'preferred_explanation_style', 'total_documents_processed', 
        'total_questions_asked'
    )
    list_filter = (
        'country', 'default_summary_length', 'preferred_explanation_style',
        'created_at'
    )
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(SubscriptionHistory)
class SubscriptionHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'tier', 'start_date', 'end_date', 'amount_paid', 
        'payment_method', 'is_active', 'created_at'
    )
    list_filter = ('tier', 'is_active', 'payment_method', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at',)
    date_hierarchy = 'start_date'


# Custom admin site title
admin.site.site_header = 'EduSauti Admin'
admin.site.site_title = 'EduSauti Admin Portal'
admin.site.index_title = 'Welcome to EduSauti Administration'
