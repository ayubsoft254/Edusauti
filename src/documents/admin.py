from django.contrib import admin
from .models import Document, AudioSummary, Question, DocumentShare, ProcessingLog


class AudioSummaryInline(admin.TabularInline):
    model = AudioSummary
    extra = 0
    readonly_fields = ('generated_at', 'generation_time', 'azure_request_id', 'azure_cost')
    fields = ('audio_file', 'voice_name', 'speech_rate', 'status', 'audio_duration', 'generated_at')


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    readonly_fields = ('asked_at', 'answered_at', 'processing_time')
    fields = ('user', 'question_text', 'is_answered', 'user_rating', 'asked_at')


class ProcessingLogInline(admin.TabularInline):
    model = ProcessingLog
    extra = 0
    readonly_fields = ('timestamp',)
    fields = ('step', 'level', 'message', 'timestamp')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    inlines = [AudioSummaryInline, QuestionInline, ProcessingLogInline]
    list_display = (
        'title', 'user', 'file_type', 'status', 'file_size_mb', 
        'view_count', 'audio_play_count', 'total_questions_asked', 'created_at'
    )
    list_filter = (
        'status', 'file_type', 'summary_length', 'difficulty_level', 
        'language', 'created_at'
    )
    search_fields = ('title', 'user__email', 'user__first_name', 'user__last_name', 'tags')
    readonly_fields = (
        'file_size', 'original_filename', 'processing_started_at', 'processing_completed_at',
        'extracted_text', 'text_extraction_confidence', 'page_count', 'word_count',
        'summary_text', 'view_count', 'audio_play_count', 'total_questions_asked',
        'average_session_duration', 'created_at', 'updated_at'
    )
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'title', 'description', 'file', 'original_filename', 'file_type', 'file_size')
        }),
        ('Processing Status', {
            'fields': ('status', 'processing_started_at', 'processing_completed_at', 'error_message')
        }),
        ('Extracted Content', {
            'fields': ('extracted_text', 'text_extraction_confidence', 'page_count', 'word_count'),
            'classes': ('collapse',)
        }),
        ('AI Summary', {
            'fields': ('summary_text', 'summary_length'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('tags', 'language', 'subject_area', 'difficulty_level')
        }),
        ('Analytics', {
            'fields': ('view_count', 'audio_play_count', 'total_questions_asked', 'average_session_duration')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def file_size_mb(self, obj):
        return obj.file_size_mb
    file_size_mb.short_description = 'File Size (MB)'


@admin.register(AudioSummary)
class AudioSummaryAdmin(admin.ModelAdmin):
    list_display = (
        'document', 'voice_name', 'status', 'audio_duration_formatted', 
        'audio_size_mb', 'generated_at'
    )
    list_filter = ('status', 'voice_name', 'audio_format', 'generated_at')
    search_fields = ('document__title', 'document__user__email')
    readonly_fields = (
        'audio_duration', 'audio_size', 'generated_at', 'generation_time',
        'azure_request_id', 'azure_cost'
    )
    
    def audio_duration_formatted(self, obj):
        return obj.audio_duration_formatted
    audio_duration_formatted.short_description = 'Duration'
    
    def audio_size_mb(self, obj):
        return obj.audio_size_mb
    audio_size_mb.short_description = 'Size (MB)'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        'question_text_short', 'document', 'user', 'is_answered', 
        'user_rating', 'asked_at'
    )
    list_filter = ('is_answered', 'user_rating', 'asked_at')
    search_fields = ('question_text', 'document__title', 'user__email')
    readonly_fields = (
        'asked_at', 'answered_at', 'processing_time', 'answer_confidence',
        'azure_request_id', 'azure_cost'
    )
    fieldsets = (
        ('Question Details', {
            'fields': ('document', 'user', 'question_text', 'audio_timestamp')
        }),
        ('Answer', {
            'fields': ('answer_text', 'context_snippet', 'is_answered', 'answer_confidence')
        }),
        ('Feedback', {
            'fields': ('user_rating', 'user_feedback')
        }),
        ('Technical Info', {
            'fields': ('processing_time', 'azure_request_id', 'azure_cost'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('asked_at', 'answered_at'),
            'classes': ('collapse',)
        }),
    )
    
    def question_text_short(self, obj):
        return obj.question_text[:50] + "..." if len(obj.question_text) > 50 else obj.question_text
    question_text_short.short_description = 'Question'


@admin.register(DocumentShare)
class DocumentShareAdmin(admin.ModelAdmin):
    list_display = (
        'document', 'shared_with_email', 'shared_by', 'can_view', 
        'can_ask_questions', 'is_active', 'access_count', 'created_at'
    )
    list_filter = ('can_view', 'can_ask_questions', 'can_download', 'is_active', 'created_at')
    search_fields = ('document__title', 'shared_with_email', 'shared_by__email')
    readonly_fields = ('share_token', 'access_count', 'last_accessed', 'created_at')


@admin.register(ProcessingLog)
class ProcessingLogAdmin(admin.ModelAdmin):
    list_display = ('document', 'step', 'level', 'message_short', 'timestamp')
    list_filter = ('step', 'level', 'timestamp')
    search_fields = ('document__title', 'message')
    readonly_fields = ('timestamp',)
    
    def message_short(self, obj):
        return obj.message[:100] + "..." if len(obj.message) > 100 else obj.message
    message_short.short_description = 'Message'
