from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta


class SubscriptionTier(models.TextChoices):
    """Subscription tier choices for EduSauti users"""
    FREE = 'free', 'Starter Learn'
    PRO = 'pro', 'Smart Learn'
    EDU = 'edu', 'Classroom Learn'
    ENTERPRISE = 'enterprise', 'Institution Learn'


class User(AbstractUser):
    """Custom User model for EduSauti"""
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    
    # Profile fields
    phone_number = models.CharField(max_length=20, blank=True)
    organization = models.CharField(max_length=100, blank=True)
    preferred_language = models.CharField(max_length=10, default='en')
    preferred_voice = models.CharField(max_length=50, default='default')
    
    # Subscription fields
    subscription_tier = models.CharField(
        max_length=20,
        choices=SubscriptionTier.choices,
        default=SubscriptionTier.FREE
    )
    subscription_start_date = models.DateTimeField(null=True, blank=True)
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    is_subscription_active = models.BooleanField(default=False)
    
    # Usage tracking
    documents_uploaded_this_month = models.IntegerField(default=0)
    questions_asked_this_month = models.IntegerField(default=0)
    last_usage_reset = models.DateTimeField(default=timezone.now)
    
    # Settings
    email_notifications = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_premium_user(self):
        """Check if user has a premium subscription"""
        return self.subscription_tier in [
            SubscriptionTier.PRO,
            SubscriptionTier.EDU,
            SubscriptionTier.ENTERPRISE
        ]
    
    def can_upload_document(self):
        """Check if user can upload more documents based on their tier"""
        limits = {
            SubscriptionTier.FREE: 5,
            SubscriptionTier.PRO: 50,
            SubscriptionTier.EDU: 200,
            SubscriptionTier.ENTERPRISE: float('inf')
        }
        limit = limits.get(self.subscription_tier, 5)
        return self.documents_uploaded_this_month < limit
    
    def can_ask_question(self):
        """Check if user can ask more questions based on their tier"""
        if self.subscription_tier == SubscriptionTier.FREE:
            return self.questions_asked_this_month < 25  # 5 docs * 5 questions
        return True  # Premium users have unlimited questions
    
    def reset_monthly_usage(self):
        """Reset monthly usage counters"""
        self.documents_uploaded_this_month = 0
        self.questions_asked_this_month = 0
        self.last_usage_reset = timezone.now()
        self.save()
    
    def increment_document_count(self):
        """Increment document upload count"""
        self.documents_uploaded_this_month += 1
        self.save()
    
    def increment_question_count(self):
        """Increment question count"""
        self.questions_asked_this_month += 1
        self.save()


class UserProfile(models.Model):
    """Extended user profile information"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    
    # Education/Organization info
    institution = models.CharField(max_length=200, blank=True)
    department = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=100, blank=True)  # Student, Teacher, Administrator, etc.
    
    # Preferences
    timezone = models.CharField(max_length=50, default='UTC')
    date_format_preference = models.CharField(max_length=20, default='YYYY-MM-DD')
    
    # Analytics preferences
    allow_analytics = models.BooleanField(default=True)
    allow_marketing_emails = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profiles'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"Profile for {self.user.full_name}"


class Subscription(models.Model):
    """Subscription history and details"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    tier = models.CharField(max_length=20, choices=SubscriptionTier.choices)
    
    # Billing
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    billing_cycle = models.CharField(max_length=20, default='monthly')  # monthly, yearly
    
    # Dates
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    # Payment info
    payment_method = models.CharField(max_length=50, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    auto_renew = models.BooleanField(default=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'subscriptions'
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.full_name} - {self.get_tier_display()}"
    
    @property
    def is_expired(self):
        return timezone.now() > self.end_date
    
    def cancel_subscription(self):
        """Cancel the subscription"""
        self.is_active = False
        self.auto_renew = False
        self.cancelled_at = timezone.now()
        self.save()
        
        # Update user subscription status
        self.user.is_subscription_active = False
        self.user.save()
