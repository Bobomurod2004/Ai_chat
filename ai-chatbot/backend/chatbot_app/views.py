from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.core.cache import cache
from .models import (
    Conversation, Message, FAQ, FAQTranslation, DynamicInfo, Document, ChatAnalytics
)
from .serializers import DocumentSerializer, ConversationSerializer, MessageSerializer
from rag_service import RAGService
from rag_cache import get_rag_cache
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
    rag_cache = get_rag_cache()

    def _get_rag_response(self, user_query, lang_code, conversation=None):
        """Unified retrieval and generation logic with analytics."""
        import time
        start_time = time.time()
        is_cache_hit = False
        source_type = 'none'

        # 1. Check cache
        cached = self.rag_cache.get(user_query, lang_code)
        if cached:
            is_cache_hit = True
            response_data = {
                'answer': cached['answer'],
                'sources': cached['sources'],
                'is_cache_hit': True,
                'confidence': 1.0,
                'source_type': 'hybrid'
            }
        else:
            # 2. Retrieval via RAG Service
            try:
                retrieval = self.rag_service.retrieve_with_self_correction(user_query, lang_code=lang_code)
                context = retrieval.get('context', '')
                sources = retrieval.get('sources', [])
                confidence = retrieval.get('grading_result', {}).get('confidence', 0.0)
                
                # Determine source type for analytics
                if sources:
                    source_type = sources[0].get('source_type', 'unknown') if len(sources) > 0 else 'none'

                # 3. Decision: Use direct answer or Ollama
                if retrieval.get('top_answer') and retrieval.get('top_confidence', 0) >= 0.9:
                    answer = retrieval['top_answer']
                else:
                    answer = ollama_client.generate(user_query, context=context, language=lang_code)
                
                error_log = None
            except Exception as e:
                logger.error(f"RAG/Ollama Error: {str(e)}")
                # Professional localized fallback
                fallbacks = {
                    'uz': "Kechirasiz, tizimda vaqtinchalik texnik nosozlik yuz berdi. Iltimos, birozdan so'ng qayta urinib ko'ring.",
                    'ru': "Извините, произошла временная техническая ошибка. Пожалуйста, попробуйте позже.",
                    'en': "Sorry, a temporary technical error occurred. Please try again later."
                }
                answer = fallbacks.get(lang_code, fallbacks['uz'])
                sources = []
                confidence = 0.0
                error_log = str(e)

            response_data = {
                'answer': answer,
                'sources': sources,
                'is_cache_hit': False,
                'confidence': confidence,
                'source_type': source_type,
                'error': error_log,
                'is_error': error_log is not None
            }
            
            # 4. Cache it (only if no error)
            if not error_log:
                self.rag_cache.set(user_query, lang_code, {
                    'answer': answer,
                    'sources': sources
                })

        # 5. Save and analytics log if conversation provided (always record attempt)
        if conversation:
            bot_msg = Message.objects.create(
                conversation=conversation,
                sender_type='bot',
                text=response_data['answer'],
                lang=lang_code,
                metadata={'sources': response_data['sources'], 'is_cache_hit': is_cache_hit, 'error': response_data.get('error')}
            )
            
            # Save Analytics
            duration = time.time() - start_time
            ChatAnalytics.objects.create(
                message=bot_msg,
                response_time=duration,
                confidence_score=response_data['confidence'],
                source_type=response_data['source_type'],
                is_cache_hit=is_cache_hit,
                language=lang_code,
                error_log=response_data.get('error')
            )
            response_data['bot_msg_id'] = bot_msg.id

        return response_data


    def _get_history_text(self, conversation, limit=5):
        """Format recent chat history for the agent."""
        messages = conversation.messages.all().order_by('-created_at')[:limit]
        history = []
        for msg in reversed(messages):
            role = "User" if msg.sender_type == 'user' else "Assistant"
            history.append(f"{role}: {msg.text}")
        return "\n".join(history)

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
            
            # Unified retrieval and generation logic
            response_data = self._get_rag_response(user_query, lang_code, conversation=conv)
            
            if response_data['is_cache_hit']:
                yield f"data: {json.dumps({'type': 'cache_hit'})}\n\n"
            
            if response_data.get('is_error'):
                yield f"data: {json.dumps({'error': response_data['answer']})}\n\n"
                return

            # Since _get_rag_response uses .generate(), we still need to stream for real-time feel
            for char in response_data['answer']:
                yield f"data: {json.dumps({'chunk': char})}\n\n"
            
            # Final data
            yield f"data: {json.dumps({'done': True, 'sources': response_data['sources']})}\n\n"

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
        dynamic_answer = None
        for info in DynamicInfo.objects.filter(is_active=True):
            if any(keyword.lower() in user_query.lower() for keyword in info.intent_keywords or []):
                val = getattr(info, f'value_{lang_code}', info.value_uz)
                dynamic_answer = val if val else info.value_uz
                break
        
        if dynamic_answer:
            bot_response = dynamic_answer
            sources = [{'title': 'Dynamic Info', 'source_type': 'database', 'relevance': 100}]
            bot_msg = Message.objects.create(
                conversation=conv,
                sender_type='bot',
                text=bot_response,
                lang=lang_code,
                metadata={'sources': sources}
            )
        else:
            # 4. Use Unified RAG Response
            response_data = self._get_rag_response(user_query, lang_code, conversation=conv)
            bot_response = response_data['answer']
            sources = response_data['sources']
            is_error = response_data.get('is_error', False)

        return Response({
            "response": bot_response,
            "conversation_id": conv.id,
            "sources": sources,
            "lang": lang_code,
            "is_error": is_error
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

