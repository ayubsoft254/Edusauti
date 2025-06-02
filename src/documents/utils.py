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
        subject = f'[EduSauti] Audio summary ready for "{document.title}"'
        
        # Render HTML email template
        html_message = render_to_string('documents/emails/audio_ready.html', {
            'user': user,
            'document': document,
            'site_url': settings.SITE_URL,
        })
        
        # Create plain text version
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Audio ready notification sent to {user.email} for document {document.id}")
        
    except Exception as e:
        logger.error(f"Failed to send audio ready notification to {user.email}: {str(e)}")


def send_processing_failed_notification(user, document, error_message):
    """Send notification when document processing fails"""
    
    if not user.email_notifications:
        return
    
    try:
        subject = f'[EduSauti] Processing failed for "{document.title}"'
        
        html_message = render_to_string('documents/emails/processing_failed.html', {
            'user': user,
            'document': document,
            'error_message': error_message,
            'site_url': settings.SITE_URL,
        })
        
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Processing failed notification sent to {user.email} for document {document.id}")
        
    except Exception as e:
        logger.error(f"Failed to send processing failed notification to {user.email}: {str(e)}")


def calculate_processing_cost(document, audio_summary=None, questions_count=0):
    """Calculate estimated Azure service costs for document processing"""
    
    cost = 0.0
    
    # Document Intelligence cost (per page)
    if document.page_count:
        # Azure Document Intelligence: ~$0.0015 per page
        cost += document.page_count * 0.0015
    
    # OpenAI cost (per token - rough estimate)
    if document.word_count:
        # Rough estimate: 1 word = 1.3 tokens, GPT-4: ~$0.03 per 1K tokens
        estimated_tokens = document.word_count * 1.3
        cost += (estimated_tokens / 1000) * 0.03
    
    # Speech Service cost
    if audio_summary and audio_summary.audio_duration:
        # Azure Speech Service: ~$4 per hour
        cost += (audio_summary.audio_duration / 3600) * 4
    
    # Additional Q&A costs
    if questions_count:
        # Estimate ~500 tokens per Q&A
        qa_tokens = questions_count * 500
        cost += (qa_tokens / 1000) * 0.03
    
    return round(cost, 4)


def get_file_type_from_extension(filename):
    """Get file type from filename extension"""
    
    extension = filename.split('.')[-1].lower()
    
    type_mapping = {
        'pdf': 'pdf',
        'docx': 'docx',
        'doc': 'docx',  # Treat .doc as .docx for simplicity
        'txt': 'txt',
        'pptx': 'pptx',
        'ppt': 'pptx',  # Treat .ppt as .pptx
    }
    
    return type_mapping.get(extension, 'unknown')


def validate_file_size(file_size, user):
    """Validate file size based on user's subscription tier"""
    
    # File size limits in bytes
    limits = {
        'free': 10 * 1024 * 1024,      # 10MB
        'pro': 50 * 1024 * 1024,       # 50MB
        'edu': 100 * 1024 * 1024,      # 100MB
        'enterprise': 500 * 1024 * 1024,  # 500MB
    }
    
    max_size = limits.get(user.subscription_tier, limits['free'])
    
    return file_size <= max_size, max_size


def generate_share_token():
    """Generate a secure share token"""
    import secrets
    return secrets.token_urlsafe(32)


def estimate_audio_duration(text_length):
    """Estimate audio duration based on text length"""
    
    # Average reading speed: ~150 words per minute
    # Average word length: ~5 characters
    estimated_words = text_length / 5
    estimated_minutes = estimated_words / 150
    
    return max(30, int(estimated_minutes * 60))  # Minimum 30 seconds


def format_file_size(size_bytes):
    """Format file size in human readable format"""
    
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"


def get_supported_file_extensions():
    """Get list of supported file extensions"""
    return ['pdf', 'docx', 'txt', 'pptx']


def is_file_supported(filename):
    """Check if file extension is supported"""
    extension = filename.split('.')[-1].lower()
    return extension in get_supported_file_extensions()