from django.contrib import admin
from django.db.models import Count, Sum, Avg
from django.utils.html import format_html
from .models import AIServiceLog, AIServiceUsage, ServiceConfiguration


@admin.register(AIServiceLog)
class AIServiceLogAdmin(admin.ModelAdmin):
    list_display = (
        'request_id_short', 'user', 'service_type', 'status', 
        'response_time_ms', 'tokens_used', 'estimated_cost', 'created_at'
    )
    list_filter = (
        'service_type', 'status', 'created_at', 'user__subscription_tier'
    )
    search_fields = (
        'request_id', 'user__email', 'user__first_name', 'user__last_name',
        'azure_request_id', 'error_message'
    )
    readonly_fields = (
        'request_id', 'response_time', 'azure_request_id', 'azure_operation_id',
        'created_at', 'completed_at'
    )
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Request Information', {
            'fields': (
                'request_id', 'user', 'service_type', 'endpoint', 'method'
            )
        }),
        ('Request Details', {
            'fields': (
                'request_size', 'status', 'response_size', 'response_time'
            )
        }),
        ('Azure Information', {
            'fields': (
                'azure_request_id', 'azure_operation_id'
            ),
            'classes': ('collapse',)
        }),
        ('Usage & Billing', {
            'fields': (
                'tokens_used', 'characters_processed', 'estimated_cost'
            )
        }),
        ('Error Information', {
            'fields': (
                'error_code', 'error_message'
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': (
                'additional_data',
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'completed_at'
            )
        }),
    )
    
    def request_id_short(self, obj):
        return str(obj.request_id)[:8] + '...'
    request_id_short.short_description = 'Request ID'
    
    def response_time_ms(self, obj):
        if obj.response_time:
            return f"{obj.response_time}ms"
        return "-"
    response_time_ms.short_description = 'Response Time'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(AIServiceUsage)
class AIServiceUsageAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'service_type', 'date', 'total_requests', 
        'success_rate', 'total_cost', 'avg_response_time'
    )
    list_filter = (
        'service_type', 'date', 'user__subscription_tier'
    )
    search_fields = (
        'user__email', 'user__first_name', 'user__last_name'
    )
    date_hierarchy = 'date'
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'service_type', 'date')
        }),
        ('Request Statistics', {
            'fields': (
                'total_requests', 'successful_requests', 'failed_requests'
            )
        }),
        ('Resource Usage', {
            'fields': (
                'total_tokens', 'total_characters', 'total_response_time'
            )
        }),
        ('Cost Information', {
            'fields': ('total_cost',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def success_rate(self, obj):
        if obj.total_requests == 0:
            return "0%"
        rate = (obj.successful_requests / obj.total_requests) * 100
        color = 'green' if rate >= 95 else 'orange' if rate >= 90 else 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, rate
        )
    success_rate.short_description = 'Success Rate'
    
    def avg_response_time(self, obj):
        if obj.total_requests == 0:
            return "0ms"
        avg_time = obj.total_response_time / obj.total_requests
        return f"{avg_time:.0f}ms"
    avg_response_time.short_description = 'Avg Response Time'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(ServiceConfiguration)
class ServiceConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        'service_name', 'endpoint_url', 'api_version', 
        'requests_per_minute', 'requests_per_day', 'is_active'
    )
    list_filter = ('is_active', 'api_version')
    search_fields = ('service_name', 'endpoint_url')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Service Information', {
            'fields': ('service_name', 'endpoint_url', 'api_version', 'is_active')
        }),
        ('Rate Limiting', {
            'fields': ('requests_per_minute', 'requests_per_day')
        }),
        ('Configuration', {
            'fields': ('default_settings',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# Custom admin view for analytics - create a simple proxy model
class AIServiceAnalytics(AIServiceLog):
    """Proxy model for analytics view"""
    class Meta:
        proxy = True
        verbose_name = "AI Service Analytics"
        verbose_name_plural = "AI Service Analytics"


@admin.register(AIServiceAnalytics)
class AIServiceAnalyticsAdmin(admin.ModelAdmin):
    """Custom admin for viewing AI service analytics"""
    
    change_list_template = 'admin/ai_services/analytics_changelist.html'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def changelist_view(self, request, extra_context=None):
        # Get usage statistics
        from datetime import datetime, timedelta
        
        # Calculate date ranges
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Service usage by type
        service_stats = AIServiceUsage.objects.filter(
            date__gte=week_ago
        ).values('service_type').annotate(
            total_requests=Sum('total_requests'),
            total_cost=Sum('total_cost'),
            avg_success_rate=Avg('successful_requests') * 100 / Avg('total_requests')
        ).order_by('-total_requests')
        
        # Top users by usage
        top_users = AIServiceUsage.objects.filter(
            date__gte=week_ago
        ).values(
            'user__email', 'user__subscription_tier'
        ).annotate(
            total_requests=Sum('total_requests'),
            total_cost=Sum('total_cost')
        ).order_by('-total_requests')[:10]
        
        # Error analysis
        error_stats = AIServiceLog.objects.filter(
            created_at__gte=week_ago,
            status='failed'
        ).values('service_type', 'error_code').annotate(
            error_count=Count('id')
        ).order_by('-error_count')
        
        # Daily trends
        daily_stats = AIServiceUsage.objects.filter(
            date__gte=week_ago
        ).values('date').annotate(
            total_requests=Sum('total_requests'),
            total_cost=Sum('total_cost')
        ).order_by('date')
        
        extra_context = extra_context or {}
        extra_context.update({
            'service_stats': service_stats,
            'top_users': top_users,
            'error_stats': error_stats,
            'daily_stats': daily_stats,
        })
        
        return super().changelist_view(request, extra_context=extra_context)
