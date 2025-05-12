import json
import os
from channels.generic.websocket import AsyncWebsocketConsumer
from .azure_clients import get_openai_client
from .models import Document, Question
from channels.db import database_sync_to_async

class QuestionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.document_id = self.scope['url_route']['kwargs']['document_id']
        self.room_group_name = f'qa_{self.document_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        question_text = data['question']
        user_id = self.scope['user'].id
        
        # Get document context
        document = await self.get_document(self.document_id)
        document_context = await self.get_document_context(document)
        
        # Generate answer using OpenAI
        answer = await self.generate_answer(question_text, document_context)
        
        # Save question and answer
        await self.save_qa(document, user_id, question_text, answer)
        
        # Send answer back to the room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'qa_message',
                'question': question_text,
                'answer': answer
            }
        )
    
    async def qa_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'question': event['question'],
            'answer': event['answer']
        }))
    
    @database_sync_to_async
    def get_document(self, document_id):
        return Document.objects.get(id=document_id)
    
    @database_sync_to_async
    def get_document_context(self, document):
        # Get summary text to provide context
        return document.summary.text
    
    @database_sync_to_async
    def save_qa(self, document, user_id, question, answer):
        Question.objects.create(
            document=document,
            user_id=user_id,
            question_text=question,
            answer_text=answer
        )
    
    async def generate_answer(self, question, context):
        openai_client = get_openai_client()
        
        prompt = f"""
        You are an educational AI assistant helping a student understand a document.
        Use the context provided to answer the question in a teacher-like manner.
        
        Context:
        {context}
        
        Question:
        {question}
        
        Provide a clear, educational answer:
        """
        
        response = openai_client.Completion.create(
            engine=os.environ["AZURE_OPENAI_DEPLOYMENT"],
            prompt=prompt,
            max_tokens=500,
            temperature=0.7
        )
        
        return response.choices[0].text.strip()