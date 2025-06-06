from typing import Dict, Any, BinaryIO, List
import azure.cognitiveservices.speech as speechsdk
from django.conf import settings
from .base import BaseAIService, RateLimitExceeded, ServiceUnavailable, InvalidInput
from .models import AIServiceLog
import time
import io


class SpeechService(BaseAIService):
    """Azure Speech Service for text-to-speech and speech-to-text"""
    
    def __init__(self):
        super().__init__()
        self.speech_key = getattr(settings, 'AZURE_SPEECH_KEY', '')
        self.speech_region = getattr(settings, 'AZURE_SPEECH_REGION', '')
        
        if not self.speech_key or not self.speech_region:
            raise ValueError("Azure Speech key and region must be configured")
        
        # Create speech config
        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.speech_key, 
            region=self.speech_region
        )
        
        # Set default audio format
        self.speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
        )
    
    def get_service_type(self) -> str:
        return 'speech_synthesis'
    
    def text_to_speech(
        self, 
        text: str,
        voice_name: str = 'en-US-JennyNeural',
        speech_rate: str = 'medium',
        speech_pitch: str = 'medium',
        user=None
    ) -> Dict[str, Any]:
        """
        Convert text to speech using Azure Speech Service
        
        Args:
            text: Text to convert to speech
            voice_name: Azure voice name to use
            speech_rate: Speed of speech (slow, medium, fast)
            speech_pitch: Pitch of speech (low, medium, high)
            user: User making the request
            
        Returns:
            Dict containing audio data and metadata
        """
        
        # Validate input
        if not text or len(text.strip()) < 1:
            raise InvalidInput("Text cannot be empty")
        
        if len(text) > 10000:
            raise InvalidInput("Text is too long. Maximum 10,000 characters allowed.")
        
        # Check rate limits
        if not self.check_rate_limits(user):
            raise RateLimitExceeded("Daily rate limit exceeded for Speech Service")
        
        # Create log entry
        log_entry = self.create_log_entry(
            user=user,
            endpoint=f"https://{self.speech_region}.tts.speech.microsoft.com/cognitiveservices/v1",
            request_size=len(text.encode('utf-8'))
        )
        
        start_time = time.time()
        
        try:
            # Configure voice and speech parameters
            self.speech_config.speech_synthesis_voice_name = voice_name
            
            # Create SSML with rate and pitch adjustments
            ssml_text = self._create_ssml(text, voice_name, speech_rate, speech_pitch)

            # Create synthesizer with default audio output (this will work)
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config,
                audio_config=None  # Use default audio output
            )
            
            # Synthesize speech
            result = synthesizer.speak_ssml_async(ssml_text).get()
            
            response_time = time.time() - start_time
            
            # Check result
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                # Get audio data directly from result
                audio_data = result.audio_data
                
                # Calculate audio duration (approximate)
                duration = self._calculate_audio_duration(audio_data, text)
                
                # Calculate cost
                character_count = len(text)
                estimated_cost = self.estimate_cost(characters=character_count)
                
                # Update log entry
                log_entry.mark_completed(
                    status='success',
                    response_size=len(audio_data)
                )
                log_entry.characters_processed = character_count
                log_entry.estimated_cost = estimated_cost
                log_entry.save()
                
                # Update usage stats
                self.update_usage_stats(
                    user=user,
                    characters=character_count,
                    cost=estimated_cost,
                    success=True
                )
                
                return {
                    'audio_data': audio_data,
                    'duration': duration,
                    'character_count': character_count,
                    'voice_name': voice_name,
                    'speech_rate': speech_rate,
                    'speech_pitch': speech_pitch,
                    'estimated_cost': estimated_cost,
                    'format': 'mp3',
                    'sample_rate': 16000,
                    'bit_rate': 32000
                }
                
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                error_msg = f"Speech synthesis canceled: {cancellation_details.reason}"
                if cancellation_details.error_details:
                    error_msg += f" - {cancellation_details.error_details}"
                
                self.handle_error(log_entry, Exception(error_msg))
                raise ServiceUnavailable(error_msg)
            
            else:
                error_msg = f"Speech synthesis failed with reason: {result.reason}"
                self.handle_error(log_entry, Exception(error_msg))
                raise ServiceUnavailable(error_msg)
                
        except Exception as e:
            response_time = time.time() - start_time
            
            if log_entry.status == 'pending':
                self.handle_error(log_entry, e)
            
            if "rate limit" in str(e).lower() or "quota" in str(e).lower():
                raise RateLimitExceeded(f"Speech Service rate limit exceeded: {e}")
            raise ServiceUnavailable(f"Speech Service error: {e}")
    
    def speech_to_text(
        self, 
        audio_file: BinaryIO,
        language: str = 'en-US',
        user=None
    ) -> Dict[str, Any]:
        """
        Convert speech to text using Azure Speech Service
        
        Args:
            audio_file: Audio file stream
            language: Language code for recognition
            user: User making the request
            
        Returns:
            Dict containing transcribed text and metadata
        """
        
        # Check rate limits
        if not self.check_rate_limits(user):
            raise RateLimitExceeded("Daily rate limit exceeded for Speech Service")
        
        # Get audio file size
        audio_file.seek(0, 2)  # Seek to end
        file_size = audio_file.tell()
        audio_file.seek(0)  # Reset to beginning
        
        # Create log entry
        log_entry = self.create_log_entry(
            user=user,
            endpoint=f"https://{self.speech_region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1",
            request_size=file_size,
            service_type='speech_recognition'
        )
        
        try:
            # Configure speech recognition
            self.speech_config.speech_recognition_language = language
            
            # Create audio stream from file
            audio_stream = speechsdk.audio.PushAudioInputStream()
            audio_config = speechsdk.audio.AudioConfig(stream=audio_stream)
            
            # Create recognizer
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )
            
            # Push audio data
            audio_data = audio_file.read()
            audio_stream.write(audio_data)
            audio_stream.close()
            
            # Recognize speech
            result = speech_recognizer.recognize_once()
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                recognized_text = result.text
                confidence = getattr(result, 'confidence', 0.0)
                
                # Calculate cost (approximate)
                duration_minutes = self._estimate_audio_duration_minutes(audio_data)
                estimated_cost = self.estimate_cost(duration_minutes=duration_minutes)
                
                # Update log entry
                log_entry.mark_completed(
                    status='success',
                    response_size=len(recognized_text.encode('utf-8'))
                )
                log_entry.characters_processed = len(recognized_text)
                log_entry.estimated_cost = estimated_cost
                log_entry.save()
                
                # Update usage stats
                self.update_usage_stats(
                    user=user,
                    characters=len(recognized_text),
                    cost=estimated_cost,
                    success=True
                )
                
                return {
                    'text': recognized_text,
                    'confidence': confidence,
                    'language': language,
                    'duration_minutes': duration_minutes,
                    'estimated_cost': estimated_cost
                }
                
            elif result.reason == speechsdk.ResultReason.NoMatch:
                error_msg = "No speech could be recognized"
                self.handle_error(log_entry, Exception(error_msg))
                return {
                    'text': '',
                    'confidence': 0.0,
                    'language': language,
                    'error': error_msg
                }
                
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                error_msg = f"Speech recognition canceled: {cancellation_details.reason}"
                if cancellation_details.error_details:
                    error_msg += f" - {cancellation_details.error_details}"
                
                self.handle_error(log_entry, Exception(error_msg))
                raise ServiceUnavailable(error_msg)
            
            else:
                error_msg = f"Speech recognition failed with reason: {result.reason}"
                self.handle_error(log_entry, Exception(error_msg))
                raise ServiceUnavailable(error_msg)
                
        except Exception as e:
            if log_entry.status == 'pending':
                self.handle_error(log_entry, e)
            
            if "rate limit" in str(e).lower() or "quota" in str(e).lower():
                raise RateLimitExceeded(f"Speech Service rate limit exceeded: {e}")
            raise ServiceUnavailable(f"Speech Service error: {e}")
    
    def _create_ssml(self, text: str, voice_name: str, speech_rate: str, speech_pitch: str) -> str:
        """Create SSML markup for enhanced speech synthesis"""
        
        # Map rate values
        rate_map = {
            'slow': '-20%',
            'medium': '0%', 
            'fast': '+20%'
        }
        
        # Map pitch values
        pitch_map = {
            'low': '-10%',
            'medium': '0%',
            'high': '+10%'
        }
        
        rate_value = rate_map.get(speech_rate, '0%')
        pitch_value = pitch_map.get(speech_pitch, '0%')
        
        ssml = f"""
        <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>
            <voice name='{voice_name}'>
                <prosody rate='{rate_value}' pitch='{pitch_value}'>
                    {self._escape_ssml_text(text)}
                </prosody>
            </voice>
        </speak>
        """
        
        return ssml.strip()
    
    def _escape_ssml_text(self, text: str) -> str:
        """Escape special characters for SSML"""
        # Basic SSML escaping
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&apos;')
        return text
    
    def _calculate_audio_duration(self, audio_data: bytes, text: str) -> int:
        """Calculate approximate audio duration in seconds"""
        # Rough estimation: average reading speed is about 150-200 words per minute
        word_count = len(text.split())
        words_per_minute = 170  # Average speaking rate
        duration_minutes = word_count / words_per_minute
        return int(duration_minutes * 60)
    
    def _estimate_audio_duration_minutes(self, audio_data: bytes) -> float:
        """Estimate audio duration from audio data"""
        # This is a rough estimation - actual duration would require audio analysis
        # Assuming standard MP3 compression ratios
        estimated_seconds = len(audio_data) / 4000  # Rough estimate
        return estimated_seconds / 60
    
    def get_available_voices(self, language: str = 'en-US') -> List[Dict[str, str]]:
        """Get list of available voices for a language"""
        
        # Predefined list of popular Azure voices
        # In production, you might want to call the Azure API to get the current list
        voices = {
            'en-US': [
                {'name': 'en-US-JennyNeural', 'gender': 'Female', 'description': 'Friendly and warm'},
                {'name': 'en-US-GuyNeural', 'gender': 'Male', 'description': 'Clear and professional'},
                {'name': 'en-US-AriaNeural', 'gender': 'Female', 'description': 'Expressive and natural'},
                {'name': 'en-US-DavisNeural', 'gender': 'Male', 'description': 'Confident and clear'},
                {'name': 'en-US-AmberNeural', 'gender': 'Female', 'description': 'Warm and engaging'},
                {'name': 'en-US-AnaNeural', 'gender': 'Female', 'description': 'Cheerful and bright'},
                {'name': 'en-US-BrandonNeural', 'gender': 'Male', 'description': 'Young and energetic'},
            ],
            'en-GB': [
                {'name': 'en-GB-SoniaNeural', 'gender': 'Female', 'description': 'British English, clear'},
                {'name': 'en-GB-RyanNeural', 'gender': 'Male', 'description': 'British English, professional'},
            ]
        }
        
        return voices.get(language, voices['en-US'])
    
    def estimate_cost(self, characters=0, duration_minutes=0, **kwargs) -> float:
        """Estimate cost for Speech Service operations"""
        if characters > 0:
            # Text-to-Speech pricing (as of 2024)
            # Neural voices: $16 per 1M characters
            cost_per_million_chars = 16.0
            return (characters / 1000000) * cost_per_million_chars
        
        elif duration_minutes > 0:
            # Speech-to-Text pricing (as of 2024)
            # Standard: $1 per hour
            cost_per_hour = 1.0
            return (duration_minutes / 60) * cost_per_hour
        
        return 0.0
    
    def _calculate_cost(self, text_length):
        """Calculate estimated cost for speech synthesis"""
        # Azure Speech pricing: ~$4 per 1M characters
        cost_per_million_chars = 4.0
        return (text_length / 1_000_000) * cost_per_million_chars