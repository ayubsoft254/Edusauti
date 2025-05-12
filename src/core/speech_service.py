import os
import uuid
from .azure_clients import get_speech_client, get_storage_client
from .models import AudioFile
import azure.cognitiveservices.speech as speechsdk

async def generate_audio(summary_instance, voice_name="en-US-JennyNeural"):
    """Convert summary text to speech using Azure Speech Service"""
    speech_config = get_speech_client()
    speech_config.speech_synthesis_voice_name = voice_name
    
    # Create file name for audio
    file_name = f"{uuid.uuid4()}.wav"
    
    # Configure audio output
    storage_client = get_storage_client()
    container_client = storage_client.get_container_client("audio-files")
    blob_client = container_client.get_blob_client(file_name)
    
    # Generate speech
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
    result = speech_synthesizer.speak_text_async(summary_instance.text).get()
    
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        # Upload to blob storage
        blob_client.upload_blob(result.audio_data)
        
        # Save audio file reference
        audio_file = AudioFile(
            summary=summary_instance,
            file_path=file_name,
            voice_type=voice_name
        )
        audio_file.save()
        
        return audio_file
    else:
        raise Exception(f"Speech synthesis failed: {result.reason}")