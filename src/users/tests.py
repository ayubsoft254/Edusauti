from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from .models import User, UserProfile, Subscription, SubscriptionTier

User = get_user_model()


class UserModelTest(TestCase):
    """Test cases for User model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )
    
    def test_user_creation(self):
        """Test user creation"""
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertEqual(self.user.full_name, 'Test User')
        self.assertEqual(self.user.subscription_tier, SubscriptionTier.FREE)
    
    def test_user_profile_creation(self):
        """Test that user profile is created automatically"""
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertIsInstance(self.user.profile, UserProfile)
    
    def test_can_upload_document_free_tier(self):
        """Test document upload limits for free tier"""
        self.assertTrue(self.user.can_upload_document())
        
        # Set to limit
        self.user.documents_uploaded_this_month = 5
        self.assertFalse(self.user.can_upload_document())
    
    def test_can_ask_question_free_tier(self):
        """Test question limits for free tier"""
        self.assertTrue(self.user.can_ask_question())
        
        # Set to limit
        self.user.questions_asked_this_month = 25
        self.assertFalse(self.user.can_ask_question())
    
    def test_is_premium_user(self):
        """Test premium user detection"""
        self.assertFalse(self.user.is_premium_user)
        
        self.user.subscription_tier = SubscriptionTier.PRO
        self.assertTrue(self.user.is_premium_user)


class UserAPITest(APITestCase):
    """Test cases for User API endpoints"""
    
    def test_user_registration(self):
        """Test user registration API"""
        url = reverse('users:api_register')
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'newpass123',
            'password_confirm': 'newpass123'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertTrue(User.objects.filter(email='newuser@example.com').exists())
    
    def test_user_login(self):
        """Test user login API"""
        user = User.objects.create_user(
            username='loginuser',
            email='login@example.com',
            password='loginpass123'
        )
        
        url = reverse('users:api_login')
        data = {
            'email': 'login@example.com',
            'password': 'loginpass123'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
    
    def test_user_profile_access(self):
        """Test authenticated user profile access"""
        user = User.objects.create_user(
            username='profileuser',
            email='profile@example.com',
            password='profilepass123'
        )
        token = Token.objects.create(user=user)
        
        url = reverse('users:api_profile')
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'profile@example.com')
    
    def test_dashboard_data(self):
        """Test dashboard data API"""
        user = User.objects.create_user(
            username='dashuser',
            email='dash@example.com',
            password='dashpass123'
        )
        token = Token.objects.create(user=user)
        
        url = reverse('users:api_dashboard')
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('usage_stats', response.data)
        self.assertIn('subscription_limits', response.data)


class SubscriptionModelTest(TestCase):
    """Test cases for Subscription model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='subuser',
            email='sub@example.com',
            password='subpass123'
        )
    
    def test_subscription_creation(self):
        """Test subscription creation"""
        from django.utils import timezone
        from datetime import timedelta
        
        subscription = Subscription.objects.create(
            user=self.user,
            tier=SubscriptionTier.PRO,
            amount=15.00,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30)
        )
        
        self.assertEqual(subscription.tier, SubscriptionTier.PRO)
        self.assertEqual(subscription.amount, 15.00)
        self.assertFalse(subscription.is_expired)
    
    def test_subscription_cancellation(self):
        """Test subscription cancellation"""
        from django.utils import timezone
        from datetime import timedelta
        
        subscription = Subscription.objects.create(
            user=self.user,
            tier=SubscriptionTier.PRO,
            amount=15.00,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            is_active=True
        )
        
        subscription.cancel_subscription()
        
        self.assertFalse(subscription.is_active)
        self.assertFalse(subscription.auto_renew)
        self.assertIsNotNone(subscription.cancelled_at)
        
        # Check user subscription status
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_subscription_active)
