from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


def home(request):
    """Home page view"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'home.html')


def landing_page(request):
    """Landing page with features and pricing"""
    return render(request, 'landing.html')


@login_required
def dashboard_redirect(request):
    """Redirect to appropriate dashboard based on user type"""
    return redirect('dashboard')