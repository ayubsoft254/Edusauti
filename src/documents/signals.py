import os
import logging
from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.core.files.storage import default_storage
from .models import Document, AudioSummary, Question, ProcessingLog

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Document)
def document_post_save(sender, instance, created, **kwargs):
    """Handle document creation and updates"""
    
    if created:
        # Log document upload
        ProcessingLog.objects.create(
            document=instance,
            step='upload',
            level='info',
            message=f'Document "{instance.title}" uploaded successfully',
            details={
                'file_size': instance.file_size,
                'file_type': instance.file_type,
                'original_filename': instance.original_filename
            }
        )
        
        # Start processing pipeline
        from .tasks import process_document_pipeline
        
        # Update status to processing
        instance.status = 'processing'
        instance.processing_started_at = timezone.now()
        instance.save(update_fields=['status', 'processing_started_at'])
        
        # Trigger async processing (assuming Celery is set up)
        try:
            process_document_pipeline.delay(instance.id)
            logger.info(f"Started processing pipeline for document {instance.id}")
        except Exception as e:
            logger.error(f"Failed to start processing pipeline for document {instance.id}: {str(e)}")
            # Update status to failed if we can't start processing
            instance.status = 'failed'
            instance.error_message = f"Failed to start processing: {str(e)}"
            instance.save(update_fields=['status', 'error_message'])
            
            ProcessingLog.objects.create(
                document=instance,
                step='upload',
                level='error',
                message=f'Failed to start processing pipeline: {str(e)}'
            )
    
    # Handle status changes
    if not created and 'status' in getattr(instance, '_dirty_fields', []):
        old_status = getattr(instance, '_original_status', None)
        new_status = instance.status
        
        if old_status != new_status:
            ProcessingLog.objects.create(
                document=instance,
                step='completion' if new_status == 'completed' else 'processing',
                level='info' if new_status == 'completed' else 'warning' if new_status == 'failed' else 'info',
                message=f'Document status changed from {old_status} to {new_status}'
            )
            
            # If processing completed, log completion time
            if new_status == 'completed' and instance.processing_completed_at:
                processing_duration = instance.processing_duration
                ProcessingLog.objects.create(
                    document=instance,
                    step='completion',
                    level='info',
                    message=f'Document processing completed in {processing_duration:.2f} seconds',
                    details={
                        'processing_duration': processing_duration,
                        'word_count': instance.word_count,
                        'page_count': instance.page_count
                    }
                )


@receiver(pre_delete, sender=Document)
def document_pre_delete(sender, instance, **kwargs):
    """Handle document deletion - cleanup files"""
    
    # Store file paths for cleanup
    files_to_delete = []
    
    # Add main document file
    if instance.file:
        files_to_delete.append(instance.file.path)
    
    # Add associated audio files
    for audio_summary in instance.audio_summaries.all():
        if audio_summary.audio_file:
            files_to_delete.append(audio_summary.audio_file.path)
    
    # Store files for post_delete cleanup
    instance._files_to_delete = files_to_delete
    
    # Log deletion
    ProcessingLog.objects.create(
        document=instance,
        step='completion',
        level='info',
        message=f'Document "{instance.title}" is being deleted',
        details={
            'files_to_delete': len(files_to_delete),
            'questions_count': instance.questions.count(),
            'shares_count': instance.shares.count()
        }
    )


@receiver(post_delete, sender=Document)
def document_post_delete(sender, instance, **kwargs):
    """Cleanup files after document deletion"""
    
    files_to_delete = getattr(instance, '_files_to_delete', [])
    
    for file_path in files_to_delete:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {str(e)}")


@receiver(post_save, sender=AudioSummary)
def audio_summary_post_save(sender, instance, created, **kwargs):
    """Handle audio summary creation and updates"""
    
    if created:
        ProcessingLog.objects.create(
            document=instance.document,
            step='audio_generation',
            level='info',
            message=f'Audio summary generation started with voice "{instance.voice_name}"',
            details={
                'voice_name': instance.voice_name,
                'speech_rate': instance.speech_rate,
                'speech_pitch': instance.speech_pitch
            }
        )
    
    # Handle status changes
    if not created and hasattr(instance, '_dirty_fields') and 'status' in instance._dirty_fields:
        old_status = getattr(instance, '_original_status', None)
        new_status = instance.status
        
        if old_status != new_status:
            if new_status == 'completed':
                ProcessingLog.objects.create(
                    document=instance.document,
                    step='audio_generation',
                    level='info',
                    message=f'Audio summary generated successfully in {instance.generation_time}s',
                    details={
                        'audio_duration': instance.audio_duration,
                        'audio_size': instance.audio_size,
                        'generation_time': instance.generation_time,
                        'azure_cost': float(instance.azure_cost) if instance.azure_cost else None
                    }
                )
                
                # Send notification to user (if notification system is implemented)
                from .utils import send_audio_ready_notification
                try:
                    send_audio_ready_notification(instance.document.user, instance.document)
                except Exception as e:
                    logger.error(f"Failed to send audio ready notification: {str(e)}")
                    
            elif new_status == 'failed':
                ProcessingLog.objects.create(
                    document=instance.document,
                    step='audio_generation',
                    level='error',
                    message=f'Audio summary generation failed'
                )


@receiver(pre_delete, sender=AudioSummary)
def audio_summary_pre_delete(sender, instance, **kwargs):
    """Handle audio summary deletion - cleanup audio file"""
    if instance.audio_file:
        instance._audio_file_path = instance.audio_file.path


@receiver(post_delete, sender=AudioSummary)
def audio_summary_post_delete(sender, instance, **kwargs):
    """Cleanup audio file after deletion"""
    audio_file_path = getattr(instance, '_audio_file_path', None)
    
    if audio_file_path:
        try:
            if os.path.exists(audio_file_path):
                os.remove(audio_file_path)
                logger.info(f"Deleted audio file: {audio_file_path}")
        except Exception as e:
            logger.error(f"Failed to delete audio file {audio_file_path}: {str(e)}")


@receiver(post_save, sender=Question)
def question_post_save(sender, instance, created, **kwargs):
    """Handle question creation and updates"""
    
    if created:
        # Log question creation
        ProcessingLog.objects.create(
            document=instance.document,
            step='completion',
            level='info',
            message=f'New question asked by {instance.user.get_full_name()}',
            details={
                'question_preview': instance.question_text[:100],
                'audio_timestamp': instance.audio_timestamp,
                'user_id': instance.user.id
            }
        )
        
        # Trigger AI processing for the question
        from .tasks import process_question
        
        try:
            process_question.delay(instance.id)
            logger.info(f"Started processing question {instance.id}")
        except Exception as e:
            logger.error(f"Failed to start question processing for question {instance.id}: {str(e)}")
    
    # Handle answer completion
    if not created and hasattr(instance, '_dirty_fields') and 'is_answered' in instance._dirty_fields:
        if instance.is_answered and instance.answer_text:
            ProcessingLog.objects.create(
                document=instance.document,
                step='completion',
                level='info',
                message=f'Question answered in {instance.processing_time}ms with confidence {instance.answer_confidence}',
                details={
                    'processing_time': instance.processing_time,
                    'answer_confidence': instance.answer_confidence,
                    'answer_preview': instance.answer_text[:100],
                    'azure_cost': float(instance.azure_cost) if instance.azure_cost else None
                }
            )
            
            # Convert answer to speech if user has premium features
            if instance.user.has_premium_features:
                from .tasks import generate_answer_audio
                try:
                    generate_answer_audio.delay(instance.id)
                except Exception as e:
                    logger.error(f"Failed to generate answer audio for question {instance.id}: {str(e)}")


# Signal to track field changes for status updates
@receiver(post_save)
def track_field_changes(sender, instance, **kwargs):
    """Generic signal to track field changes"""
    
    # Only track specific models
    if sender not in [Document, AudioSummary, Question]:
        return
    
    # Store original values for comparison in next save
    if hasattr(instance, 'pk') and instance.pk:
        try:
            original = sender.objects.get(pk=instance.pk)
            
            # Track status changes for Document
            if sender == Document:
                instance._original_status = original.status
            elif sender == AudioSummary:
                instance._original_status = original.status
                
        except sender.DoesNotExist:
            pass


# Model change tracking for better signal handling
def __init__(self, *args, **kwargs):
    """Override model __init__ to track field changes"""
    super().__init__(*args, **kwargs)
    self._original_values = {}
    
    if self.pk:
        for field in self._meta.fields:
            self._original_values[field.name] = getattr(self, field.name)


def save(self, *args, **kwargs):
    """Override model save to track dirty fields"""
    if self.pk:
        self._dirty_fields = []
        for field in self._meta.fields:
            original_value = self._original_values.get(field.name)
            current_value = getattr(self, field.name)
            
            if original_value != current_value:
                self._dirty_fields.append(field.name)
    
    super().save(*args, **kwargs)


# Add methods to models (monkey patching - better to do this in models.py)
Document.__init__ = __init__
Document.save = save
AudioSummary.__init__ = __init__
AudioSummary.save = save
Question.__init__ = __init__
Question.save = save


# User analytics update signals
@receiver(post_save, sender=Document)
def update_user_analytics(sender, instance, created, **kwargs):
    """Update user profile analytics when documents are processed"""
    
    if instance.status == 'completed' and hasattr(instance.user, 'profile'):
        profile = instance.user.profile
        profile.total_documents_processed = Document.objects.filter(
            user=instance.user, 
            status='completed'
        ).count()
        profile.save(update_fields=['total_documents_processed'])


@receiver(post_save, sender=Question)
def update_question_analytics(sender, instance, created, **kwargs):
    """Update user analytics when questions are asked"""
    
    if created and hasattr(instance.user, 'profile'):
        profile = instance.user.profile
        profile.total_questions_asked = Question.objects.filter(
            user=instance.user
        ).count()
        profile.save(update_fields=['total_questions_asked'])


@receiver(post_save, sender=AudioSummary)
def update_audio_analytics(sender, instance, **kwargs):
    """Update audio listening analytics"""
    
    if instance.status == 'completed' and hasattr(instance.document.user, 'profile'):
        profile = instance.document.user.profile
        
        # Calculate total audio time available
        total_audio_time = AudioSummary.objects.filter(
            document__user=instance.document.user,
            status='completed'
        ).aggregate(
            total_duration=models.Sum('audio_duration')
        )['total_duration'] or 0
        
        profile.total_audio_time_listened = total_audio_time
        profile.save(update_fields=['total_audio_time_listened'])


# Cleanup signals for orphaned files
@receiver(post_save, sender=Document)
def cleanup_failed_documents(sender, instance, **kwargs):
    """Cleanup documents that have been in processing state too long"""
    
    if instance.status == 'processing' and instance.processing_started_at:
        # Check if processing has been running for more than 30 minutes
        processing_time = timezone.now() - instance.processing_started_at
        
        if processing_time.total_seconds() > 1800:  # 30 minutes
            instance.status = 'failed'
            instance.error_message = 'Processing timeout - operation took too long'
            instance.save(update_fields=['status', 'error_message'])
            
            ProcessingLog.objects.create(
                document=instance,
                step='processing',
                level='error',
                message='Document processing timed out after 30 minutes'
            )