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
import asyncio

class DocumentUploadView(APIView):
    async def post(self, request):
        # Save uploaded file
        file_obj = request.FILES['file']
        title = request.POST.get('title', file_obj.name)
        
        document = Document(
            user=request.user,
            title=title,
            file=file_obj
        )
        document.save()
        
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