from rest_framework import serializers
from .models import Document



class DocumentSerializer(serializers.ModelSerializer):
    """Document upload serializer - Frontend uchun."""
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'title', 'description', 'file', 'file_url', 'url',
            'doc_type', 'status', 'chunks_created', 'error_message',
            'created_at', 'updated_at', 'processed_at'
        ]
        read_only_fields = [
            'id', 'status', 'chunks_created', 'error_message',
            'created_at', 'updated_at', 'processed_at'
        ]
    
    def get_file_url(self, obj):
        """Return full file URL."""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None
    
    def validate(self, data):
        """Validate that either file or url is provided."""
        file = data.get('file')
        url = data.get('url')
        
        if not file and not url:
            raise serializers.ValidationError(
                "Either 'file' or 'url' must be provided."
            )
        
        if file and url:
            raise serializers.ValidationError(
                "Provide either 'file' or 'url', not both."
            )
        
        # Auto-detect doc_type from file extension
        if file and not data.get('doc_type'):
            ext = file.name.split('.')[-1].lower()
            type_map = {
                'pdf': 'pdf',
                'doc': 'word',
                'docx': 'word',
                'txt': 'text',
            }
            data['doc_type'] = type_map.get(ext, 'text')
        elif url and not data.get('doc_type'):
            data['doc_type'] = 'url'
        
        return data