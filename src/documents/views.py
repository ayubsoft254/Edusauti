from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Document, Question, DocumentShare
from .serializers import (
    DocumentSerializer, DocumentListSerializer, AudioSummarySerializer,
    QuestionSerializer, QuestionCreateSerializer, DocumentShareSerializer
)


# Web Views
@login_required
def dashboard(request):
    """Main dashboard showing user's documents"""
    documents = Document.objects.filter(user=request.user).order_by('-created_at')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        documents = documents.filter(status=status_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        documents = documents.filter(title__icontains=search_query)
    
    # Pagination
    paginator = Paginator(documents, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    stats = {
        'total_documents': documents.count(),
        'completed_documents': documents.filter(status='completed').count(),
        'processing_documents': documents.filter(status__in=['uploaded', 'processing']).count(),
        'failed_documents': documents.filter(status__in=['failed', 'error']).count(),
    }
    
    context = {
        'documents': page_obj,
        'stats': stats,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    return render(request, 'documents/dashboard.html', context)


@login_required
def document_detail(request, document_id):
    """Document detail view with audio player and Q&A"""
    document = get_object_or_404(Document, id=document_id, user=request.user)
    audio_summary = document.audio_summaries.filter(status='completed').first()
    recent_questions = document.questions.filter(user=request.user).order_by('-asked_at')[:10]
    
    # Increment view count
    document.increment_view_count()
    
    # Process tags for template
    document_tags = []
    if document.tags:
        document_tags = [tag.strip() for tag in document.tags.split(',') if tag.strip()]
    
    context = {
        'document': document,
        'document_tags': document_tags,
        'audio_summary': audio_summary,
        'recent_questions': recent_questions,
    }
    return render(request, 'documents/detail.html', context)


@login_required
def upload_document(request):
    """Document upload view"""
    if request.method == 'POST':
        # Handle file upload via AJAX or form
        if request.FILES.get('file'):
            # Check if user can upload more documents
            if not request.user.can_upload_document:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return Response(
                        {'error': f'Monthly upload limit of {request.user.monthly_document_limit} documents reached.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                else:
                    messages.error(request, f'You have reached your monthly limit of {request.user.monthly_document_limit} documents.')
                    return render(request, 'documents/upload.html', {'limit_reached': True})
            
            try:
                # Create document instance
                document = Document(
                    user=request.user,
                    title=request.POST.get('title', request.FILES['file'].name),
                    description=request.POST.get('description', ''),
                    file=request.FILES['file'],
                    status='uploaded'
                )
                
                # Validate file type and size
                if not document.is_valid_file_type():
                    error_msg = 'Invalid file type. Please upload PDF, DOCX, TXT, or PPTX files.'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'error': error_msg}, status=400)
                    else:
                        messages.error(request, error_msg)
                        return render(request, 'documents/upload.html')
                
                if not document.is_valid_file_size():
                    error_msg = f'File size exceeds maximum limit of {document.MAX_FILE_SIZE // (1024*1024)}MB.'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'error': error_msg}, status=400)
                    else:
                        messages.error(request, error_msg)
                        return render(request, 'documents/upload.html')
                
                # Save the document
                document.save()
                
                # Increment user's document count
                request.user.increment_document_count()
                
                # Start document processing (you'll need to implement this)
                # TODO: Trigger async processing task
                # process_document_async.delay(document.id)
                
                # Return success response
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': 'Document uploaded successfully!',
                        'document_id': document.id,
                        'redirect_url': f'/documents/{document.id}/'
                    })
                else:
                    messages.success(request, 'Document uploaded successfully!')
                    return redirect('documents:document_detail', document_id=document.id)
                    
            except Exception as e:
                error_msg = f'Error uploading document: {str(e)}'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': error_msg}, status=500)
                else:
                    messages.error(request, error_msg)
                    return render(request, 'documents/upload.html')
        else:
            error_msg = 'No file selected for upload.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': error_msg}, status=400)
            else:
                messages.error(request, error_msg)
                return render(request, 'documents/upload.html')
    
    # Check if user can upload more documents
    if not request.user.can_upload_document:
        messages.error(request, f'You have reached your monthly limit of {request.user.monthly_document_limit} documents.')
        return render(request, 'documents/upload.html', {'limit_reached': True})
    
    return render(request, 'documents/upload.html')


# API Views
class DocumentListCreateView(generics.ListCreateAPIView):
    """API view for listing and creating documents"""
    
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        return Document.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return DocumentListSerializer
        return DocumentSerializer
    
    def create(self, request, *args, **kwargs):
        # Check if user can upload more documents
        if not request.user.can_upload_document:
            return Response(
                {'error': f'Monthly upload limit of {request.user.monthly_document_limit} documents reached.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super(DocumentListCreateView, self).create(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        document = serializer.save(user=self.request.user)
        
        # Increment user's document count
        self.request.user.increment_document_count()
        
        # TODO: Trigger async processing task
        # process_document_async.delay(document.id)


class DocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """API view for document detail operations"""
    
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Document.objects.filter(user=self.request.user)


class DocumentAudioView(generics.RetrieveAPIView):
    """API view for getting document audio summary"""
    
    serializer_class = AudioSummarySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        document_id = self.kwargs['document_id']
        document = get_object_or_404(Document, id=document_id, user=self.request.user)
        audio_summary = document.audio_summaries.filter(status='completed').first()
        
        if not audio_summary:
            raise Http404("Audio summary not found or not ready yet.")
        
        # Increment audio play count
        document.increment_audio_play_count()
        
        return audio_summary


class DocumentQuestionsView(generics.ListCreateAPIView):
    """API view for document questions"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        document_id = self.kwargs['document_id']
        document = get_object_or_404(Document, id=document_id, user=self.request.user)
        return Question.objects.filter(document=document, user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return QuestionCreateSerializer
        return QuestionSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        document_id = self.kwargs['document_id']
        context['document'] = get_object_or_404(Document, id=document_id, user=self.request.user)
        return context
    
    def create(self, request, *args, **kwargs):
        # Check if user can ask more questions
        if not request.user.can_ask_question:
            return Response(
                {'error': f'Monthly question limit of {request.user.monthly_question_limit} questions reached.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        response = super().create(request, *args, **kwargs)
        
        if response.status_code == status.HTTP_201_CREATED:
            # Increment user's question count
            request.user.increment_question_count()
            
            # Increment document question count
            document = self.get_serializer_context()['document']
            document.increment_question_count()
            
            # TODO: Process the question with AI and return answer
            
        return response


class DocumentShareView(generics.ListCreateAPIView):
    """API view for document sharing"""
    
    serializer_class = DocumentShareSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        document_id = self.kwargs['document_id']
        document = get_object_or_404(Document, id=document_id, user=self.request.user)
        return DocumentShare.objects.filter(document=document)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        document_id = self.kwargs['document_id']
        context['document'] = get_object_or_404(Document, id=document_id, user=self.request.user)
        return context


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def regenerate_audio(request, document_id):
    """API endpoint to regenerate audio summary"""
    document = get_object_or_404(Document, id=document_id, user=request.user)
    
    if not document.is_completed:
        return Response(
            {'error': 'Document processing is not completed yet.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get voice preferences from request
    voice_name = request.data.get('voice_name', request.user.preferred_voice)
    speech_rate = request.data.get('speech_rate', 'medium')
    speech_pitch = request.data.get('speech_pitch', 'medium')
    
    # TODO: Trigger audio regeneration task
    
    return Response({'message': 'Audio regeneration started.'}, status=status.HTTP_202_ACCEPTED)


@api_view(['GET'])
def shared_document_view(request, share_token):
    """API endpoint for accessing shared documents"""
    try:
        share = DocumentShare.objects.get(share_token=share_token, is_active=True)
        
        if share.is_expired:
            return Response({'error': 'Share link has expired.'}, status=status.HTTP_410_GONE)
        
        # Increment access count
        share.increment_access_count()
        
        # Return document data based on permissions
        document_data = DocumentListSerializer(share.document).data
        
        # Remove sensitive fields for shared view
        allowed_fields = ['id', 'title', 'description', 'summary_text', 'created_at']
        if not share.can_view:
            return Response({'error': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)
        
        response_data = {
            'document': {k: v for k, v in document_data.items() if k in allowed_fields},
            'permissions': {
                'can_view': share.can_view,
                'can_ask_questions': share.can_ask_questions,
                'can_download': share.can_download,
            }
        }
        
        return Response(response_data)
        
    except DocumentShare.DoesNotExist:
        return Response({'error': 'Invalid share link.'}, status=status.HTTP_404_NOT_FOUND)


# Utility API Views
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_stats(request):
    """API endpoint for user document statistics"""
    user = request.user
    documents = Document.objects.filter(user=user)
    
    stats = {
        'total_documents': documents.count(),
        'completed_documents': documents.filter(status='completed').count(),
        'processing_documents': documents.filter(status__in=['uploaded', 'processing']).count(),
        'failed_documents': documents.filter(status__in=['failed', 'error']).count(),
        'total_questions_asked': sum(doc.total_questions_asked for doc in documents),
        'total_audio_plays': sum(doc.audio_play_count for doc in documents),
        'monthly_usage': {
            'documents_uploaded': user.documents_uploaded_this_month,
            'questions_asked': user.questions_asked_this_month,
            'document_limit': user.monthly_document_limit,
            'question_limit': user.monthly_question_limit,
        }
    }
    
    return Response(stats)
