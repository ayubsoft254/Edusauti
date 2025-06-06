from django import template

register = template.Library()

@register.filter
def audio_size_mb(value):
    """Convert audio size from bytes to MB"""
    if not value:
        return 0
    return round(value / (1024 * 1024), 1)