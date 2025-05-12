import os
from decouple import config
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient
import azure.cognitiveservices.speech as speechsdk
import openai



# Document Intelligence client
def get_document_client():
    endpoint = config("AZURE_DOCUMENT_ENDPOINT")
    key = config("AZURE_DOCUMENT_KEY")
    return DocumentAnalysisClient(endpoint, AzureKeyCredential(key))

# OpenAI client
def get_openai_client():
    openai.api_type = "azure"
    openai.api_base = config("AZURE_OPENAI_ENDPOINT")
    openai.api_key = config("AZURE_OPENAI_KEY")
    openai.api_version = "2023-05-15"
    return openai

# Speech Service client
def get_speech_client():
    speech_config = speechsdk.SpeechConfig(
        subscription= config("AZURE_SPEECH_KEY"),
        region=config("AZURE_SPEECH_REGION"),
    )
    return speech_config

# Blob Storage client
def get_storage_client():
    conn_str = config("AZURE_STORAGE_CONNECTION_STRING")
    return BlobServiceClient.from_connection_string(conn_str)