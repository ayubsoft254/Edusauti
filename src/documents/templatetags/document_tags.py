from django import template

register = template.Library()

@register.filter
def audio_size_mb(value):
    """Convert bytes to MB for audio files"""
    if not value:
        return 0
    return round(value / (1024 * 1024), 1)

@register.filter
def split(value, delimiter=','):
    """Split a string by delimiter and return a list"""
    if not value:
        return []
    return [item.strip() for item in value.split(delimiter) if item.strip()]