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

    SUBSCRIPTION_CHOICES = SUBSCRIPTION_TIERS
    
    # Keep both username and email
    username = models.CharField(max_length=150, unique=True)  # Add this back
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
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']  # These will be prompted during createsuperuser
    
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
    
    PAYMENT_METHOD_CHOICES = [
        ('demo', 'Demo'),
        ('api', 'API'),
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscription_history')
    tier = models.CharField(max_length=20, choices=User.SUBSCRIPTION_TIERS)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Subscription History'
        verbose_name_plural = 'Subscription Histories'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.tier} ({self.start_date.date()})"
    
    def get_next_billing_date(self):
        """Calculate next billing date"""
        if not self.is_active or not self.end_date:
            return None
        
        # Fix: Compare datetime with datetime, not datetime with date
        if self.end_date > timezone.now():
            return self.end_date
        
        return None


class BillingProfile(models.Model):
    """Extended billing information for users"""
    
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound'),
        ('CAD', 'Canadian Dollar'),
        ('AUD', 'Australian Dollar'),
    ]
    
    COUNTRY_CHOICES = [
        ('US', 'United States'),
        ('CA', 'Canada'),
        ('GB', 'United Kingdom'),
        ('AU', 'Australia'),
        ('DE', 'Germany'),
        ('FR', 'France'),
        ('IT', 'Italy'),
        ('ES', 'Spain'),
        ('NL', 'Netherlands'),
        ('SE', 'Sweden'),
        ('NO', 'Norway'),
        ('DK', 'Denmark'),
        ('FI', 'Finland'),
        ('CH', 'Switzerland'),
        ('AT', 'Austria'),
        ('BE', 'Belgium'),
        ('IE', 'Ireland'),
        ('PT', 'Portugal'),
        ('LU', 'Luxembourg'),
        ('IS', 'Iceland'),
        # Add more countries as needed
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='billing_profile')
    
    # Company information
    company_name = models.CharField(max_length=200, blank=True)
    tax_id = models.CharField(max_length=50, blank=True, help_text="VAT ID, Tax ID, etc.")
    
    # Billing address
    billing_address_line1 = models.CharField(max_length=200)
    billing_address_line2 = models.CharField(max_length=200, blank=True)
    billing_city = models.CharField(max_length=100)
    billing_state = models.CharField(max_length=100, blank=True)
    billing_country = models.CharField(max_length=2, choices=COUNTRY_CHOICES)
    billing_postal_code = models.CharField(max_length=20)
    
    # Preferences
    preferred_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Billing Profile'
        verbose_name_plural = 'Billing Profiles'
    
    def __str__(self):
        return f"Billing for {self.user.email}"
    
    def get_full_address(self):
        """Get formatted billing address"""
        address_parts = [self.billing_address_line1]
        
        if self.billing_address_line2:
            address_parts.append(self.billing_address_line2)
        
        address_parts.append(f"{self.billing_city}, {self.billing_state}")
        address_parts.append(self.billing_postal_code)
        address_parts.append(self.get_billing_country_display())
        
        return '\n'.join(address_parts)
    
    def get_payment_methods(self):
        """Get associated payment methods (placeholder for payment processor integration)"""
        # This would integrate with your payment processor (Stripe, PayPal, etc.)
        return []
