import os
import logging
import tempfile
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from celery import shared_task
from celery.exceptions import Retry
from .models import Document, AudioSummary, Question, ProcessingLog
from ai_services.document_intelligence import DocumentIntelligenceService
from ai_services.openai_service import OpenAIService
from ai_services.speech_service import SpeechService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_document_pipeline(self, document_id):
    """
    Main task to process a document through the complete AI pipeline
    1. Extract text from document
    2. Generate AI summary
    3. Create audio summary
    """
    
    try:
        document = Document.objects.get(id=document_id)
        
        ProcessingLog.objects.create(
            document=document,
            step='processing',
            level='info',
            message='Starting document processing pipeline'
        )
        
        # Step 1: Extract text from document
        extract_text_from_document.delay(document_id)
        
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found")
        raise
    except Exception as exc:
        logger.error(f"Error in document pipeline for {document_id}: {str(exc)}")
        
        # Update document status to failed
        try:
            document = Document.objects.get(id=document_id)
            document.status = 'failed'
            document.error_message = f"Pipeline error: {str(exc)}"
            document.save(update_fields=['status', 'error_message'])
            
            ProcessingLog.objects.create(
                document=document,
                step='processing',
                level='error',
                message=f'Pipeline failed: {str(exc)}'
            )
        except:
            pass
        
        # Retry the task
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries), exc=exc)
        else:
            raise exc


@shared_task(bind=True, max_retries=3)
def extract_text_from_document(self, document_id):
    """Extract text from document using Azure Document Intelligence"""
    
    try:
        document = Document.objects.get(id=document_id)
        
        ProcessingLog.objects.create(
            document=document,
            step='text_extraction',
            level='info',
            message='Starting text extraction'
        )
        
        # Initialize Document Intelligence service
        doc_intel_service = DocumentIntelligenceService()
        
        # Extract text from document
        extraction_result = doc_intel_service.extract_text(document.file.path)
        
        # Update document with extracted content
        document.extracted_text = extraction_result['text']
        document.text_extraction_confidence = extraction_result.get('confidence', 0.0)
        document.page_count = extraction_result.get('page_count', 1)
        document.word_count = len(extraction_result['text'].split()) if extraction_result['text'] else 0
        document.save(update_fields=[
            'extracted_text', 'text_extraction_confidence', 'page_count', 'word_count'
        ])
        
        ProcessingLog.objects.create(
            document=document,
            step='text_extraction',
            level='info',
            message=f'Text extraction completed. {document.word_count} words extracted.',
            details={
                'word_count': document.word_count,
                'page_count': document.page_count,
                'confidence': document.text_extraction_confidence
            }
        )
        
        # Proceed to summarization
        generate_ai_summary.delay(document_id)
        
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found for text extraction")
        raise
    except Exception as exc:
        logger.error(f"Text extraction failed for document {document_id}: {str(exc)}")
        
        try:
            document = Document.objects.get(id=document_id)
            document.status = 'failed'
            document.error_message = f"Text extraction failed: {str(exc)}"
            document.save(update_fields=['status', 'error_message'])
            
            ProcessingLog.objects.create(
                document=document,
                step='text_extraction',
                level='error',
                message=f'Text extraction failed: {str(exc)}'
            )
        except:
            pass
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries), exc=exc)
        else:
            raise exc


@shared_task(bind=True, max_retries=3)
def generate_ai_summary(self, document_id):
    """Generate AI summary using Azure OpenAI"""
    
    try:
        document = Document.objects.get(id=document_id)
        
        if not document.extracted_text:
            raise ValueError("No extracted text available for summarization")
        
        ProcessingLog.objects.create(
            document=document,
            step='summarization',
            level='info',
            message='Starting AI summarization'
        )
        
        # Initialize OpenAI service
        openai_service = OpenAIService()
        
        # Determine summary length based on user preference or document setting
        summary_style = 'teacher'  # Teacher-like explanation style
        summary_length = document.summary_length
        
        # Generate summary
        summary_result = openai_service.generate_summary(
            text=document.extracted_text,
            style=summary_style,
            length=summary_length,
            subject_area=document.subject_area,
            difficulty_level=document.difficulty_level
        )
        
        # Update document with summary
        document.summary_text = summary_result['summary']
        document.save(update_fields=['summary_text'])
        
        ProcessingLog.objects.create(
            document=document,
            step='summarization',
            level='info',
            message=f'AI summary generated successfully. {len(summary_result["summary"])} characters.',
            details={
                'summary_length': len(summary_result['summary']),
                'tokens_used': summary_result.get('tokens_used'),
                'cost': summary_result.get('cost')
            }
        )
        
        # Proceed to audio generation
        generate_audio_summary.delay(document_id)
        
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found for summarization")
        raise
    except Exception as exc:
        logger.error(f"AI summarization failed for document {document_id}: {str(exc)}")
        
        try:
            document = Document.objects.get(id=document_id)
            document.status = 'failed'
            document.error_message = f"AI summarization failed: {str(exc)}"
            document.save(update_fields=['status', 'error_message'])
            
            ProcessingLog.objects.create(
                document=document,
                step='summarization',
                level='error',
                message=f'AI summarization failed: {str(exc)}'
            )
        except:
            pass
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries), exc=exc)
        else:
            raise exc


@shared_task(bind=True, max_retries=3)
def generate_audio_summary(self, document_id, voice_name=None, speech_rate='medium', speech_pitch='medium'):
    """Generate audio summary using Azure Speech Service"""
    
    try:
        document = Document.objects.get(id=document_id)
        
        if not document.summary_text:
            raise ValueError("No summary text available for audio generation")
        
        # Use user's preferred voice or provided voice
        if not voice_name:
            voice_name = document.user.preferred_voice
        
        ProcessingLog.objects.create(
            document=document,
            step='audio_generation',
            level='info',
            message=f'Starting audio generation with voice {voice_name}'
        )
        
        # Create AudioSummary record
        audio_summary = AudioSummary.objects.create(
            document=document,
            voice_name=voice_name,
            speech_rate=speech_rate,
            speech_pitch=speech_pitch,
            status='generating'
        )
        
        # Initialize Speech service
        speech_service = SpeechService()
        
        # Generate audio
        audio_result = speech_service.text_to_speech(
            text=document.summary_text,
            voice_name=voice_name,
            speech_rate=speech_rate,
            speech_pitch=speech_pitch
        )
        
        # Save audio file
        audio_filename = f"summary_{document_id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        audio_path = f"audio/{document.user.id}/{timezone.now().year}/{timezone.now().month}/"
        
        # Ensure directory exists
        full_audio_path = os.path.join(settings.MEDIA_ROOT, audio_path)
        os.makedirs(full_audio_path, exist_ok=True)
        
        # Save audio file
        full_audio_filename = os.path.join(full_audio_path, audio_filename)
        with open(full_audio_filename, 'wb') as audio_file:
            audio_file.write(audio_result['audio_data'])
        
        # Update AudioSummary record
        audio_summary.audio_file = os.path.join(audio_path, audio_filename)
        audio_summary.audio_duration = audio_result['duration']
        audio_summary.audio_size = len(audio_result['audio_data'])
        audio_summary.generation_time = audio_result.get('generation_time', 0)
        audio_summary.azure_request_id = audio_result.get('request_id', '')
        audio_summary.azure_cost = audio_result.get('cost', 0)
        audio_summary.status = 'completed'
        audio_summary.save()
        
        # Mark document as completed
        document.status = 'completed'
        document.processing_completed_at = timezone.now()
        document.save(update_fields=['status', 'processing_completed_at'])
        
        ProcessingLog.objects.create(
            document=document,
            step='audio_generation',
            level='info',
            message=f'Audio generation completed. Duration: {audio_summary.audio_duration_formatted}',
            details={
                'audio_duration': audio_summary.audio_duration,
                'audio_size': audio_summary.audio_size,
                'generation_time': audio_summary.generation_time,
                'cost': float(audio_summary.azure_cost) if audio_summary.azure_cost else None
            }
        )
        
        ProcessingLog.objects.create(
            document=document,
            step='completion',
            level='info',
            message='Document processing pipeline completed successfully'
        )
        
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found for audio generation")
        raise
    except Exception as exc:
        logger.error(f"Audio generation failed for document {document_id}: {str(exc)}")
        
        try:
            document = Document.objects.get(id=document_id)
            document.status = 'failed'
            document.error_message = f"Audio generation failed: {str(exc)}"
            document.save(update_fields=['status', 'error_message'])
            
            # Update AudioSummary status if it exists
            try:
                audio_summary = AudioSummary.objects.get(document=document, status='generating')
                audio_summary.status = 'failed'
                audio_summary.save()
            except AudioSummary.DoesNotExist:
                pass
            
            ProcessingLog.objects.create(
                document=document,
                step='audio_generation',
                level='error',
                message=f'Audio generation failed: {str(exc)}'
            )
        except:
            pass
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries), exc=exc)
        else:
            raise exc


@shared_task(bind=True, max_retries=3)
def process_question(self, question_id):
    """Process a user question using Azure OpenAI"""
    
    try:
        question = Question.objects.get(id=question_id)
        document = question.document
        
        ProcessingLog.objects.create(
            document=document,
            step='completion',
            level='info',
            message=f'Processing question: {question.question_text[:50]}...'
        )
        
        # Initialize OpenAI service
        openai_service = OpenAIService()
        
        # Process the question
        start_time = timezone.now()
        
        answer_result = openai_service.answer_question(
            question=question.question_text,
            context=document.extracted_text,
            summary=document.summary_text,
            audio_timestamp=question.audio_timestamp
        )
        
        end_time = timezone.now()
        processing_time = int((end_time - start_time).total_seconds() * 1000)  # milliseconds
        
        # Update question with answer
        question.answer_text = answer_result['answer']
        question.context_snippet = answer_result.get('context_snippet', '')
        question.answer_confidence = answer_result.get('confidence', 0.0)
        question.processing_time = processing_time
        question.azure_request_id = answer_result.get('request_id', '')
        question.azure_cost = answer_result.get('cost', 0)
        question.is_answered = True
        question.answered_at = timezone.now()
        question.save()
        
        ProcessingLog.objects.create(
            document=document,
            step='completion',
            level='info',
            message=f'Question answered successfully in {processing_time}ms',
            details={
                'processing_time': processing_time,
                'confidence': question.answer_confidence,
                'tokens_used': answer_result.get('tokens_used'),
                'cost': float(question.azure_cost) if question.azure_cost else None
            }
        )
        
    except Question.DoesNotExist:
        logger.error(f"Question {question_id} not found")
        raise
    except Exception as exc:
        logger.error(f"Question processing failed for question {question_id}: {str(exc)}")
        
        try:
            question = Question.objects.get(id=question_id)
            question.answer_text = f"I'm sorry, I encountered an error while processing your question: {str(exc)}"
            question.is_answered = True
            question.answered_at = timezone.now()
            question.save()
            
            ProcessingLog.objects.create(
                document=question.document,
                step='completion',
                level='error',
                message=f'Question processing failed: {str(exc)}'
            )
        except:
            pass
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=30 * (2 ** self.request.retries), exc=exc)
        else:
            raise exc


@shared_task(bind=True, max_retries=2)
def generate_answer_audio(self, question_id):
    """Generate audio for question answer (premium feature)"""
    
    try:
        question = Question.objects.get(id=question_id)
        
        if not question.is_answered or not question.answer_text:
            raise ValueError("Question is not answered yet")
        
        if not question.user.has_premium_features:
            logger.info(f"User {question.user.id} doesn't have premium features for audio answers")
            return
        
        # Initialize Speech service
        speech_service = SpeechService()
        
        # Use user's preferred voice
        voice_name = question.user.preferred_voice
        
        # Generate audio for the answer
        audio_result = speech_service.text_to_speech(
            text=question.answer_text,
            voice_name=voice_name,
            speech_rate='medium',
            speech_pitch='medium'
        )
        
        # Save audio file (simplified - you might want to create a separate model for question audio)
        audio_filename = f"answer_{question_id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        audio_path = f"audio/answers/{question.user.id}/"
        
        # Ensure directory exists
        full_audio_path = os.path.join(settings.MEDIA_ROOT, audio_path)
        os.makedirs(full_audio_path, exist_ok=True)
        
        # Save audio file
        full_audio_filename = os.path.join(full_audio_path, audio_filename)
        with open(full_audio_filename, 'wb') as audio_file:
            audio_file.write(audio_result['audio_data'])
        
        # You might want to store the audio path in the question model or create a separate model
        # For now, we'll just log it
        ProcessingLog.objects.create(
            document=question.document,
            step='completion',
            level='info',
            message=f'Answer audio generated for question',
            details={
                'audio_path': os.path.join(audio_path, audio_filename),
                'audio_duration': audio_result['duration'],
                'cost': audio_result.get('cost')
            }
        )
        
    except Question.DoesNotExist:
        logger.error(f"Question {question_id} not found for audio generation")
        raise
    except Exception as exc:
        logger.error(f"Answer audio generation failed for question {question_id}: {str(exc)}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=exc)
        else:
            # Don't fail hard for audio generation
            logger.error(f"Answer audio generation permanently failed for question {question_id}")


@shared_task
def cleanup_failed_documents():
    """Periodic task to cleanup documents stuck in processing state"""
    
    # Find documents that have been processing for more than 1 hour
    cutoff_time = timezone.now() - timedelta(hours=1)
    stuck_documents = Document.objects.filter(
        status='processing',
        processing_started_at__lt=cutoff_time
    )
    
    for document in stuck_documents:
        document.status = 'failed'
        document.error_message = 'Processing timeout - document was stuck in processing state'
        document.save(update_fields=['status', 'error_message'])
        
        ProcessingLog.objects.create(
            document=document,
            step='processing',
            level='error',
            message='Document processing timed out and was marked as failed'
        )
        
        logger.warning(f"Document {document.id} was stuck in processing and marked as failed")
    
    logger.info(f"Cleanup completed. {stuck_documents.count()} documents were marked as failed.")


@shared_task
def cleanup_old_files():
    """Periodic task to cleanup old files and optimize storage"""
    
    # Find audio summaries older than 90 days for free users
    cutoff_date = timezone.now() - timedelta(days=90)
    old_audio_summaries = AudioSummary.objects.filter(
        generated_at__lt=cutoff_date,
        document__user__subscription_tier='free'
    )
    
    deleted_count = 0
    for audio_summary in old_audio_summaries:
        try:
            if audio_summary.audio_file and os.path.exists(audio_summary.audio_file.path):
                os.remove(audio_summary.audio_file.path)
                deleted_count += 1
            audio_summary.delete()
        except Exception as e:
            logger.error(f"Failed to cleanup audio summary {audio_summary.id}: {str(e)}")
    
    logger.info(f"Cleanup completed. {deleted_count} old audio files were deleted.")


@shared_task
def generate_usage_analytics():
    """Generate usage analytics and update user profiles"""
    
    from django.contrib.auth import get_user_model
    from django.db.models import Count, Sum, Avg
    
    User = get_user_model()
    
    for user in User.objects.filter(is_active=True):
        try:
            # Calculate analytics
            user_documents = Document.objects.filter(user=user)
            
            analytics = {
                'total_documents': user_documents.count(),
                'completed_documents': user_documents.filter(status='completed').count(),
                'total_questions': Question.objects.filter(user=user).count(),
                'total_audio_time': AudioSummary.objects.filter(
                    document__user=user,
                    status='completed'
                ).aggregate(Sum('audio_duration'))['audio_duration__sum'] or 0,
                'average_processing_time': user_documents.filter(
                    status='completed'
                ).aggregate(Avg('processing_duration'))['processing_duration__avg'] or 0
            }
            
            # Update user profile if it exists
            if hasattr(user, 'profile'):
                profile = user.profile
                profile.total_documents_processed = analytics['completed_documents']
                profile.total_questions_asked = analytics['total_questions']
                profile.total_audio_time_listened = analytics['total_audio_time']
                profile.save()
            
        except Exception as e:
            logger.error(f"Failed to generate analytics for user {user.id}: {str(e)}")
    
    logger.info("Usage analytics generation completed.")


@shared_task(bind=True)
def regenerate_audio_summary(self, document_id, voice_name, speech_rate='medium', speech_pitch='medium'):
    """Regenerate audio summary with different voice settings"""
    
    try:
        document = Document.objects.get(id=document_id)
        
        if not document.summary_text:
            raise ValueError("No summary text available for audio regeneration")
        
        # Call the audio generation task with custom settings
        generate_audio_summary.delay(document_id, voice_name, speech_rate, speech_pitch)
        
        ProcessingLog.objects.create(
            document=document,
            step='audio_generation',
            level='info',
            message=f'Audio regeneration started with voice {voice_name}'
        )
        
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found for audio regeneration")
        raise
    except Exception as exc:
        logger.error(f"Audio regeneration failed for document {document_id}: {str(exc)}")
        raise exc