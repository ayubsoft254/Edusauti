from django.urls import path, include
from . import views

app_name = 'documents'

# Web URLs
web_urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('upload/', views.upload_document, name='upload'),
    path('<int:document_id>/', views.document_detail, name='detail'),
]

# API URLs
api_urlpatterns = [
    # Document CRUD
    path('', views.DocumentListCreateView.as_view(), name='document-list-create'),
    path('<int:pk>/', views.DocumentDetailView.as_view(), name='document-detail'),
    
    # Document audio
    path('<int:document_id>/audio/', views.DocumentAudioView.as_view(), name='document-audio'),
    path('<int:document_id>/regenerate-audio/', views.regenerate_audio, name='regenerate-audio'),
    
    # Document Q&A
    path('<int:document_id>/questions/', views.DocumentQuestionsView.as_view(), name='document-questions'),
    
    # Document sharing
    path('<int:document_id>/share/', views.DocumentShareView.as_view(), name='document-share'),
    path('shared/<str:share_token>/', views.shared_document_view, name='shared-document'),
    
    # User statistics
    path('stats/', views.user_stats, name='user-stats'),
]

urlpatterns = [
    path('', include(web_urlpatterns)),
    path('api/', include(api_urlpatterns)),
]