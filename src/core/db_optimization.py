from django.db import models
from django.core.cache import cache
from .models import Document 

class CachedDocument(Document):  # Specify the base model
    """Optimized document model with caching"""
    
    class Meta:
        proxy = True
        
    @property
    def cached_summary(self):
        cache_key = f'summary_{self.id}'
        summary = cache.get(cache_key)
        
        if summary is None:
            # Add error handling for missing summary
            try:
                summary = self.summary.text if hasattr(self, 'summary') and self.summary else ""
                cache.set(cache_key, summary, 3600)  # Cache for 1 hour
            except Exception as e:
                summary = ""
                # Log the error
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error retrieving summary for document {self.id}: {e}")
        
        return summary

    def invalidate_cache(self):
        """Invalidate cached data when document is updated"""
        cache_key = f'summary_{self.id}'
        cache.delete(cache_key)
        
    def save(self, *args, **kwargs):
        """Override save to invalidate cache"""
        super().save(*args, **kwargs)
        self.invalidate_cache()