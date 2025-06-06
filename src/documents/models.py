import os
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import FileExtensionValidator


def document_upload_path(instance, filename):
    """Generate upload path for documents"""
    # Create path: documents/user_id/year/month/filename
    return f"documents/{instance.user.id}/{timezone.now().year}/{timezone.now().month}/{filename}"


def audio_upload_path(instance, filename):
    """Generate upload path for audio files"""
    return f"audio/{instance.document.user.id}/{timezone.now().year}/{timezone.now().month}/{filename}"


class Document(models.Model):
    """Model for uploaded documents"""
    
    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('error', 'Error'),
    ]
    
    DOCUMENT_TYPES = [
        ('pdf', 'PDF'),
        ('docx', 'Word Document'),
        ('txt', 'Text File'),
        ('pptx', 'PowerPoint'),
    ]
    
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = ['pdf', 'docx', 'txt', 'pptx']
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # File information
    file = models.FileField(
        upload_to=document_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'docx', 'txt', 'pptx'])]
    )
    file_type = models.CharField(max_length=10, choices=DOCUMENT_TYPES)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    original_filename = models.CharField(max_length=255)
    
    # Processing status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Extracted content
    extracted_text = models.TextField(blank=True)
    text_extraction_confidence = models.FloatField(null=True, blank=True)
    page_count = models.PositiveIntegerField(null=True, blank=True)
    word_count = models.PositiveIntegerField(null=True, blank=True)
    
    # AI Summary
    summary_text = models.TextField(blank=True)
    summary_length = models.CharField(
        max_length=20,
        choices=[
            ('short', 'Short (1-2 min)'),
            ('medium', 'Medium (3-5 min)'),
            ('long', 'Long (5+ min)'),
        ],
        default='medium'
    )
    
    # Metadata
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")
    language = models.CharField(max_length=10, default='en-US')
    subject_area = models.CharField(max_length=100, blank=True)
    difficulty_level = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
        ],
        blank=True
    )
    
    # Analytics
    view_count = models.PositiveIntegerField(default=0)
    audio_play_count = models.PositiveIntegerField(default=0)
    total_questions_asked = models.PositiveIntegerField(default=0)
    average_session_duration = models.PositiveIntegerField(default=0, help_text="Average session time in seconds")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'
    
    def __str__(self):
        return f"{self.title} - {self.user.get_full_name()}"
    
    @property
    def file_size_mb(self):
        """Get file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)
    
    @property
    def processing_duration(self):
        """Get processing duration in seconds"""
        if self.processing_started_at and self.processing_completed_at:
            return (self.processing_completed_at - self.processing_started_at).total_seconds()
        return None
    
    @property
    def is_processing(self):
        """Check if document is currently being processed"""
        return self.status in ['uploaded', 'processing']
    
    @property
    def is_completed(self):
        """Check if document processing is completed"""
        return self.status == 'completed'
    
    @property
    def has_audio(self):
        """Check if document has associated audio"""
        return self.audio_summaries.filter(status='completed').exists()
    
    def increment_view_count(self):
        """Increment view count"""
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def increment_audio_play_count(self):
        """Increment audio play count"""
        self.audio_play_count += 1
        self.save(update_fields=['audio_play_count'])
    
    def increment_question_count(self):
        """Increment question count"""
        self.total_questions_asked += 1
        self.save(update_fields=['total_questions_asked'])
    
    def is_valid_file_type(self):
        """Check if file type is valid"""
        if not self.file:
            return False
        
        extension = self.file.name.split('.')[-1].lower() if '.' in self.file.name else ''
        return extension in self.ALLOWED_EXTENSIONS

    def is_valid_file_size(self):
        """Check if file size is within limits"""
        if not self.file:
            return False
        
        return self.file.size <= self.MAX_FILE_SIZE

    def clean(self):
        """Model validation"""
        from django.core.exceptions import ValidationError
        
        if self.file:
            if not self.is_valid_file_type():
                raise ValidationError('Invalid file type. Only PDF, DOCX, TXT, and PPTX files are allowed.')
            
            if not self.is_valid_file_size():
                raise ValidationError(f'File size exceeds maximum limit of {self.MAX_FILE_SIZE // (1024*1024)}MB.')
    
    def save(self, *args, **kwargs):
        """Override save to set file metadata"""
        # Set file metadata when creating new documents
        if not self.pk and self.file:
            self.original_filename = self.file.name
            self.file_size = self.file.size
            
            # Determine file type from extension
            if '.' in self.file.name:
                extension = self.file.name.split('.')[-1].lower()
                self.file_type = extension
        
        # Call parent save method explicitly
        super(Document, self).save(*args, **kwargs)


class AudioSummary(models.Model):
    """Model for AI-generated audio summaries"""
    
    STATUS_CHOICES = [
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='audio_summaries')
    
    # Audio file
    audio_file = models.FileField(upload_to=audio_upload_path)
    audio_format = models.CharField(max_length=10, default='mp3')
    audio_duration = models.PositiveIntegerField(help_text="Duration in seconds")
    audio_size = models.PositiveIntegerField(help_text="File size in bytes")
    
    # Voice settings
    voice_name = models.CharField(max_length=50, default='en-US-JennyNeural')
    speech_rate = models.CharField(max_length=20, default='medium')
    speech_pitch = models.CharField(max_length=20, default='medium')
    
    # Generation info
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='generating')
    generated_at = models.DateTimeField(auto_now_add=True)
    generation_time = models.PositiveIntegerField(null=True, blank=True, help_text="Generation time in seconds")
    
    # Azure service info
    azure_request_id = models.CharField(max_length=100, blank=True)
    azure_cost = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    
    class Meta:
        ordering = ['-generated_at']
        verbose_name = 'Audio Summary'
        verbose_name_plural = 'Audio Summaries'
    
    def __str__(self):
        return f"Audio for {self.document.title}"
    
    @property
    def audio_duration_formatted(self):
        """Get formatted duration (MM:SS)"""
        minutes, seconds = divmod(self.audio_duration, 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    @property
    def audio_size_mb(self):
        """Get audio size in MB"""
        return round(self.audio_size / (1024 * 1024), 2)


class Question(models.Model):
    """Model for user questions about documents"""
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='questions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='questions')
    
    # Question details
    question_text = models.TextField()
    answer_text = models.TextField(blank=True)
    
    # Context
    audio_timestamp = models.PositiveIntegerField(null=True, blank=True, help_text="Timestamp in audio when question was asked")
    context_snippet = models.TextField(blank=True, help_text="Relevant text snippet from document")
    
    # AI processing
    is_answered = models.BooleanField(default=False)
    answer_confidence = models.FloatField(null=True, blank=True)
    processing_time = models.PositiveIntegerField(null=True, blank=True, help_text="Time taken to answer in milliseconds")
    
    # Feedback
    user_rating = models.PositiveSmallIntegerField(
        null=True, 
        blank=True,
        choices=[(i, i) for i in range(1, 6)],
        help_text="User rating from 1 to 5"
    )
    user_feedback = models.TextField(blank=True)
    
    # Azure service info
    azure_request_id = models.CharField(max_length=100, blank=True)
    azure_cost = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    
    # Timestamps
    asked_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-asked_at']
        verbose_name = 'Question'
        verbose_name_plural = 'Questions'
    
    def __str__(self):
        return f"Q: {self.question_text[:50]}..."
    
    @property
    def response_time(self):
        """Get response time in seconds"""
        if self.asked_at and self.answered_at:
            return (self.answered_at - self.asked_at).total_seconds()
        return None


class DocumentShare(models.Model):
    """Model for sharing documents with others"""
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='shares')
    shared_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shared_documents')
    shared_with_email = models.EmailField()
    
    # Share settings
    can_view = models.BooleanField(default=True)
    can_ask_questions = models.BooleanField(default=False)
    can_download = models.BooleanField(default=False)
    
    # Share info
    share_token = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Tracking
    access_count = models.PositiveIntegerField(default=0)
    last_accessed = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['document', 'shared_with_email']
        verbose_name = 'Document Share'
        verbose_name_plural = 'Document Shares'
    
    def __str__(self):
        return f"{self.document.title} shared with {self.shared_with_email}"
    
    @property
    def is_expired(self):
        """Check if share link is expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def increment_access_count(self):
        """Increment access count and update last accessed"""
        self.access_count += 1
        self.last_accessed = timezone.now()
        self.save(update_fields=['access_count', 'last_accessed'])


class ProcessingLog(models.Model):
    """Model for tracking document processing steps"""
    
    LOG_LEVELS = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]
    
    PROCESSING_STEPS = [
        ('upload', 'File Upload'),
        ('text_extraction', 'Text Extraction'),
        ('summarization', 'AI Summarization'),
        ('audio_generation', 'Audio Generation'),
        ('completion', 'Processing Complete'),
    ]
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='processing_logs')
    step = models.CharField(max_length=20, choices=PROCESSING_STEPS)
    level = models.CharField(max_length=10, choices=LOG_LEVELS, default='info')
    message = models.TextField()
    details = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Processing Log'
        verbose_name_plural = 'Processing Logs'
    
    def __str__(self):
        return f"{self.document.title} - {self.step} - {self.level}"
