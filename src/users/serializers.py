from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, UserProfile, SubscriptionHistory


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'organization', 'role',
            'password', 'password_confirm'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(
            username=validated_data['email'],
            password=password,
            **validated_data
        )
        
        # Create user profile
        UserProfile.objects.create(user=user)
        
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(email=email, password=password)
            
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            
            if not user.is_active:
                raise serializers.ValidationError('Account is disabled')
            
            attrs['user'] = user
            return attrs
        
        raise serializers.ValidationError('Must include email and password')


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile data"""
    
    full_name = serializers.ReadOnlyField()
    subscription_tier_display = serializers.CharField(source='get_subscription_tier_display', read_only=True)
    monthly_document_limit = serializers.ReadOnlyField()
    monthly_question_limit = serializers.ReadOnlyField()
    can_upload_document = serializers.ReadOnlyField()
    can_ask_question = serializers.ReadOnlyField()
    has_premium_features = serializers.ReadOnlyField()
    has_realtime_qa = serializers.ReadOnlyField()
    available_voices = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'subscription_tier', 'subscription_tier_display', 'is_subscription_active',
            'documents_uploaded_this_month', 'questions_asked_this_month',
            'monthly_document_limit', 'monthly_question_limit',
            'can_upload_document', 'can_ask_question',
            'has_premium_features', 'has_realtime_qa',
            'preferred_voice', 'preferred_language', 'auto_play_summaries',
            'email_notifications', 'available_voices',
            'bio', 'organization', 'role', 'avatar',
            'created_at', 'last_login'
        ]
        read_only_fields = [
            'id', 'email', 'subscription_tier', 'is_subscription_active',
            'documents_uploaded_this_month', 'questions_asked_this_month',
            'created_at', 'last_login'
        ]


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'bio', 'organization', 'role',
            'preferred_voice', 'preferred_language', 'auto_play_summaries',
            'email_notifications', 'avatar'
        ]
    
    def validate_preferred_voice(self, value):
        """Validate that the user can access the selected voice"""
        user = self.instance
        if user and value not in user.available_voices:
            raise serializers.ValidationError(
                "Selected voice is not available for your subscription tier"
            )
        return value


class ExtendedUserProfileSerializer(serializers.ModelSerializer):
    """Serializer for extended user profile"""
    
    class Meta:
        model = UserProfile
        fields = [
            'phone_number', 'date_of_birth', 'country', 'timezone',
            'default_summary_length', 'preferred_explanation_style',
            'total_documents_processed', 'total_questions_asked',
            'total_audio_time_listened'
        ]
        read_only_fields = [
            'total_documents_processed', 'total_questions_asked',
            'total_audio_time_listened'
        ]


class SubscriptionHistorySerializer(serializers.ModelSerializer):
    """Serializer for subscription history"""
    
    tier_display = serializers.CharField(source='get_tier_display', read_only=True)
    
    class Meta:
        model = SubscriptionHistory
        fields = [
            'id', 'tier', 'tier_display', 'start_date', 'end_date',
            'amount_paid', 'payment_method', 'is_active', 'created_at'
        ]


class SubscriptionUpgradeSerializer(serializers.Serializer):
    """Serializer for subscription upgrades"""
    
    TIER_CHOICES = [
        ('pro', 'Smart Learn'),
        ('edu', 'Classroom Learn'),
        ('enterprise', 'Institution Learn'),
    ]
    
    BILLING_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    tier = serializers.ChoiceField(choices=TIER_CHOICES)
    billing_cycle = serializers.ChoiceField(choices=BILLING_CHOICES, default='monthly')
    
    def validate_tier(self, value):
        """Validate that user can upgrade to this tier"""
        user = self.context['request'].user
        
        tier_hierarchy = ['free', 'pro', 'edu', 'enterprise']
        current_index = tier_hierarchy.index(user.subscription_tier)
        new_index = tier_hierarchy.index(value)
        
        if new_index <= current_index:
            raise serializers.ValidationError(
                "You can only upgrade to a higher tier"
            )
        
        return value


class UsageStatsSerializer(serializers.Serializer):
    """Serializer for user usage statistics"""
    
    documents_uploaded_this_month = serializers.IntegerField()
    questions_asked_this_month = serializers.IntegerField()
    monthly_document_limit = serializers.IntegerField()
    monthly_question_limit = serializers.IntegerField()
    documents_remaining = serializers.IntegerField()
    questions_remaining = serializers.IntegerField()
    subscription_tier = serializers.CharField()
    subscription_tier_display = serializers.CharField()
    days_until_reset = serializers.IntegerField()
    
    def to_representation(self, instance):
        """Calculate usage statistics"""
        from django.utils import timezone
        import calendar
        
        # Calculate days until month reset
        now = timezone.now()
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        days_until_reset = days_in_month - now.day + 1
        
        # Calculate remaining usage
        documents_remaining = max(0, instance.monthly_document_limit - instance.documents_uploaded_this_month)
        questions_remaining = max(0, instance.monthly_question_limit - instance.questions_asked_this_month)
        
        return {
            'documents_uploaded_this_month': instance.documents_uploaded_this_month,
            'questions_asked_this_month': instance.questions_asked_this_month,
            'monthly_document_limit': instance.monthly_document_limit,
            'monthly_question_limit': instance.monthly_question_limit,
            'documents_remaining': documents_remaining,
            'questions_remaining': questions_remaining,
            'subscription_tier': instance.subscription_tier,
            'subscription_tier_display': instance.get_subscription_tier_display(),
            'days_until_reset': days_until_reset,
        }


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change"""
    
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True)
    
    def validate_old_password(self, value):
        """Validate old password"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Invalid old password")
        return value
    
    def validate(self, attrs):
        """Validate new passwords match"""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs
    
    def save(self):
        """Update user password"""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class AccountDeactivationSerializer(serializers.Serializer):
    """Serializer for account deactivation"""
    
    password = serializers.CharField(write_only=True)
    reason = serializers.CharField(max_length=500, required=False)
    
    def validate_password(self, value):
        """Validate password for account deactivation"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Invalid password")
        return value
