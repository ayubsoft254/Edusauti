
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .models import Document

class SignUpView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        form = UserCreationForm()
        return render(request, 'registration/signup.html', {'form': form})
    
    def post(self, request):
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            return redirect('dashboard')
        return render(request, 'registration/signup.html', {'form': form})

@method_decorator(login_required, name='dispatch')
class DashboardView(View):
    def get(self, request):
        return render(request, 'dashboard.html')

@method_decorator(login_required, name='dispatch')
class PlayerView(View):
    def get(self, request, document_id):
        try:
            document = Document.objects.get(id=document_id, user=request.user)
            summary = document.summary
            audio_file = summary.audiofile
            return render(request, 'player.html', {
                'document': document,
                'summary': summary,
                'audio_file': audio_file
            })
        except Document.DoesNotExist:
            return redirect('dashboard')