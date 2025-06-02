from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import DetailView, UpdateView
from django.utils import timezone

# DRF imports
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.throttling import UserRateThrottle
from rest_framework.parsers import MultiPartParser, FormParser

# Local imports
from .models import User, UserProfile, SubscriptionHistory
from .forms import UserProfileForm, ExtendedProfileForm, SubscriptionUpgradeForm
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer,
    UserProfileUpdateSerializer, ExtendedUserProfileSerializer,
    SubscriptionHistorySerializer, SubscriptionUpgradeSerializer,
    UsageStatsSerializer, PasswordChangeSerializer, AccountDeactivationSerializer
)


# ===== WEB VIEWS =====

@login_required
def dashboard_view(request):
    """User dashboard view"""
    user = request.user
    
    # Get recent activity data
    recent_documents = user.documents.all()[:5] if hasattr(user, 'documents') else []
    
    # Calculate usage statistics
    context = {
        'user': user,
        'recent_documents': recent_documents,
        'documents_used': user.documents_uploaded_this_month,
        'documents_limit': user.monthly_document_limit,
        'questions_used': user.questions_asked_this_month,
        'questions_limit': user.monthly_question_limit,
        'subscription_tier': user.get_subscription_tier_display(),
        'has_premium': user.has_premium_features,
    }
    
    return render(request, 'users/dashboard.html', context)


class ProfileView(LoginRequiredMixin, DetailView):
    """User profile view"""
    model = User
    template_name = 'users/profile.html'
    context_object_name = 'profile_user'
    
    def get_object(self):
        return self.request.user


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Update user profile view"""
    model = User
    form_class = UserProfileForm
    template_name = 'users/profile_edit.html'
    success_url = reverse_lazy('users:profile')
    
    def get_object(self):
        return self.request.user
    
    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully!')
        return super().form_valid(form)


@login_required
def settings_view(request):
    """User settings view"""
    user = request.user
    profile = getattr(user, 'profile', None)
    
    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, request.FILES, instance=user)
        profile_form = ExtendedProfileForm(request.POST, instance=profile) if profile else None
        
        if user_form.is_valid() and (not profile_form or profile_form.is_valid()):
            user_form.save()
            if profile_form:
                profile_form.save()
            messages.success(request, 'Settings updated successfully!')
            return redirect('users:settings')
    else:
        user_form = UserProfileForm(instance=user)
        profile_form = ExtendedProfileForm(instance=profile) if profile else None
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }
    
    return render(request, 'users/settings.html', context)


@login_required
def subscription_view(request):
    """Subscription management view"""
    user = request.user
    subscription_history = SubscriptionHistory.objects.filter(user=user).order_by('-created_at')
    
    context = {
        'user': user,
        'subscription_history': subscription_history,
        'upgrade_form': SubscriptionUpgradeForm(user=user),
    }
    
    return render(request, 'users/subscription.html', context)


@login_required
def upgrade_subscription(request):
    """Handle subscription upgrade"""
    if request.method == 'POST':
        form = SubscriptionUpgradeForm(request.POST, user=request.user)
        if form.is_valid():
            tier = form.cleaned_data['tier']
            billing_cycle = form.cleaned_data['billing_cycle']
            
            # In a real app, you'd integrate with a payment processor here
            # For now, we'll just simulate the upgrade
            
            duration_months = 12 if billing_cycle == 'yearly' else 1
            request.user.update_subscription(tier, duration_months)
            
            # Create subscription history record
            SubscriptionHistory.objects.create(
                user=request.user,
                tier=tier,
                start_date=timezone.now(),
                amount_paid=0,  # Set based on actual payment
                payment_method='demo',
                is_active=True
            )
            
            messages.success(request, f'Successfully upgraded to {tier.title()} plan!')
            return redirect('users:subscription')
    
    return redirect('users:subscription')


@login_required
def usage_stats_view(request):
    """User usage statistics view"""
    user = request.user
    
    # Get extended usage stats if profile exists
    profile = getattr(user, 'profile', None)
    
    context = {
        'user': user,
        'profile': profile,
        'usage_percentage_docs': (user.documents_uploaded_this_month / user.monthly_document_limit * 100) if user.monthly_document_limit > 0 else 0,
        'usage_percentage_questions': (user.questions_asked_this_month / user.monthly_question_limit * 100) if user.monthly_question_limit > 0 else 0,
    }
    
    return render(request, 'users/usage_stats.html', context)


# ===== API VIEWS =====

class UserRegistrationAPIView(generics.CreateAPIView):
    """API view for user registration"""
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [UserRateThrottle]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Create authentication token
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'message': 'User created successfully',
            'user': UserProfileSerializer(user).data,
            'token': token.key
        }, status=status.HTTP_201_CREATED)


class UserLoginAPIView(generics.GenericAPIView):
    """API view for user login"""
    serializer_class = UserLoginSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [UserRateThrottle]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        
        # Update last login IP
        user.last_login_ip = self.get_client_ip(request)
        user.save(update_fields=['last_login_ip'])
        
        return Response({
            'message': 'Login successful',
            'user': UserProfileSerializer(user).data,
            'token': token.key
        })
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserLogoutAPIView(generics.GenericAPIView):
    """API view for user logout"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            # Delete the user's token
            request.user.auth_token.delete()
            return Response({'message': 'Logout successful'})
        except:
            return Response({'error': 'Error logging out'}, 
                          status=status.HTTP_400_BAD_REQUEST)


class UserProfileAPIView(generics.RetrieveUpdateAPIView):
    """API view for user profile"""
    serializer_class = UserProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_object(self):
        return self.request.user
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return UserProfileSerializer
        return UserProfileUpdateSerializer


class ExtendedProfileAPIView(generics.RetrieveUpdateAPIView):
    """API view for extended user profile"""
    serializer_class = ExtendedUserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


class SubscriptionHistoryAPIView(generics.ListAPIView):
    """API view for subscription history"""
    serializer_class = SubscriptionHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return SubscriptionHistory.objects.filter(user=self.request.user)


class SubscriptionUpgradeAPIView(generics.GenericAPIView):
    """API view for subscription upgrade"""
    serializer_class = SubscriptionUpgradeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        tier = serializer.validated_data['tier']
        billing_cycle = serializer.validated_data['billing_cycle']
        
        # In a real app, integrate with payment processor here
        # For demo purposes, we'll just update the subscription
        
        duration_months = 12 if billing_cycle == 'yearly' else 1
        request.user.update_subscription(tier, duration_months)
        
        # Create subscription history
        SubscriptionHistory.objects.create(
            user=request.user,
            tier=tier,
            start_date=timezone.now(),
            amount_paid=0,  # Set based on actual payment
            payment_method='api',
            is_active=True
        )
        
        return Response({
            'message': f'Successfully upgraded to {tier} plan',
            'user': UserProfileSerializer(request.user).data
        })


class UsageStatsAPIView(generics.GenericAPIView):
    """API view for usage statistics"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        user.reset_monthly_usage_if_needed()
        
        serializer = UsageStatsSerializer(user)
        return Response(serializer.data)


class PasswordChangeAPIView(generics.GenericAPIView):
    """API view for password change"""
    serializer_class = PasswordChangeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({'message': 'Password changed successfully'})


class AccountDeactivationAPIView(generics.GenericAPIView):
    """API view for account deactivation"""
    serializer_class = AccountDeactivationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Deactivate user account
        user = request.user
        user.is_active = False
        user.save()
        
        # Delete auth token
        try:
            user.auth_token.delete()
        except:
            pass
        
        return Response({'message': 'Account deactivated successfully'})


# ===== UTILITY VIEWS =====

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_limits_api(request):
    """Check user limits for documents and questions"""
    user = request.user
    user.reset_monthly_usage_if_needed()
    
    return Response({
        'can_upload_document': user.can_upload_document,
        'can_ask_question': user.can_ask_question,
        'documents_remaining': max(0, user.monthly_document_limit - user.documents_uploaded_this_month),
        'questions_remaining': max(0, user.monthly_question_limit - user.questions_asked_this_month),
        'subscription_tier': user.subscription_tier,
        'has_premium_features': user.has_premium_features,
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def increment_usage_api(request):
    """Increment usage counters"""
    user = request.user
    usage_type = request.data.get('type')  # 'document' or 'question'
    
    if usage_type == 'document':
        if not user.can_upload_document:
            return Response(
                {'error': 'Document upload limit reached'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        user.increment_document_count()
        return Response({'message': 'Document count incremented'})
    
    elif usage_type == 'question':
        if not user.can_ask_question:
            return Response(
                {'error': 'Question limit reached'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        user.increment_question_count()
        return Response({'message': 'Question count incremented'})
    
    return Response(
        {'error': 'Invalid usage type'}, 
        status=status.HTTP_400_BAD_REQUEST
    )
