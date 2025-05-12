from .azure_clients import get_document_client
from .models import Document, Summary
import io

async def process_document(document_instance):
    """Process uploaded document using Azure Document Intelligence"""
    client = get_document_client()
    
    # Get document content
    document_instance.file.open(mode='rb')
    document_content = document_instance.file.read()
    document_instance.file.close()
    
    # Analyze document
    poller = client.begin_analyze_document("prebuilt-document", document_content)
    result = poller.result()
    
    # Extract text
    extracted_text = ""
    for page in result.pages:
        for line in page.lines:
            extracted_text += line.content + "\n"
    
    # Create summary instance
    summary = Summary(document=document_instance, text=extracted_text)
    summary.save()
    
    return summary