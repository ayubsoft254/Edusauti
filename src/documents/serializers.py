from rest_framework import serializers
from .models import Document, AudioSummary, Question, DocumentShare, ProcessingLog


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for Document model"""
    
    file_size_mb = serializers.ReadOnlyField()
    processing_duration = serializers.ReadOnlyField()
    is_processing = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    has_audio = serializers.ReadOnlyField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'title', 'description', 'file', 'file_type', 'file_size', 'file_size_mb',
            'original_filename', 'status', 'processing_started_at', 'processing_completed_at',
            'error_message', 'extracted_text', 'text_extraction_confidence', 'page_count',
            'word_count', 'summary_text', 'summary_length', 'tags', 'language',
            'subject_area', 'difficulty_level', 'view_count', 'audio_play_count',
            'total_questions_asked', 'average_session_duration', 'created_at', 'updated_at',
            'processing_duration', 'is_processing', 'is_completed', 'has_audio'
        ]
        read_only_fields = [
            'id', 'user', 'file_size', 'original_filename', 'status', 'processing_started_at',
            'processing_completed_at', 'error_message', 'extracted_text', 'text_extraction_confidence',
            'page_count', 'word_count', 'summary_text', 'view_count', 'audio_play_count',
            'total_questions_asked', 'average_session_duration', 'created_at', 'updated_at'
        ]
    
    def create(self, validated_data):
        # Set user from request context
        validated_data['user'] = self.context['request'].user
        
        # Set file metadata
        file_obj = validated_data['file']
        validated_data['original_filename'] = file_obj.name
        validated_data['file_size'] = file_obj.size
        
        # Determine file type from extension
        extension = file_obj.name.split('.')[-1].lower()
        validated_data['file_type'] = extension
        
        return super().create(validated_data)


class DocumentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for document lists"""
    
    file_size_mb = serializers.ReadOnlyField()
    has_audio = serializers.ReadOnlyField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'title', 'description', 'file_type', 'file_size_mb', 'status',
            'summary_length', 'tags', 'subject_area', 'difficulty_level',
            'view_count', 'audio_play_count', 'total_questions_asked',
            'created_at', 'has_audio'
        ]


class AudioSummarySerializer(serializers.ModelSerializer):
    """Serializer for AudioSummary model"""
    
    audio_duration_formatted = serializers.ReadOnlyField()
    audio_size_mb = serializers.ReadOnlyField()
    
    class Meta:
        model = AudioSummary
        fields = [
            'id', 'document', 'audio_file', 'audio_format', 'audio_duration',
            'audio_duration_formatted', 'audio_size', 'audio_size_mb', 'voice_name',
            'speech_rate', 'speech_pitch', 'status', 'generated_at', 'generation_time',
            'azure_request_id', 'azure_cost'
        ]
        read_only_fields = [
            'id', 'document', 'audio_file', 'audio_format', 'audio_duration',
            'audio_size', 'status', 'generated_at', 'generation_time',
            'azure_request_id', 'azure_cost'
        ]


class QuestionSerializer(serializers.ModelSerializer):
    """Serializer for Question model"""
    
    response_time = serializers.ReadOnlyField()
    
    class Meta:
        model = Question
        fields = [
            'id', 'document', 'question_text', 'answer_text', 'audio_timestamp',
            'context_snippet', 'is_answered', 'answer_confidence', 'processing_time',
            'user_rating', 'user_feedback', 'azure_request_id', 'azure_cost',
            'asked_at', 'answered_at', 'response_time'
        ]
        read_only_fields = [
            'id', 'user', 'document', 'answer_text', 'context_snippet', 'is_answered',
            'answer_confidence', 'processing_time', 'azure_request_id', 'azure_cost',
            'asked_at', 'answered_at'
        ]
    
    def create(self, validated_data):
        # Set user from request context
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class QuestionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating questions"""
    
    class Meta:
        model = Question
        fields = ['question_text', 'audio_timestamp']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        validated_data['document'] = self.context['document']
        return super().create(validated_data)


class DocumentShareSerializer(serializers.ModelSerializer):
    """Serializer for DocumentShare model"""
    
    is_expired = serializers.ReadOnlyField()
    
    class Meta:
        model = DocumentShare
        fields = [
            'id', 'document', 'shared_with_email', 'can_view', 'can_ask_questions',
            'can_download', 'share_token', 'expires_at', 'is_active', 'access_count',
            'last_accessed', 'created_at', 'is_expired'
        ]
        read_only_fields = [
            'id', 'document', 'share_token', 'access_count', 'last_accessed', 'created_at'
        ]
    
    def create(self, validated_data):
        validated_data['shared_by'] = self.context['request'].user
        validated_data['document'] = self.context['document']
        
        # Generate unique share token
        import secrets
        validated_data['share_token'] = secrets.token_urlsafe(32)
        
        return super().create(validated_data)


class ProcessingLogSerializer(serializers.ModelSerializer):
    """Serializer for ProcessingLog model"""
    
    class Meta:
        model = ProcessingLog
        fields = ['id', 'step', 'level', 'message', 'details', 'timestamp']
        read_only_fields = ['id', 'timestamp']