import logging
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def send_audio_ready_notification(user, document):
    """Send notification when audio summary is ready"""
    
    if not user.email_notifications:
        return
    
    try:
        subject = f"[EduSauti] Your audio summary is ready: {document.title}"
        
        html_message = render_to_string('documents/emails/audio_ready.html', {
            'user': user,
            'document': document,
            'site_name': 'EduSauti'
        })
        
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False
        )
        
        logger.info(f"Audio ready notification sent to {user.email} for document {document.id}")
        
    except Exception as e:
        logger.error(f"Failed to send audio ready notification to {user.email}: {str(e)}")


def send_processing_failed_notification(user, document, error_message):
    """Send notification when document processing fails"""
    
    if not user.email_notifications:
        return
    
    try:
        subject = f"[EduSauti] Processing failed for: {document.title}"
        
        html_message = render_to_string('documents/emails/processing_failed.html', {
            'user': user,
            'document': document,
            'error_message': error_message,
            'site_name': 'EduSauti'
        })
        
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False
        )
        
        logger.info(f"Processing failed notification sent to {user.email} for document {document.id}")
        
    except Exception as e:
        logger.error(f"Failed to send processing failed notification to {user.email}: {str(e)}")


def calculate_processing_cost(document):
    """Calculate the estimated cost for processing a document"""
    
    # Rough estimates - you should update these based on actual Azure pricing
    costs = {
        'text_extraction': 0.01,  # per page
        'summarization': 0.002,   # per 1K tokens
        'audio_generation': 0.016,  # per 1M characters
    }
    
    total_cost = 0
    
    # Text extraction cost (based on pages)
    if document.page_count:
        total_cost += costs['text_extraction'] * document.page_count
    
    # Summarization cost (rough estimate based on word count)
    if document.word_count:
        # Roughly 1 token = 0.75 words
        tokens = document.word_count / 0.75
        total_cost += costs['summarization'] * (tokens / 1000)
    
    # Audio generation cost (based on summary length)
    if document.summary_text:
        chars = len(document.summary_text)
        total_cost += costs['audio_generation'] * (chars / 1000000)
    
    return round(total_cost, 4)


def get_processing_status_message(document):
    """Get user-friendly status message for document processing"""
    
    status_messages = {
        'uploaded': 'Your document has been uploaded and is queued for processing.',
        'processing': 'We are currently processing your document. This may take a few minutes.',
        'completed': 'Your document has been processed successfully! You can now listen to the audio summary.',
        'failed': 'There was an error processing your document. Please try uploading again or contact support.',
        'error': 'An unexpected error occurred. Our team has been notified.'
    }
    
    return status_messages.get(document.status, 'Unknown status')


def validate_document_file(file):
    """Validate uploaded document file"""
    
    # File size validation (e.g., 50MB limit)
    max_size = 50 * 1024 * 1024  # 50MB
    if file.size > max_size:
        raise ValueError(f"File size ({file.size / 1024 / 1024:.1f}MB) exceeds the maximum limit of 50MB.")
    
    # File type validation
    allowed_extensions = ['pdf', 'docx', 'txt', 'pptx']
    file_extension = file.name.split('.')[-1].lower()
    
    if file_extension not in allowed_extensions:
        raise ValueError(f"File type '{file_extension}' is not supported. Allowed types: {', '.join(allowed_extensions)}")
    
    # File name validation
    if len(file.name) > 255:
        raise ValueError("File name is too long. Please use a shorter file name.")
    
    return True


def generate_share_link(document, base_url):
    """Generate a shareable link for a document"""
    
    from .models import DocumentShare
    import secrets
    
    # Generate unique token
    share_token = secrets.token_urlsafe(32)
    
    # Create share record
    share = DocumentShare.objects.create(
        document=document,
        shared_by=document.user,
        share_token=share_token,
        can_view=True
    )
    
    return f"{base_url}/documents/shared/{share_token}/"


def format_duration(seconds):
    """Format duration in seconds to human-readable format"""
    
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = int(seconds // 3600)
        remaining_minutes = int((seconds % 3600) // 60)
        return f"{hours}h {remaining_minutes}m"


def get_file_icon(file_type):
    """Get appropriate icon for file type"""
    
    icons = {
        'pdf': 'far fa-file-pdf',
        'docx': 'far fa-file-word',
        'txt': 'far fa-file-alt',
        'pptx': 'far fa-file-powerpoint',
    }
    
    return icons.get(file_type, 'far fa-file')


def sanitize_filename(filename):
    """Sanitize filename for safe storage"""
    
    import re
    
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Limit length
    if len(filename) > 100:
        name, ext = filename.rsplit('.', 1)
        filename = name[:100-len(ext)-1] + '.' + ext
    
    return filename