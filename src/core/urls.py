from django.urls import path
from .views import DocumentUploadView, AudioStreamView

urlpatterns = [
    path('upload/', DocumentUploadView.as_view(), name='upload_document'),
    path('audio/<int:audio_id>/', AudioStreamView.as_view(), name='stream_audio'),
]