from django.db import models
from django.core.cache import cache

class CachedDocument(models.Model):
    """Optimized document model with caching"""
    
    class Meta:
        proxy = True
        
    @property
    def cached_summary(self):
        cache_key = f'summary_{self.id}'
        summary = cache.get(cache_key)
        
        if summary is None:
            summary = self.summary.text
            cache.set(cache_key, summary, 3600)  # Cache for 1 hour
        
        return summary