from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import DetailView, UpdateView
from django.utils import timezone
from django.db import models

# DRF imports
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.throttling import UserRateThrottle
from rest_framework.parsers import MultiPartParser, FormParser

# Local imports
from .models import User, UserProfile, SubscriptionHistory, BillingProfile
from .forms import UserProfileForm, ExtendedProfileForm, SubscriptionUpgradeForm, BillingProfileForm
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer,
    UserProfileUpdateSerializer, ExtendedUserProfileSerializer,
    SubscriptionHistorySerializer, SubscriptionUpgradeSerializer,
    UsageStatsSerializer, PasswordChangeSerializer, AccountDeactivationSerializer,
    BillingProfileSerializer
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
        'user': request.user,
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
        'user': request.user,
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
        'user': request.user,
        'profile': profile,
        'usage_percentage_docs': (user.documents_uploaded_this_month / user.monthly_document_limit * 100) if user.monthly_document_limit > 0 else 0,
        'usage_percentage_questions': (user.questions_asked_this_month / user.monthly_question_limit * 100) if user.monthly_question_limit > 0 else 0,
    }
    
    return render(request, 'users/usage_stats.html', context)


@login_required
def billing_view(request):
    """Billing and payment management view"""
    user = request.user
    
    # Get billing information
    billing_profile = getattr(user, 'billing_profile', None)
    subscription_history = SubscriptionHistory.objects.filter(user=user).order_by('-created_at')
    
    # Calculate current billing cycle info
    current_subscription = subscription_history.filter(is_active=True).first()
    
    # Get usage for current billing period
    if current_subscription:
        usage_start_date = current_subscription.start_date.date()
    else:
        # Use month start for free users
        from datetime import date
        today = date.today()
        usage_start_date = date(today.year, today.month, 1)
    
    # Calculate AI service costs (if ai_services app is available)
    try:
        from ai_services.utils import calculate_monthly_cost
        ai_costs = calculate_monthly_cost(user, usage_start_date.month, usage_start_date.year)
    except ImportError:
        ai_costs = {'total_cost': 0, 'costs_by_service': {}}
    
    # Calculate subscription costs
    subscription_cost = 0
    if current_subscription:
        subscription_cost = float(current_subscription.amount_paid)
    
    # Get upcoming charges
    upcoming_charges = []
    if current_subscription and current_subscription.is_active:
        next_billing_date = current_subscription.get_next_billing_date()
        if next_billing_date:
            upcoming_charges.append({
                'description': f'{current_subscription.get_tier_display()} Subscription',
                'amount': subscription_cost,
                'date': next_billing_date,
                'type': 'subscription'
            })
    
    # Add AI service costs to upcoming charges if significant
    if ai_costs['total_cost'] > 1.0:  # Only show if over $1
        upcoming_charges.append({
            'description': 'AI Services Usage',
            'amount': ai_costs['total_cost'],
            'date': usage_start_date.replace(day=1),  # First of next month
            'type': 'usage'
        })
    
    # Calculate totals
    total_this_month = subscription_cost + ai_costs['total_cost']
    
    # Get payment methods (placeholder - integrate with payment processor)
    payment_methods = []
    if billing_profile:
        payment_methods = billing_profile.get_payment_methods()
    
    context = {
        'user': user,
        'billing_profile': billing_profile,
        'current_subscription': current_subscription,
        'subscription_history': subscription_history[:10],  # Last 10 records
        'ai_costs': ai_costs,
        'subscription_cost': subscription_cost,
        'total_this_month': total_this_month,
        'upcoming_charges': upcoming_charges,
        'payment_methods': payment_methods,
        'usage_start_date': usage_start_date,
        'subscription_tiers': User.SUBSCRIPTION_CHOICES,
    }
    
    return render(request, 'users/billing.html', context)


@login_required
def billing_history_view(request):
    """Detailed billing history view"""
    user = request.user
    
    # Pagination
    from django.core.paginator import Paginator
    
    subscription_history = SubscriptionHistory.objects.filter(user=user).order_by('-created_at')
    paginator = Paginator(subscription_history, 20)  # 20 records per page
    
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate totals
    total_spent = subscription_history.aggregate(
        total=models.Sum('amount_paid')
    )['total'] or 0
    
    # Get yearly spending
    from datetime import datetime, timedelta
    current_year = datetime.now().year
    yearly_spending = subscription_history.filter(
        created_at__year=current_year
    ).aggregate(
        total=models.Sum('amount_paid')
    )['total'] or 0
    
    context = {
        'user': user,
        'page_obj': page_obj,
        'total_spent': total_spent,
        'yearly_spending': yearly_spending,
        'current_year': current_year,
    }
    
    return render(request, 'users/billing_history.html', context)


@login_required
def update_billing_info(request):
    """Update billing information"""
    user = request.user
    billing_profile = getattr(user, 'billing_profile', None)
    
    if request.method == 'POST':
        form = BillingProfileForm(request.POST, instance=billing_profile)
        if form.is_valid():
            billing_profile = form.save(commit=False)
            billing_profile.user = user
            billing_profile.save()
            
            messages.success(request, 'Billing information updated successfully!')
            return redirect('users:billing')
    else:
        form = BillingProfileForm(instance=billing_profile)
    
    context = {
        'form': form,
        'billing_profile': billing_profile,
    }
    
    return render(request, 'users/update_billing.html', context)


@login_required
def download_invoice(request, invoice_id):
    """Download invoice as PDF"""
    try:
        subscription = SubscriptionHistory.objects.get(
            id=invoice_id,
            user=request.user
        )
    except SubscriptionHistory.DoesNotExist:
        messages.error(request, 'Invoice not found.')
        return redirect('users:billing_history')
    
    # Generate PDF invoice
    from django.http import HttpResponse
    from django.template.loader import render_to_string
    import io
    
    try:
        # Try to use reportlab for PDF generation
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        
        # Create PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{subscription.id}.pdf"'
        
        # Create PDF document
        doc = SimpleDocTemplate(response, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph("EduSauti Invoice", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Invoice details
        invoice_data = [
            ['Invoice Number:', f'INV-{subscription.id:06d}'],
            ['Date:', subscription.created_at.strftime('%B %d, %Y')],
            ['Customer:', f'{request.user.get_full_name() or request.user.email}'],
            ['Subscription:', subscription.get_tier_display()],
            ['Amount:', f'${subscription.amount_paid:.2f}'],
            ['Status:', 'Paid' if subscription.is_active else 'Inactive'],
        ]
        
        invoice_table = Table(invoice_data, colWidths=[2*inch, 3*inch])
        invoice_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(invoice_table)
        story.append(Spacer(1, 12))
        
        # Footer
        footer = Paragraph("Thank you for using EduSauti!", styles['Normal'])
        story.append(footer)
        
        # Build PDF
        doc.build(story)
        
        return response
        
    except ImportError:
        # Fallback to HTML if reportlab is not available
        context = {
            'subscription': subscription,
            'user': user,
            'invoice_number': f'INV-{subscription.id:06d}',
        }
        
        html_content = render_to_string('users/invoice_template.html', context)
        response = HttpResponse(html_content, content_type='text/html')
        response['Content-Disposition'] = f'attachment; filename="invoice_{subscription.id}.html"'
        
        return response


@login_required 
def cancel_subscription(request):
    """Cancel current subscription"""
    if request.method == 'POST':
        user = request.user
        current_subscription = SubscriptionHistory.objects.filter(
            user=user, 
            is_active=True
        ).first()
        
        if current_subscription:
            # In a real app, you'd cancel with the payment processor here
            current_subscription.is_active = False
            current_subscription.save()
            
            # Downgrade user to free tier
            user.subscription_tier = 'free'
            user.subscription_expires_at = None
            user.save()
            
            messages.success(request, 'Subscription cancelled successfully. You will retain access until the end of your billing period.')
        else:
            messages.info(request, 'No active subscription found.')
        
        return redirect('users:billing')
    
    # Show confirmation page
    current_subscription = SubscriptionHistory.objects.filter(
        user=request.user, 
        is_active=True
    ).first()
    
    context = {
        'current_subscription': current_subscription,
    }
    
    return render(request, 'users/cancel_subscription.html', context)


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


# ===== API VIEWS FOR BILLING =====

class BillingInfoAPIView(generics.RetrieveUpdateAPIView):
    """API view for billing information"""
    serializer_class = BillingProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        billing_profile, created = BillingProfile.objects.get_or_create(
            user=self.request.user
        )
        return billing_profile


class BillingHistoryAPIView(generics.ListAPIView):
    """API view for billing history"""
    serializer_class = SubscriptionHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None  # Disable pagination for API
    
    def get_queryset(self):
        return SubscriptionHistory.objects.filter(
            user=self.request.user
        ).order_by('-created_at')


class CurrentSubscriptionAPIView(generics.RetrieveAPIView):
    """API view for current subscription details"""
    serializer_class = SubscriptionHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return SubscriptionHistory.objects.filter(
            user=self.request.user,
            is_active=True
        ).first()
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance is None:
            return Response({
                'detail': 'No active subscription found',
                'subscription_tier': request.user.subscription_tier,
                'is_active': False
            }, status=status.HTTP_200_OK)
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class UsageCostsAPIView(generics.GenericAPIView):
    """API view for usage costs breakdown"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        
        try:
            if month:
                month = int(month)
            if year:
                year = int(year)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid month or year parameter'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from ai_services.utils import calculate_monthly_cost
            costs = calculate_monthly_cost(user, month, year)
            return Response(costs)
        except ImportError:
            return Response({
                'total_cost': 0,
                'costs_by_service': {},
                'message': 'AI services not available'
            })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cancel_subscription_api(request):
    """API endpoint to cancel subscription"""
    user = request.user
    current_subscription = SubscriptionHistory.objects.filter(
        user=user,
        is_active=True
    ).first()
    
    if not current_subscription:
        return Response(
            {'error': 'No active subscription found'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Cancel subscription
    current_subscription.is_active = False
    current_subscription.save()
    
    # Downgrade user
    user.subscription_tier = 'free'
    user.subscription_expires_at = None
    user.save()
    
    return Response({
        'message': 'Subscription cancelled successfully',
        'new_tier': 'free'
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def billing_summary_api(request):
    """API endpoint for billing summary"""
    user = request.user
    
    # Get current subscription
    current_subscription = SubscriptionHistory.objects.filter(
        user=user,
        is_active=True
    ).first()
    
    # Calculate current month costs
    try:
        from ai_services.utils import calculate_monthly_cost
        from datetime import date
        today = date.today()
        ai_costs = calculate_monthly_cost(user, today.month, today.year)
    except ImportError:
        ai_costs = {'total_cost': 0}
    
    # Calculate subscription cost
    subscription_cost = 0
    if current_subscription:
        subscription_cost = float(current_subscription.amount_paid)
    
    # Get total spending
    total_spent = SubscriptionHistory.objects.filter(
        user=user
    ).aggregate(
        total=models.Sum('amount_paid')
    )['total'] or 0
    
    return Response({
        'current_subscription': SubscriptionHistorySerializer(current_subscription).data if current_subscription else None,
        'subscription_cost': subscription_cost,
        'ai_usage_cost': ai_costs['total_cost'],
        'total_this_month': subscription_cost + ai_costs['total_cost'],
        'total_spent_ever': float(total_spent),
        'subscription_tier': user.subscription_tier,
        'next_billing_date': current_subscription.get_next_billing_date() if current_subscription else None,
    })
