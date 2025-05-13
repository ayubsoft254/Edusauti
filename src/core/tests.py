from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Document, Summary, AudioFile, Question
import asyncio

class DocumentProcessingTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.client.login(username='testuser', password='testpass')
    
    def test_document_upload(self):
        # Create a test file
        test_file = SimpleUploadedFile(
            "test.txt",
            b"Test content for EduSauti platform",
            content_type="text/plain"
        )
        
        response = self.client.post('/api/upload/', {
            'title': 'Test Document',
            'file': test_file,
            'voice_type': 'en-US-JennyNeural'
        })
        
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Document.objects.filter(title='Test Document').exists())
    
    def test_summary_generation(self):
        # Create a document
        document = Document.objects.create(
            user=self.user,
            title='Test Document',
            file='test.pdf'
        )
        
        # Mock the summarization process
        summary = Summary.objects.create(
            document=document,
            text='This is a test summary'
        )
        
        self.assertEqual(summary.document, document)
        self.assertTrue(len(summary.text) > 0)

class WebSocketTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
    
    def test_websocket_connection(self):
        # This is a simplified test - in production, use channels.testing
        from channels.testing import WebsocketCommunicator
        from config.asgi import application
        
        communicator = WebsocketCommunicator(
            application,
            f"/ws/qa/1/"
        )
        
        # Test connection
        async def test():
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.disconnect()
        
        asyncio.run(test())