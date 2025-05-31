from django.db import models
from django.core.cache import cache
from .models import Document 
import logging

logger = logging.getLogger(__name__)

class CachedDocument(Document):  # Specify the base model
    """Optimized document model with caching"""
    
    class Meta:
        proxy = True
        
    @property
    def cached_summary(self):
        cache_key = f'summary_{self.id}'
        summary = cache.get(cache_key)
        
        if summary is None:
            logger.debug(f"Cache miss for summary_{self.id}")
            try:
                summary = self.summary.text if hasattr(self, 'summary') and self.summary else ""
                cache.set(cache_key, summary, 3600)
                logger.debug(f"Cached summary for document {self.id}")
            except Exception as e:
                logger.error(f"Error retrieving summary for document {self.id}: {e}")
                summary = ""
        else:
            logger.debug(f"Cache hit for summary_{self.id}")
        
        return summary

    def invalidate_cache(self):
        """Invalidate cached data when document is updated"""
        cache_key = f'summary_{self.id}'
        cache.delete(cache_key)
        
    def save(self, *args, **kwargs):
        """Override save to invalidate cache"""
        super().save(*args, **kwargs)
        self.invalidate_cache()
        
    @classmethod
    def get_user_documents_cached(cls, user_id):
        """Get user documents with caching"""
        cache_key = f'user_docs_{user_id}'
        documents = cache.get(cache_key)
        
        if documents is None:
            documents = list(cls.objects.filter(user_id=user_id).select_related('user'))
            cache.set(cache_key, documents, 1800)  # Cache for 30 minutes
            
        return documents
    
    @property
    def cached_audio_url(self):
        """Cache audio file URL"""
        cache_key = f'audio_url_{self.id}'
        audio_url = cache.get(cache_key)
        
        if audio_url is None:
            try:
                if hasattr(self, 'audiofile') and self.audiofile:
                    audio_url = f"/api/audio/{self.audiofile.id}/"
                else:
                    audio_url = ""
                cache.set(cache_key, audio_url, 3600)
            except Exception:
                audio_url = ""
                
        return audio_url