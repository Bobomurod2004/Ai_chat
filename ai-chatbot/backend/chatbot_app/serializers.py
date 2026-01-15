from rest_framework import serializers
from .models import Document, Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for chatbot messages."""
    class Meta:
        model = Message
        fields = ['id', 'sender_type', 'text', 'lang', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for full conversations with their messages."""
    messages = MessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Conversation
        fields = ['id', 'user_id', 'platform', 'is_active', 'messages', 'created_at', 'updated_at']


class DocumentSerializer(serializers.ModelSerializer):
    """Document upload serializer - Professional Version."""
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'title', 'source_type', 'file_path', 'file_url', 
            'url', 'status', 'version', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'version', 'created_at', 'updated_at'
        ]
    
    def get_file_url(self, obj):
        """Return full file URL."""
        if obj.file_path:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file_path.url)
            return obj.file_path.url
        return None
    
    def validate(self, data):
        """Validate that either file or url is provided."""
        file = data.get('file_path')
        url = data.get('url')
        
        if not file and not url:
            raise serializers.ValidationError(
                "Either 'file_path' or 'url' must be provided."
            )
        
        if file and url:
            raise serializers.ValidationError(
                "Provide either 'file_path' or 'url', not both."
            )
        
        # Auto-detect source_type from file extension
        if file and not data.get('source_type'):
            ext = file.name.split('.')[-1].lower()
            type_map = {
                'pdf': 'pdf',
                'doc': 'doc',
                'docx': 'doc',
                'txt': 'text',
            }
            data['source_type'] = type_map.get(ext, 'text')
        elif url and not data.get('source_type'):
            data['source_type'] = 'html'
        
        return data