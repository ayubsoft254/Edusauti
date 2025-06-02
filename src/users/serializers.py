from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, UserProfile, Subscription


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile model"""
    
    class Meta:
        model = UserProfile
        fields = [
            'avatar', 'bio', 'institution', 'department', 'role',
            'timezone', 'date_format_preference', 'allow_analytics',
            'allow_marketing_emails'
        ]


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)
    is_premium_user = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'organization', 'preferred_language', 'preferred_voice',
            'subscription_tier', 'is_subscription_active', 'is_premium_user',
            'documents_uploaded_this_month', 'questions_asked_this_month',
            'email_notifications', 'is_verified', 'date_joined', 'profile'
        ]
        read_only_fields = [
            'id', 'username', 'subscription_tier', 'is_subscription_active',
            'documents_uploaded_this_month', 'questions_asked_this_month',
            'is_verified', 'date_joined'
        ]


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'phone_number', 'organization', 'password', 'password_confirm'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        
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
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('Account is disabled')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Must include email and password')
        
        return attrs


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change"""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect')
        return value
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs
    
    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for Subscription model"""
    tier_display = serializers.CharField(source='get_tier_display', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'tier', 'tier_display', 'amount', 'currency',
            'billing_cycle', 'start_date', 'end_date', 'is_active',
            'is_expired', 'auto_renew', 'cancelled_at', 'created_at'
        ]
        read_only_fields = [
            'id', 'is_expired', 'cancelled_at', 'created_at'
        ]


class UserDashboardSerializer(serializers.ModelSerializer):
    """Serializer for user dashboard data"""
    profile = UserProfileSerializer(read_only=True)
    current_subscription = serializers.SerializerMethodField()
    usage_stats = serializers.SerializerMethodField()
    subscription_limits = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'email', 'subscription_tier',
            'is_subscription_active', 'profile', 'current_subscription',
            'usage_stats', 'subscription_limits'
        ]
    
    def get_current_subscription(self, obj):
        current_sub = obj.subscriptions.filter(is_active=True).first()
        if current_sub:
            return SubscriptionSerializer(current_sub).data
        return None
    
    def get_usage_stats(self, obj):
        return {
            'documents_uploaded': obj.documents_uploaded_this_month,
            'questions_asked': obj.questions_asked_this_month,
            'last_reset': obj.last_usage_reset
        }
    
    def get_subscription_limits(self, obj):
        from .models import SubscriptionTier
        
        limits = {
            SubscriptionTier.FREE: {
                'documents': 5,
                'questions_per_doc': 5,
                'voice_options': 1,
                'summary_length': 1000
            },
            SubscriptionTier.PRO: {
                'documents': 50,
                'questions_per_doc': 'unlimited',
                'voice_options': 5,
                'summary_length': 'unlimited'
            },
            SubscriptionTier.EDU: {
                'documents': 200,
                'questions_per_doc': 'unlimited',
                'voice_options': 'multiple',
                'summary_length': 'unlimited'
            },
            SubscriptionTier.ENTERPRISE: {
                'documents': 'unlimited',
                'questions_per_doc': 'unlimited',
                'voice_options': 'custom',
                'summary_length': 'unlimited'
            }
        }
        
        return limits.get(obj.subscription_tier, limits[SubscriptionTier.FREE])
