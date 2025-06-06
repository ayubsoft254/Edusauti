import os
import logging
from django.db import models
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
        
        # Update status to processing
        instance.status = 'processing'
        instance.processing_started_at = timezone.now()
        instance.save(update_fields=['status', 'processing_started_at'])
        
        # Process synchronously for development
        try:
            from django.conf import settings
            if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False) or settings.DEBUG:
                # Process synchronously in development
                from .tasks import process_document_sync
                process_document_sync(instance.id)
            else:
                # Use Celery in production
                from .tasks import process_document_pipeline
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