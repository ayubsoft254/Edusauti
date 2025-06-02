from django.shortcuts import render
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, permissions, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from .models import User, UserProfile, Subscription
from .serializers import (
    UserSerializer, UserRegistrationSerializer, UserLoginSerializer,
    PasswordChangeSerializer, UserProfileSerializer, SubscriptionSerializer,
    UserDashboardSerializer
)


class UserRegistrationView(APIView):
    """API view for user registration"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Create auth token
            token, created = Token.objects.get_or_create(user=user)
            
            return Response({
                'message': 'User registered successfully',
                'user': UserSerializer(user).data,
                'token': token.key
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    """API view for user login"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            # Get or create auth token
            token, created = Token.objects.get_or_create(user=user)
            
            return Response({
                'message': 'Login successful',
                'user': UserSerializer(user).data,
                'token': token.key
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLogoutView(APIView):
    """API view for user logout"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            # Delete the user's token
            request.user.auth_token.delete()
            return Response({
                'message': 'Logged out successfully'
            }, status=status.HTTP_200_OK)
        except:
            return Response({
                'error': 'Error logging out'
            }, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """API view for user profile"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class UserProfileDetailView(generics.RetrieveUpdateAPIView):
    """API view for user profile details"""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


class PasswordChangeView(APIView):
    """API view for password change"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Password changed successfully'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserDashboardView(APIView):
    """API view for user dashboard data"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        serializer = UserDashboardSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SubscriptionListView(generics.ListAPIView):
    """API view for user's subscription history"""
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user)


class SubscriptionDetailView(generics.RetrieveAPIView):
    """API view for subscription details"""
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cancel_subscription(request, subscription_id):
    """API endpoint to cancel a subscription"""
    try:
        subscription = Subscription.objects.get(
            id=subscription_id,
            user=request.user,
            is_active=True
        )
        subscription.cancel_subscription()
        
        return Response({
            'message': 'Subscription cancelled successfully'
        }, status=status.HTTP_200_OK)
    
    except Subscription.DoesNotExist:
        return Response({
            'error': 'Subscription not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def usage_stats(request):
    """API endpoint to get user usage statistics"""
    user = request.user
    
    # Check if monthly usage needs to be reset
    from django.utils import timezone
    from datetime import timedelta
    
    if timezone.now() - user.last_usage_reset > timedelta(days=30):
        user.reset_monthly_usage()
    
    return Response({
        'documents_uploaded': user.documents_uploaded_this_month,
        'questions_asked': user.questions_asked_this_month,
        'can_upload_document': user.can_upload_document(),
        'can_ask_question': user.can_ask_question(),
        'subscription_tier': user.get_subscription_tier_display(),
        'is_premium': user.is_premium_user
    }, status=status.HTTP_200_OK)


# Template Views (for web interface)
@login_required
def dashboard_view(request):
    """Dashboard view for authenticated users"""
    context = {
        'user': request.user,
        'subscription': request.user.subscriptions.filter(is_active=True).first(),
        'documents_count': request.user.documents_uploaded_this_month,
        'questions_count': request.user.questions_asked_this_month,
    }
    return render(request, 'dashboard/dashboard.html', context)


@login_required
def profile_view(request):
    """Profile view for authenticated users"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    context = {
        'user': request.user,
        'profile': profile,
    }
    return render(request, 'account/profile.html', context)


def pricing_view(request):
    """Pricing page view"""
    context = {
        'tiers': [
            {
                'name': 'Starter Learn',
                'price': 'Free',
                'features': [
                    '5 document uploads/month',
                    'Basic voice (1-2 choices)',
                    'Up to 5 questions per document',
                    'Text summary view + 5 min audio per doc',
                    'Summary length limited (max 1,000 words/doc)'
                ]
            },
            {
                'name': 'Smart Learn',
                'price': '$15/month',
                'features': [
                    '50 documents/month',
                    '5 premium voices',
                    'Unlimited Q&A per document',
                    'Full-length summary with deeper explanation',
                    'Real-time interactive chat (text and voice)',
                    'Save Q&A history',
                    'Basic personalization'
                ]
            },
            {
                'name': 'Classroom Learn',
                'price': '$49/month',
                'features': [
                    '200 document uploads/month (shared)',
                    'Access for up to 30 users',
                    'Teacher dashboard with usage stats',
                    'Class-specific voice packs',
                    'Real-time questions for class presentations',
                    'Full Q&A and summary export to PDF or audio',
                    'Admin controls for access management'
                ]
            },
            {
                'name': 'Institution Learn',
                'price': 'Custom',
                'features': [
                    'Unlimited documents',
                    'Unlimited users',
                    'Custom voices',
                    'API access for platform integration',
                    'Real-time analytics & reporting',
                    'SLA-backed support',
                    'White-label options'
                ]
            }
        ]
    }
    return render(request, 'pricing.html', context)
