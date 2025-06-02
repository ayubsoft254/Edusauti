from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta


class User(AbstractUser):
    """Custom User model with subscription tiers and usage tracking"""
    
    SUBSCRIPTION_TIERS = [
        ('free', 'Starter Learn'),
        ('pro', 'Smart Learn'),
        ('edu', 'Classroom Learn'),
        ('enterprise', 'Institution Learn'),
    ]
    
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    
    # Subscription and billing
    subscription_tier = models.CharField(
        max_length=20, 
        choices=SUBSCRIPTION_TIERS, 
        default='free'
    )
    subscription_start_date = models.DateTimeField(null=True, blank=True)
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    is_subscription_active = models.BooleanField(default=False)
    
    # Usage tracking
    documents_uploaded_this_month = models.PositiveIntegerField(default=0)
    questions_asked_this_month = models.PositiveIntegerField(default=0)
    last_usage_reset = models.DateTimeField(auto_now_add=True)
    
    # User preferences
    preferred_voice = models.CharField(max_length=50, default='en-US-JennyNeural')
    preferred_language = models.CharField(max_length=10, default='en-US')
    auto_play_summaries = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)
    
    # Profile
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    organization = models.CharField(max_length=200, blank=True)
    role = models.CharField(max_length=100, blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def monthly_document_limit(self):
        """Get document upload limit based on subscription tier"""
        limits = {
            'free': 5,
            'pro': 50,
            'edu': 200,
            'enterprise': 999999,  # Unlimited
        }
        return limits.get(self.subscription_tier, 5)
    
    @property
    def monthly_question_limit(self):
        """Get question limit based on subscription tier"""
        limits = {
            'free': 5,
            'pro': 999999,  # Unlimited
            'edu': 999999,  # Unlimited
            'enterprise': 999999,  # Unlimited
        }
        return limits.get(self.subscription_tier, 5)
    
    @property
    def can_upload_document(self):
        """Check if user can upload more documents this month"""
        self.reset_monthly_usage_if_needed()
        return self.documents_uploaded_this_month < self.monthly_document_limit
    
    @property
    def can_ask_question(self):
        """Check if user can ask more questions this month"""
        self.reset_monthly_usage_if_needed()
        return self.questions_asked_this_month < self.monthly_question_limit
    
    @property
    def has_premium_features(self):
        """Check if user has access to premium features"""
        return self.subscription_tier in ['pro', 'edu', 'enterprise']
    
    @property
    def has_realtime_qa(self):
        """Check if user has access to real-time Q&A"""
        return self.subscription_tier in ['pro', 'edu', 'enterprise']
    
    @property
    def available_voices(self):
        """Get available voices based on subscription tier"""
        basic_voices = ['en-US-JennyNeural', 'en-US-GuyNeural']
        premium_voices = [
            'en-US-AriaNeural', 'en-US-DavisNeural', 'en-US-AmberNeural',
            'en-US-AnaNeural', 'en-US-BrandonNeural'
        ]
        
        if self.subscription_tier == 'free':
            return basic_voices
        else:
            return basic_voices + premium_voices
    
    def reset_monthly_usage_if_needed(self):
        """Reset monthly usage counters if a new month has started"""
        now = timezone.now()
        if self.last_usage_reset.month != now.month or self.last_usage_reset.year != now.year:
            self.documents_uploaded_this_month = 0
            self.questions_asked_this_month = 0
            self.last_usage_reset = now
            self.save(update_fields=['documents_uploaded_this_month', 'questions_asked_this_month', 'last_usage_reset'])
    
    def increment_document_count(self):
        """Increment document upload count"""
        self.reset_monthly_usage_if_needed()
        self.documents_uploaded_this_month += 1
        self.save(update_fields=['documents_uploaded_this_month'])
    
    def increment_question_count(self):
        """Increment question count"""
        self.reset_monthly_usage_if_needed()
        self.questions_asked_this_month += 1
        self.save(update_fields=['questions_asked_this_month'])
    
    def update_subscription(self, tier, duration_months=1):
        """Update user subscription"""
        self.subscription_tier = tier
        self.subscription_start_date = timezone.now()
        self.subscription_end_date = self.subscription_start_date + timedelta(days=30 * duration_months)
        self.is_subscription_active = True
        self.save()
    
    def cancel_subscription(self):
        """Cancel user subscription (set to expire at end of period)"""
        # Don't immediately downgrade, let it expire naturally
        self.is_subscription_active = False
        self.save()
    
    def check_subscription_status(self):
        """Check and update subscription status"""
        if self.subscription_end_date and timezone.now() > self.subscription_end_date:
            self.subscription_tier = 'free'
            self.is_subscription_active = False
            self.subscription_start_date = None
            self.subscription_end_date = None
            self.save()


class UserProfile(models.Model):
    """Extended user profile for additional information"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    country = models.CharField(max_length=100, blank=True)
    timezone = models.CharField(max_length=50, default='UTC')
    
    # Learning preferences
    default_summary_length = models.CharField(
        max_length=20,
        choices=[
            ('short', 'Short (1-2 min)'),
            ('medium', 'Medium (3-5 min)'),
            ('long', 'Long (5+ min)'),
        ],
        default='medium'
    )
    preferred_explanation_style = models.CharField(
        max_length=20,
        choices=[
            ('simple', 'Simple & Clear'),
            ('detailed', 'Detailed & Technical'),
            ('academic', 'Academic Style'),
        ],
        default='simple'
    )
    
    # Analytics
    total_documents_processed = models.PositiveIntegerField(default=0)
    total_questions_asked = models.PositiveIntegerField(default=0)
    total_audio_time_listened = models.PositiveIntegerField(default=0)  # in seconds
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"Profile for {self.user.get_full_name()}"


class SubscriptionHistory(models.Model):
    """Track subscription changes and billing history"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscription_history')
    tier = models.CharField(max_length=20, choices=User.SUBSCRIPTION_TIERS)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Subscription History'
        verbose_name_plural = 'Subscription Histories'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.tier} ({self.start_date.date()})"
