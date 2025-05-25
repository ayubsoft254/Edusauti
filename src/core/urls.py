from django.urls import path
from .views import DocumentUploadView, AudioStreamView, SecureDocumentUploadView

urlpatterns = [
    path('upload/', DocumentUploadView.as_view(), name='document-upload'),
    path('secure-upload/', SecureDocumentUploadView.as_view(), name='secure-document-upload'),
    path('audio/<int:audio_id>/', AudioStreamView.as_view(), name='audio-stream'),
]