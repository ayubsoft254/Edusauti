import os
import json
from typing import Dict, Any
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from django.conf import settings
from .base import BaseAIService, RateLimitExceeded, ServiceUnavailable, InvalidInput

class DocumentIntelligenceService(BaseAIService):
    """Azure Document Intelligence service for text extraction"""
    
    def __init__(self):
        super().__init__()
        self.endpoint = getattr(settings, 'AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT', '')
        self.api_key = getattr(settings, 'AZURE_DOCUMENT_INTELLIGENCE_KEY', '')
        
        if not self.endpoint or not self.api_key:
            raise ValueError("Azure Document Intelligence endpoint and key must be configured")
        
        self.client = DocumentIntelligenceClient(
            endpoint=self.endpoint,
            credential=AzureKeyCredential(self.api_key)
        )
    
    def get_service_type(self) -> str:
        return 'document_intelligence'
    
    def extract_text(self, file_path: str, user=None) -> Dict[str, Any]:
        """
        Extract text from a document file
        
        Args:
            file_path: Path to the document file
            user: User making the request (for logging)
            
        Returns:
            Dict containing extracted text and metadata
        """
        
        # Validate input
        if not os.path.exists(file_path):
            raise InvalidInput(f"File not found: {file_path}")
        
        # Check rate limits
        if not self.check_rate_limits(user):
            raise RateLimitExceeded("Daily rate limit exceeded for Document Intelligence")
        
        # Get file size for logging
        file_size = os.path.getsize(file_path)
        
        # Create log entry
        log_entry = self.create_log_entry(
            user=user,
            endpoint=f"{self.endpoint}/documentModels/prebuilt-read:analyze",
            request_size=file_size
        )
        
        try:
            # Read the file
            with open(file_path, 'rb') as file:
                file_content = file.read()
            
            # Updated API call for newer Azure Document Intelligence SDK
            poller = self.client.begin_analyze_document(
                model_id="prebuilt-read",
                body=file_content,
                content_type="application/octet-stream"
            )
            
            # Wait for completion
            result = poller.result()
            
            # Extract text and metadata
            extracted_data = self._process_analysis_result(result)
            
            # Calculate cost
            page_count = extracted_data.get('page_count', 1)
            estimated_cost = self.estimate_cost(pages=page_count)
            
            # Update log entry
            log_entry.mark_completed(
                status='success',
                response_size=len(json.dumps(extracted_data))
            )
            log_entry.characters_processed = len(extracted_data.get('text', ''))
            log_entry.estimated_cost = estimated_cost
            log_entry.azure_operation_id = getattr(poller, 'operation_id', '')
            log_entry.save()
            
            # Update usage stats
            self.update_usage_stats(
                user=user,
                characters=len(extracted_data.get('text', '')),
                cost=estimated_cost,
                success=True
            )
            
            return extracted_data
            
        except HttpResponseError as e:
            self.handle_error(log_entry, e, error_code=str(e.status_code))
            raise ServiceUnavailable(f"Document Intelligence API error: {e}")
        
        except Exception as e:
            self.handle_error(log_entry, e)
            raise


    def extract_text_from_url(self, document_url: str, user=None) -> Dict[str, Any]:
        """
        Extract text from a document via URL
        
        Args:
            document_url: URL to the document
            user: User making the request
            
        Returns:
            Dict containing extracted text and metadata
        """
        
        # Check rate limits
        if not self.check_rate_limits(user):
            raise RateLimitExceeded("Daily rate limit exceeded for Document Intelligence")
        
        # Create log entry
        log_entry = self.create_log_entry(
            user=user,
            endpoint=f"{self.endpoint}/documentModels/prebuilt-read:analyze",
            request_size=len(document_url)
        )
        
        try:
            # Updated API call for URL-based analysis
            poller = self.client.begin_analyze_document(
                model_id="prebuilt-read",
                body={"urlSource": document_url}
            )
            
            # Wait for completion
            result = poller.result()
            
            # Extract text and metadata
            extracted_data = self._process_analysis_result(result)
            
            # Calculate cost
            page_count = extracted_data.get('page_count', 1)
            estimated_cost = self.estimate_cost(pages=page_count)
            
            # Update log entry
            log_entry.mark_completed(
                status='success',
                response_size=len(json.dumps(extracted_data))
            )
            log_entry.characters_processed = len(extracted_data.get('text', ''))
            log_entry.estimated_cost = estimated_cost
            log_entry.azure_operation_id = getattr(poller, 'operation_id', '')
            log_entry.save()
            
            # Update usage stats
            self.update_usage_stats(
                user=user,
                characters=len(extracted_data.get('text', '')),
                cost=estimated_cost,
                success=True
            )
            
            return extracted_data
            
        except HttpResponseError as e:
            self.handle_error(log_entry, e, error_code=str(e.status_code))
            raise ServiceUnavailable(f"Document Intelligence API error: {e}")
        
        except Exception as e:
            self.handle_error(log_entry, e)
            raise
    
    def _process_analysis_result(self, result) -> Dict[str, Any]:
        """Process the analysis result and extract relevant information"""
        
        # Extract all text content
        full_text = ""
        for page in result.pages:
            for line in page.lines:
                full_text += line.content + "\n"
        
        # Calculate confidence score
        confidence_scores = []
        for page in result.pages:
            for line in page.lines:
                if hasattr(line, 'confidence') and line.confidence:
                    confidence_scores.append(line.confidence)
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        # Extract page information
        page_count = len(result.pages)
        
        # Extract tables if any
        tables = []
        if hasattr(result, 'tables') and result.tables:
            for table in result.tables:
                table_data = {
                    'row_count': table.row_count,
                    'column_count': table.column_count,
                    'cells': []
                }
                for cell in table.cells:
                    table_data['cells'].append({
                        'content': cell.content,
                        'row_index': cell.row_index,
                        'column_index': cell.column_index
                    })
                tables.append(table_data)
        
        # Extract key-value pairs if any
        key_value_pairs = []
        if hasattr(result, 'key_value_pairs') and result.key_value_pairs:
            for kv_pair in result.key_value_pairs:
                key_value_pairs.append({
                    'key': kv_pair.key.content if kv_pair.key else '',
                    'value': kv_pair.value.content if kv_pair.value else ''
                })
        
        return {
            'text': full_text.strip(),
            'confidence': avg_confidence,
            'page_count': page_count,
            'word_count': len(full_text.split()) if full_text else 0,
            'character_count': len(full_text),
            'tables': tables,
            'key_value_pairs': key_value_pairs,
            'language': self._detect_language(full_text),
            'metadata': {
                'extraction_method': 'azure_document_intelligence',
                'model_id': 'prebuilt-read',
                'api_version': '2024-02-29-preview'
            }
        }
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection - can be enhanced with Azure Text Analytics"""
        # Basic language detection based on common words
        # This is a simplified version - you might want to use Azure Text Analytics for better detection
        
        if not text:
            return 'unknown'
        
        # Check for common English words
        english_indicators = ['the', 'and', 'is', 'in', 'to', 'of', 'a', 'that', 'it', 'with']
        words = text.lower().split()[:100]  # Check first 100 words
        
        english_count = sum(1 for word in words if word in english_indicators)
        
        if english_count > len(words) * 0.1:  # If more than 10% are English indicators
            return 'en'
        
        return 'unknown'
    
    def estimate_cost(self, pages=1, **kwargs) -> float:
        """Estimate cost for document analysis"""
        # Azure Document Intelligence pricing (as of 2024)
        # Read API: $0.001 per page for first 1M pages
        cost_per_page = 0.001
        return cost_per_page * pages
    
    def validate_input(self, file_path: str = None, document_url: str = None, **kwargs) -> bool:
        """Validate input parameters"""
        if not file_path and not document_url:
            raise InvalidInput("Either file_path or document_url must be provided")
        
        if file_path and not os.path.exists(file_path):
            raise InvalidInput(f"File does not exist: {file_path}")
        
        if file_path:
            # Check file size (max 500MB for Document Intelligence)
            file_size = os.path.getsize(file_path)
            max_size = 500 * 1024 * 1024  # 500MB
            if file_size > max_size:
                raise InvalidInput(f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds maximum limit of 500MB")
            
            # Check file extension
            allowed_extensions = ['.pdf', '.docx', '.doc', '.txt', '.rtf', '.html', '.htm']
            file_extension = os.path.splitext(file_path)[1].lower()
            if file_extension not in allowed_extensions:
                raise InvalidInput(f"Unsupported file type: {file_extension}")
        
        return True