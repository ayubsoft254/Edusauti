import tiktoken
import time
from typing import Dict, Any
from openai import AzureOpenAI
from django.conf import settings
from django.utils import timezone
from .base import BaseAIService, RateLimitExceeded, ServiceUnavailable, InvalidInput


class OpenAIService(BaseAIService):
    """Azure OpenAI service for text generation and Q&A"""
    
    def __init__(self):
        super().__init__()
        self.endpoint = getattr(settings, 'AZURE_OPENAI_ENDPOINT', '')
        self.api_key = getattr(settings, 'AZURE_OPENAI_KEY', '')
        self.api_version = getattr(settings, 'AZURE_OPENAI_API_VERSION', '2024-02-01')
        self.deployment_name = getattr(settings, 'AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4')
        
        if not self.endpoint or not self.api_key:
            raise ValueError("Azure OpenAI endpoint and key must be configured")
        
        self.client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version
        )
        
        # Initialize tokenizer for cost calculation
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        except:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def get_service_type(self) -> str:
        return 'openai_chat'
    
    def generate_summary(
        self, 
        text: str, 
        style: str = 'teacher',
        length: str = 'medium',
        subject_area: str = '',
        difficulty_level: str = 'intermediate',
        user=None
    ) -> Dict[str, Any]:
        """
        Generate a teacher-like summary of the provided text
        
        Args:
            text: The text to summarize
            style: Style of summary ('teacher', 'academic', 'simple')
            length: Length of summary ('short', 'medium', 'long')
            subject_area: Subject area context
            difficulty_level: Target difficulty level
            user: User making the request
            
        Returns:
            Dict containing the generated summary and metadata
        """
        
        # Validate input
        if not text or len(text.strip()) < 10:
            raise InvalidInput("Text must be at least 10 characters long")
        
        # Check rate limits
        if not self.check_rate_limits(user):
            raise RateLimitExceeded("Daily rate limit exceeded for OpenAI")
        
        # Calculate input tokens
        input_tokens = len(self.tokenizer.encode(text))
        
        # Create log entry
        log_entry = self.create_log_entry(
            user=user,
            endpoint=f"{self.endpoint}/openai/deployments/{self.deployment_name}/chat/completions",
            request_size=len(text.encode('utf-8'))
        )
        
        try:
            # Create the prompt based on parameters
            system_prompt = self._create_summary_prompt(style, length, subject_area, difficulty_level)
            
            # Prepare messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Please summarize the following text:\n\n{text}"}
            ]
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                max_tokens=self._get_max_tokens_for_length(length),
                temperature=0.7,
                top_p=0.9,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            
            # Extract the summary
            summary = response.choices[0].message.content.strip()
            
            # Calculate tokens and cost
            output_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens
            estimated_cost = self.estimate_cost(tokens=total_tokens)
            
            # Update log entry
            log_entry.mark_completed(
                status='success',
                response_size=len(summary.encode('utf-8'))
            )
            log_entry.tokens_used = total_tokens
            log_entry.estimated_cost = estimated_cost
            log_entry.azure_request_id = response.id
            log_entry.save()
            
            # Update usage stats
            self.update_usage_stats(
                user=user,
                tokens=total_tokens,
                cost=estimated_cost,
                success=True
            )
            
            result = {
                'summary': summary,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': total_tokens,
                'estimated_cost': estimated_cost,
                'request_id': response.id,
                'style': style,
                'length': length,
                'subject_area': subject_area,
                'difficulty_level': difficulty_level
            }
            
            # Log successful request
            AIServiceLog.log_request(
                service_type='openai_chat',
                operation='generate_summary',
                success=True,
                response_time=response_time,
                tokens_used=response.usage.total_tokens,
                estimated_cost=result['estimated_cost']
            )
            
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            
            # Log failed request
            AIServiceLog.log_request(
                service_type='openai_chat',
                operation='generate_summary',
                success=False,
                error_message=str(e),
                response_time=response_time
            )
            
            raise e
    
    def answer_question(
        self, 
        question: str, 
        context: str,
        summary: str = '',
        audio_timestamp: int = None,
        user=None
    ) -> Dict[str, Any]:
        """
        Answer a question based on the document context
        
        Args:
            question: The user's question
            context: Full document text for context
            summary: Document summary for additional context
            audio_timestamp: Timestamp in audio where question was asked
            user: User making the request
            
        Returns:
            Dict containing the answer and metadata
        """
        
        # Validate input
        if not question or len(question.strip()) < 3:
            raise InvalidInput("Question must be at least 3 characters long")
        
        if not context:
            raise InvalidInput("Context is required to answer questions")
        
        # Check rate limits
        if not self.check_rate_limits(user):
            raise RateLimitExceeded("Daily rate limit exceeded for OpenAI")
        
        # Create log entry
        log_entry = self.create_log_entry(
            user=user,
            endpoint=f"{self.endpoint}/openai/deployments/{self.deployment_name}/chat/completions",
            request_size=len(question.encode('utf-8')) + len(context.encode('utf-8'))
        )
        
        try:
            # Create the Q&A prompt
            system_prompt = self._create_qa_prompt()
            
            # Prepare context (truncate if too long)
            max_context_length = 8000  # Leave room for question and response
            if len(context) > max_context_length:
                context = context[:max_context_length] + "..."
            
            # Build user message
            user_message = f"""Context from document:
{context}

{f"Summary: {summary}" if summary else ""}

Question: {question}

Please provide a clear, helpful answer based on the document content."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                max_tokens=500,  # Reasonable limit for Q&A
                temperature=0.3,  # Lower temperature for more focused answers
                top_p=0.9
            )
            
            # Extract the answer
            answer = response.choices[0].message.content.strip()
            
            # Calculate tokens and cost
            total_tokens = response.usage.total_tokens
            estimated_cost = self.estimate_cost(tokens=total_tokens)
            
            # Extract relevant context snippet
            context_snippet = self._extract_relevant_context(question, context, answer)
            
            # Calculate confidence based on response quality
            confidence = self._calculate_answer_confidence(answer, context)
            
            # Update log entry
            log_entry.mark_completed(
                status='success',
                response_size=len(answer.encode('utf-8'))
            )
            log_entry.tokens_used = total_tokens
            log_entry.estimated_cost = estimated_cost
            log_entry.azure_request_id = response.id
            log_entry.save()
            
            # Update usage stats
            self.update_usage_stats(
                user=user,
                tokens=total_tokens,
                cost=estimated_cost,
                success=True
            )
            
            return {
                'answer': answer,
                'context_snippet': context_snippet,
                'confidence': confidence,
                'tokens_used': total_tokens,
                'estimated_cost': estimated_cost,
                'request_id': response.id,
                'audio_timestamp': audio_timestamp
            }
            
        except Exception as e:
            self.handle_error(log_entry, e)
            if "rate limit" in str(e).lower():
                raise RateLimitExceeded(f"OpenAI rate limit exceeded: {e}")
            raise ServiceUnavailable(f"OpenAI API error: {e}")
    
    def _create_summary_prompt(self, style: str, length: str, subject_area: str, difficulty_level: str) -> str:
        """Create system prompt for summarization"""
        
        base_prompt = """You are an experienced teacher creating an educational summary. Your goal is to help students understand the content clearly and thoroughly."""
        
        style_prompts = {
            'teacher': "Explain concepts as a friendly, knowledgeable teacher would, using clear examples and connecting ideas.",
            'academic': "Provide a scholarly analysis with proper terminology and formal structure.",
            'simple': "Use simple language and break down complex concepts into easy-to-understand parts."
        }
        
        length_prompts = {
            'short': "Create a concise summary that covers the main points (aim for 1-2 minutes when read aloud).",
            'medium': "Provide a comprehensive summary with key details and examples (aim for 3-5 minutes when read aloud).",
            'long': "Create a detailed summary that thoroughly explains concepts and includes relevant examples (aim for 5+ minutes when read aloud)."
        }
        
        difficulty_prompts = {
            'beginner': "Assume the audience is new to this topic and needs foundational explanations.",
            'intermediate': "Assume the audience has some background knowledge but needs clear explanations.",
            'advanced': "Assume the audience is knowledgeable and can handle detailed, technical content."
        }
        
        prompt_parts = [
            base_prompt,
            style_prompts.get(style, style_prompts['teacher']),
            length_prompts.get(length, length_prompts['medium']),
            difficulty_prompts.get(difficulty_level, difficulty_prompts['intermediate'])
        ]
        
        if subject_area:
            prompt_parts.append(f"Focus on {subject_area} concepts and terminology where relevant.")
        
        prompt_parts.append("Structure your summary with clear paragraphs and smooth transitions between ideas.")
        
        return " ".join(prompt_parts)
    
    def _create_qa_prompt(self) -> str:
        """Create system prompt for Q&A"""
        return """You are a helpful teaching assistant. Answer questions based on the provided document context. 

Guidelines:
1. Only answer based on information in the document
2. If the answer isn't in the document, say so clearly
3. Provide specific, helpful answers
4. Use clear, educational language
5. If relevant, suggest related concepts from the document
6. Keep answers concise but complete

Always base your response on the document content provided."""
    
    def _get_max_tokens_for_length(self, length: str) -> int:
        """Get max tokens based on summary length"""
        token_limits = {
            'short': 300,
            'medium': 600,
            'long': 1200
        }
        return token_limits.get(length, 600)
    
    def _extract_relevant_context(self, question: str, context: str, answer: str) -> str:
        """Extract relevant context snippet for the answer"""
        # Simple implementation - find sentences containing key words from question
        words = question.lower().split()
        sentences = context.split('.')
        
        relevant_sentences = []
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(word in sentence_lower for word in words if len(word) > 3):
                relevant_sentences.append(sentence.strip())
                if len(relevant_sentences) >= 2:  # Limit to 2 sentences
                    break
        
        return '. '.join(relevant_sentences) + '.' if relevant_sentences else context[:200] + '...'
    
    def _calculate_answer_confidence(self, answer: str, context: str) -> float:
        """Calculate confidence score for the answer"""
        # Simple heuristic - this could be improved with more sophisticated methods
        if "I don't" in answer or "not mentioned" in answer or "unclear" in answer:
            return 0.3
        elif len(answer) < 20:
            return 0.5
        elif len(answer.split()) > 10:
            return 0.8
        else:
            return 0.7
    
    def estimate_cost(self, tokens=0, **kwargs) -> float:
        """Estimate cost for OpenAI API usage"""
        # Azure OpenAI pricing (as of 2024) - adjust based on your model
        # GPT-4: $0.03 per 1K input tokens, $0.06 per 1K output tokens
        # For simplicity, using average cost
        cost_per_1k_tokens = 0.045  # Average between input and output
        return (tokens / 1000) * cost_per_1k_tokens