import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import StreamingHttpResponse
from .models import Document, Summary, AudioFile
from .document_processing import process_document
from .summarization import generate_summary
from .speech_service import generate_audio
from .azure_clients import get_storage_client
from asgiref.sync import sync_to_async
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from django.views.generic import TemplateView
from django.shortcuts import render
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from .db_optimization import CachedDocument

class DocumentUploadView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    async def post(self, request):
        try:
            # Save uploaded file synchronously first
            file_obj = request.FILES['file']
            title = request.POST.get('title', file_obj.name)
            
            # Use sync_to_async for database operations
            @sync_to_async
            def save_document():
                doc = CachedDocument(
                    user=request.user,
                    title=title,
                    file=file_obj
                )
                doc.save()
                return doc
            
            document = await save_document()
            
            # Process document (async)
            summary_instance = await process_document(document)
            
            # Generate summary
            summary_text = await generate_summary(summary_instance.text)
            summary_instance.text = summary_text
            summary_instance.save()
            
            # Generate audio
            voice_type = request.POST.get('voice_type', 'en-US-JennyNeural')
            audio_file = await generate_audio(summary_instance, voice_type)
            
            return Response({
                'document_id': document.id,
                'title': document.title,
                'summary': summary_text,
                'audio_url': f"/api/audio/{audio_file.id}/"
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Document upload error: {str(e)}")
            
            return Response(
                {'error': f"Upload failed: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AudioStreamView(APIView):
    def get(self, request, audio_id):
        try:
            audio_file = AudioFile.objects.get(id=audio_id)
            
            # Get audio blob
            storage_client = get_storage_client()
            container_client = storage_client.get_container_client("audio-files")
            blob_client = container_client.get_blob_client(audio_file.file_path)
            
            # Stream the audio
            def generate():
                download_stream = blob_client.download_blob()
                return download_stream.readall()
            
            response = StreamingHttpResponse(generate(), content_type='audio/wav')
            return response
        except AudioFile.DoesNotExist:
            return Response({'error': 'Audio file not found'}, status=status.HTTP_404_NOT_FOUND)
        
class OptimizedDocumentUploadView(APIView):
    @sync_to_async
    def save_document(self, user, title, file_obj):
        return Document.objects.create(
            user=user,
            title=title,
            file=file_obj
        )
    
    async def post(self, request):
        # Process in parallel when possible
        document_task = self.save_document(
            request.user,
            request.POST.get('title'),
            request.FILES['file']
        )
        
        # Start processing immediately
        document = await document_task
        
        # Process document asynchronously
        summary_task = process_document(document)
        
        # Generate summary and audio in parallel
        summary_instance = await summary_task
        
        summary_text_task = generate_summary(summary_instance.text)
        
        summary_text = await summary_text_task
        summary_instance.text = summary_text
        await sync_to_async(summary_instance.save)()
        
        # Generate audio
        audio_file = await generate_audio(summary_instance)
        
        return Response({
            'document_id': document.id,
            'title': document.title,
            'summary': summary_text,
            'audio_url': f"/api/audio/{audio_file.id}/"
        }, status=status.HTTP_201_CREATED)
    
class SecureDocumentUploadView(DocumentUploadView):
    ALLOWED_EXTENSIONS = ['pdf', 'docx', 'txt']
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    def validate_file(self, file_obj):
        # Check file extension
        validator = FileExtensionValidator(allowed_extensions=self.ALLOWED_EXTENSIONS)
        try:
            validator(file_obj)
        except ValidationError:
            raise ValidationError("Invalid file type. Only PDF, DOCX, and TXT files are allowed.")
        
        # Check file size
        if file_obj.size > self.MAX_FILE_SIZE:
            raise ValidationError("File size exceeds 10MB limit.")
        
        # Check file content (basic validation)
        file_obj.seek(0)
        first_bytes = file_obj.read(1024)
        file_obj.seek(0)
        
        # Basic magic number checking
        if file_obj.name.endswith('.pdf') and not first_bytes.startswith(b'%PDF'):
            raise ValidationError("Invalid PDF file.")
        
        return True
    
    async def post(self, request):
        try:
            # Check if file exists in request
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file uploaded'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            file_obj = request.FILES['file']
            self.validate_file(file_obj)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        return await super().post(request)   
class HomeView(TemplateView):
    """Landing page view"""
    template_name = 'marketing/home.html'
    
class FeaturesView(TemplateView):
    """Features page view"""
    template_name = 'marketing/features.html'
    
class AboutView(TemplateView):
    """About page view"""
    template_name = 'marketing/about.html'
    
class ContactView(TemplateView):
    """Contact page view with form handling"""
    template_name = 'marketing/contact.html'
    
    def post(self, request, *args, **kwargs):
        # Process contact form submission
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        reason = request.POST.get('reason', 'general')
        message = request.POST.get('message', '')
        
        # Here you would typically save to database or send an email
        # For example using Django's send_mail function:
        """
        from django.core.mail import send_mail
        
        send_mail(
            subject=f'EduSauti Contact: {reason}',
            message=f'From: {name} ({email})\n\n{message}',
            from_email='noreply@edusauti.com',
            recipient_list=['support@edusauti.com'],
            fail_silently=False,
        )
        """
        
        # Add a success message
        messages.success(request, 'Your message has been sent successfully. We will get back to you soon!')
        
        # Redirect back to contact page
        return HttpResponseRedirect(reverse('contact'))