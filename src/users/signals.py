from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from .models import User, UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create user profile when user is created"""
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save user profile when user is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()


@receiver(user_logged_in)
def update_last_login_ip(sender, request, user, **kwargs):
    """Update user's last login IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    user.last_login_ip = ip
    user.save(update_fields=['last_login_ip'])


@receiver(pre_save, sender=User)
def check_subscription_status(sender, instance, **kwargs):
    """Check and update subscription status before saving"""
    if instance.pk:  # Only for existing users
        instance.check_subscription_status()
