from django import forms
from allauth.account.forms import SignupForm, LoginForm
from .models import User, UserProfile, BillingProfile


class CustomSignupForm(SignupForm):
    """Custom signup form with additional fields"""
    
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent',
            'placeholder': 'First Name'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent',
            'placeholder': 'Last Name'
        })
    )
    organization = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent',
            'placeholder': 'Organization (Optional)'
        })
    )
    role = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent',
            'placeholder': 'Role/Title (Optional)'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Style existing fields
        self.fields['email'].widget.attrs.update({
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent',
            'placeholder': 'Email Address'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent',
            'placeholder': 'Password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent',
            'placeholder': 'Confirm Password'
        })
        
        # Update field order
        self.field_order = ['first_name', 'last_name', 'email', 'organization', 'role', 'password1', 'password2']
    
    def save(self, request):
        user = super().save(request)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.organization = self.cleaned_data.get('organization', '')
        user.role = self.cleaned_data.get('role', '')
        user.save()
        
        # Create user profile
        UserProfile.objects.create(user=user)
        
        return user


class CustomLoginForm(LoginForm):
    """Custom login form with styling"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Style fields
        self.fields['login'].widget.attrs.update({
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent',
            'placeholder': 'Email Address'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent',
            'placeholder': 'Password'
        })
        
        # Update remember me checkbox
        self.fields['remember'].widget.attrs.update({
            'class': 'h-4 w-4 text-yellow-600 focus:ring-yellow-500 border-gray-300 rounded'
        })


class UserProfileForm(forms.ModelForm):
    """Form for updating user profile"""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'bio', 'organization', 'role',
            'preferred_voice', 'preferred_language', 'auto_play_summaries',
            'email_notifications', 'avatar'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent',
                'rows': 3
            }),
            'organization': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent'
            }),
            'role': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent'
            }),
            'preferred_voice': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent'
            }),
            'preferred_language': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent'
            }),
            'auto_play_summaries': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-yellow-600 focus:ring-yellow-500 border-gray-300 rounded'
            }),
            'email_notifications': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-yellow-600 focus:ring-yellow-500 border-gray-300 rounded'
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-yellow-50 file:text-yellow-700 hover:file:bg-yellow-100'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set voice choices based on user's subscription
        if self.instance and hasattr(self.instance, 'available_voices'):
            voice_choices = [(voice, voice.replace('Neural', '').replace('-', ' ')) 
                           for voice in self.instance.available_voices]
            self.fields['preferred_voice'].choices = voice_choices
        
        # Language choices
        self.fields['preferred_language'].choices = [
            ('en-US', 'English (US)'),
            ('en-GB', 'English (UK)'),
            ('es-ES', 'Spanish'),
            ('fr-FR', 'French'),
            ('de-DE', 'German'),
        ]


class ExtendedProfileForm(forms.ModelForm):
    """Form for extended user profile information"""
    
    class Meta:
        model = UserProfile
        fields = [
            'phone_number', 'date_of_birth', 'country', 'timezone',
            'default_summary_length', 'preferred_explanation_style'
        ]
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent',
                'type': 'date'
            }),
            'country': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent'
            }),
            'timezone': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent'
            }),
            'default_summary_length': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent'
            }),
            'preferred_explanation_style': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Common timezone choices
        self.fields['timezone'].choices = [
            ('UTC', 'UTC'),
            ('America/New_York', 'Eastern Time'),
            ('America/Chicago', 'Central Time'),
            ('America/Denver', 'Mountain Time'),
            ('America/Los_Angeles', 'Pacific Time'),
            ('Europe/London', 'London'),
            ('Europe/Paris', 'Paris'),
            ('Africa/Nairobi', 'Nairobi'),
            ('Asia/Tokyo', 'Tokyo'),
            ('Australia/Sydney', 'Sydney'),
        ]


class SubscriptionUpgradeForm(forms.Form):
    """Form for subscription upgrades"""
    
    TIER_CHOICES = [
        ('pro', 'Smart Learn - $12/month'),
        ('edu', 'Classroom Learn - $49/month'),
        ('enterprise', 'Institution Learn - Contact Sales'),
    ]
    
    tier = forms.ChoiceField(
        choices=TIER_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'h-4 w-4 text-yellow-600 focus:ring-yellow-500 border-gray-300'
        })
    )
    
    billing_cycle = forms.ChoiceField(
        choices=[
            ('monthly', 'Monthly'),
            ('yearly', 'Yearly (Save 20%)'),
        ],
        initial='monthly',
        widget=forms.RadioSelect(attrs={
            'class': 'h-4 w-4 text-yellow-600 focus:ring-yellow-500 border-gray-300'
        })
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Remove current tier from choices
        if user and user.subscription_tier != 'free':
            updated_choices = [choice for choice in self.TIER_CHOICES 
                             if choice[0] != user.subscription_tier]
            self.fields['tier'].choices = updated_choices


class BillingProfileForm(forms.ModelForm):
    """Form for billing profile information"""
    
    class Meta:
        model = BillingProfile
        fields = [
            'company_name', 'billing_address_line1', 'billing_address_line2',
            'billing_city', 'billing_state', 'billing_country', 'billing_postal_code',
            'tax_id', 'preferred_currency'
        ]
        
        widgets = {
            'company_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Company name (optional)'
            }),
            'billing_address_line1': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Address line 1'
            }),
            'billing_address_line2': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Address line 2 (optional)'
            }),
            'billing_city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City'
            }),
            'billing_state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'State/Province'
            }),
            'billing_country': forms.Select(attrs={
                'class': 'form-control'
            }),
            'billing_postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Postal code'
            }),
            'tax_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tax ID (optional)'
            }),
            'preferred_currency': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make all fields optional by default
        for field in self.fields.values():
            field.required = False
        
        # Make required fields actually required
        required_fields = ['billing_address_line1', 'billing_city', 'billing_country']
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True


class PaymentMethodForm(forms.Form):
    """Form for adding payment methods"""
    
    CARD_TYPES = [
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('amex', 'American Express'),
        ('discover', 'Discover'),
    ]
    
    card_number = forms.CharField(
        max_length=19,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '1234 5678 9012 3456',
            'pattern': r'[0-9\s]{13,19}',
        })
    )
    
    expiry_month = forms.ChoiceField(
        choices=[(i, f'{i:02d}') for i in range(1, 13)],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    expiry_year = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    cvv = forms.CharField(
        max_length=4,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'CVV',
            'pattern': r'[0-9]{3,4}',
        })
    )
    
    cardholder_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Name on card'
        })
    )
    
    is_default = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Generate year choices (current year + 10 years)
        from datetime import datetime
        current_year = datetime.now().year
        year_choices = [(year, str(year)) for year in range(current_year, current_year + 11)]
        self.fields['expiry_year'].choices = year_choices
    
    def clean_card_number(self):
        card_number = self.cleaned_data['card_number']
        # Remove spaces and validate
        card_number = card_number.replace(' ', '')
        
        if not card_number.isdigit():
            raise forms.ValidationError('Card number must contain only numbers')
        
        if len(card_number) < 13 or len(card_number) > 19:
            raise forms.ValidationError('Invalid card number length')
        
        return card_number
    
    def clean_cvv(self):
        cvv = self.cleaned_data['cvv']
        
        if not cvv.isdigit():
            raise forms.ValidationError('CVV must contain only numbers')
        
        if len(cvv) < 3 or len(cvv) > 4:
            raise forms.ValidationError('CVV must be 3 or 4 digits')
        
        return cvv
    
    def clean(self):
        cleaned_data = super().clean()
        expiry_month = cleaned_data.get('expiry_month')
        expiry_year = cleaned_data.get('expiry_year')
        
        if expiry_month and expiry_year:
            from datetime import datetime
            current_date = datetime.now()
            expiry_date = datetime(int(expiry_year), int(expiry_month), 1)
            
            if expiry_date < current_date:
                raise forms.ValidationError('Card has expired')
        
        return cleaned_data
