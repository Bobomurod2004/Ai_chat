from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.core.cache import cache
from .models import (
    Conversation, Message, FAQ, FAQTranslation, DynamicInfo, Document
)
from .serializers import DocumentSerializer, ConversationSerializer, MessageSerializer
from rag_service import RAGService
from ollama_integration.client import ollama_client
from langdetect import detect
import logging

# Logger setup
logger = logging.getLogger('chatbot_app')

from django.http import StreamingHttpResponse
import json

class ChatbotResponseViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    rag_service = RAGService()

    @action(detail=False, methods=['get'])
    def health(self, request):
        """Service health check."""
        return Response({"status": "ok", "service": "UzSWLU Chatbot API"})

    @action(detail=False, methods=['post'])
    def stream(self, request):
        """Streaming endpoint for real-time responses."""
        user_query = request.data.get('question', '').strip()
        user_id = request.data.get('user_id', 'anonymous')
        platform = request.data.get('platform', 'web')
        session_id = request.data.get('session_id')  # Frontend can specify session
        user_language = request.data.get('language')  # User's selected language
        
        if not user_query:
            return Response({"error": "Question is required"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Conversation Management
        if session_id:
            # Use existing conversation if session_id provided
            try:
                conv = Conversation.objects.get(id=session_id, user_id=user_id)
            except Conversation.DoesNotExist:
                # Session not found, create new one
                conv = Conversation.objects.create(user_id=user_id, platform=platform, is_active=True)
        else:
            # No session_id means NEW CHAT requested
            # Deactivate all previous conversations for this user
            Conversation.objects.filter(user_id=user_id, is_active=True).update(is_active=False)
            
            # Create fresh conversation
            conv = Conversation.objects.create(user_id=user_id, platform=platform, is_active=True)
        
        # 2. Language Detection - PRIORITIZE USER SELECTION
        if user_language and user_language in ['uz', 'ru', 'en']:
            lang_code = user_language
        else:
            # Fallback to auto-detection only if language not provided
            try:
                lang_code = detect(user_query) if len(user_query) > 5 else 'uz'
                if lang_code not in ['uz', 'ru', 'en']: lang_code = 'uz'
            except: 
                lang_code = 'uz'

        # Save user message
        Message.objects.create(conversation=conv, sender_type='user', text=user_query, lang=lang_code)

        def event_stream():
            # Initial ID sync for frontend
            yield f"data: {json.dumps({'session_id': str(conv.id)})}\n\n"
            
            # Retrieval
            retrieval = self.rag_service.retrieve_with_sources(user_query, lang_code=lang_code)
            context = retrieval.get('context', '')
            sources = retrieval.get('sources', [])
            
            full_response = ""
            
            # Stream from Ollama
            for chunk in ollama_client.generate_stream(user_query, context=context, language=lang_code):
                full_response += chunk
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            
            # Save bot message at the end
            Message.objects.create(
                conversation=conv,
                sender_type='bot',
                text=full_response,
                lang=lang_code,
                metadata={'sources': sources}
            )
            
            # Final data
            yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"

        return StreamingHttpResponse(event_stream(), content_type='text/event-stream')

    @action(detail=False, methods=['post'])
    def ask(self, request):
        """Main endpoint for chatbot interaction."""
        user_query = request.data.get('message', '').strip()
        user_id = request.data.get('user_id', 'anonymous')
        platform = request.data.get('platform', 'web')
        
        if not user_query:
            return Response({"error": "Message is required"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Conversation management
        conv, created = Conversation.objects.get_or_create(
            user_id=user_id,
            platform=platform,
            is_active=True
        )
        
        # 2. Language Detection
        try:
            lang_code = detect(user_query)
            if lang_code not in ['uz', 'ru', 'en']:
                lang_code = 'uz'
        except:
            lang_code = 'uz'

        # Save user message
        user_msg = Message.objects.create(
            conversation=conv,
            sender_type='user',
            text=user_query,
            lang=lang_code
        )

        # 3. DynamicInfo / Intent Match (Internal University Info)
        # Check for keywords in DynamicInfo
        dynamic_answer = None
        for info in DynamicInfo.objects.filter(is_active=True):
            if any(keyword.lower() in user_query.lower() for keyword in info.intent_keywords or []):
                dynamic_answer = info.value
                break
        
        if dynamic_answer:
            bot_response = dynamic_answer
            sources = [{'title': 'Dynamic Info', 'source_type': 'database', 'relevance': 100}]
        else:
            # 4. RAG Service - FAQ and Documents
            retrieval = self.rag_service.retrieve_with_sources(user_query, lang_code=lang_code)
            context = retrieval.get('context', '')
            sources = retrieval.get('sources', [])
            
            # 5. LLM Generation
            if retrieval.get('top_answer') and retrieval.get('top_confidence', 0) >= 0.9:
                # Direct answer from high-confidence FAQ
                bot_response = retrieval['top_answer']
            else:
                # Generate via Ollama
                bot_response = ollama_client.generate(user_query, context=context, language=lang_code)

        # 6. Post-processing and Saving
        bot_msg = Message.objects.create(
            conversation=conv,
            sender_type='bot',
            text=bot_response,
            lang=lang_code,
            metadata={'sources': sources}
        )

        return Response({
            "response": bot_response,
            "message_id": bot_msg.id,
            "conversation_id": conv.id,
            "sources": sources,
            "lang": lang_code
        })

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Retrieve conversation history for a specific user or session."""
        user_id = request.query_params.get('user_id')
        session_id = request.query_params.get('session_id')  # Optional: filter by specific session
        
        if not user_id:
            return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # If session_id provided, return only that conversation
        if session_id:
            try:
                conversation = Conversation.objects.get(id=session_id, user_id=user_id)
                serializer = ConversationSerializer(conversation)
                return Response([serializer.data])  # Return as list for consistency
            except Conversation.DoesNotExist:
                return Response([], status=status.HTTP_200_OK)
        
        # Otherwise, return all conversations for user
        conversations = Conversation.objects.filter(user_id=user_id).order_by('-updated_at')
        serializer = ConversationSerializer(conversations, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def feedback(self, request):
        """Handle user feedback for specific messages."""
        message_id = request.data.get('message_id')
        rating = request.data.get('rating') # 1-5 or boolean
        comment = request.data.get('comment', '')
        is_positive = request.data.get('is_positive', True)
        
        try:
            msg = Message.objects.get(id=message_id)
            from .models import Feedback
            Feedback.objects.create(
                message=msg,
                is_positive=is_positive,
                comment=comment
            )
            # Also update message metadata for quick access
            if not msg.metadata:
                msg.metadata = {}
            msg.metadata['has_feedback'] = True
            msg.save(update_fields=['metadata'])
            
            return Response({"status": "success"})
        except Message.DoesNotExist:
            return Response({"error": "Message not found"}, status=status.HTTP_404_NOT_FOUND)

class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [AllowAny]

# Constants needed for context
INTENT_MAP = {
    "tuition": ["kontrakt", "to'lov", "shartnoma", "pul", "narx", "cost", "price"],
    "admission": ["qabul", "hujjat", "topshirish", "kirish"],
}
