#flake8: noqa
"""
UzSWLU Chatbot Views - Clean English Version
Simple and efficient chatbot API endpoints with caching
10,000+ user uchun optimizatsiya qilingan
"""
# flake8: noqa
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.http import StreamingHttpResponse
from django.core.cache import cache
from django.utils import timezone
from .models import (
    ChatSession, DynamicInfo, 
    ChatLog, SessionMemory, Feedback, ChatAnalytics, Document
)
from .serializers import DocumentSerializer
from ollama_integration.client import ollama_client
try:
    from langdetect import detect, LangDetectException
except ImportError:
    detect = None
import json
import hashlib
import uuid
import time
import logging

# Logger setup - Error monitoring uchun
logger = logging.getLogger('chatbot_app')

# Cache timeout (10 minutes)
CACHE_TIMEOUT = 600

# Intent mapping for DynamicInfo - Robust synonym matching
INTENT_MAP = {
    "tuition": ["kontrakt", "to'lov", "shartnoma", "pul", "narx", "cost", "price", "to’lov", "to`lov", "shartnoma puli", "to‘lov"],
    "admission": ["qabul", "hujjat", "topshirish", "kirish", "deadline", "vaqt", "admission", "registration", "imtihon"],
    "contact": ["telefon", "aloqa", "manzil", "joylashuv", "location", "address", "phone", "rector", "email", "pochta"],
    "working_hours": ["ish vaqti", "soat", "vaqti", "working hours", "open", "yopiq", "ochiq", "jadval"],
}

KEY_MAPPINGS = {
    "tuition": ["tuition_fee", "contract_price", "payment_deadline"],
    "admission": ["admission_start", "admission_end", "admission_deadline"],
    "contact": ["main_phone", "admission_phone", "hotline", "main_email", "address", "location", "rector_name"],
    "working_hours": ["working_hours", "office_hours", "library_hours"],
}

# RAG service import
try:
    from rag_service import get_rag_service
    RAG_ENABLED = True
except ImportError:
    RAG_ENABLED = False
    import logging
    logging.getLogger('chatbot_app').warning("RAG service not available")


def get_cache_key(question: str, language: str = 'en') -> str:
    """Generate unique cache key for question."""
    q_normalized = question.lower().strip()
    key_str = f"chatbot:{language}:{q_normalized}"
    return hashlib.md5(key_str.encode()).hexdigest()


def get_dynamic_context(question):
    """Get relevant dynamic info based on intent mapping - Robust matching."""
    q_lower = question.lower()
    
    # Cache key - question keywords asosida
    cache_key = f"dynamic_context:v2:{hashlib.md5(q_lower.encode()).hexdigest()}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    matching_keys = set()
    
    # 1. Check INTENT_MAP for synonyms
    for intent, synonyms in INTENT_MAP.items():
        if any(syn in q_lower for syn in synonyms):
            keys = KEY_MAPPINGS.get(intent, [])
            matching_keys.update(keys)
    
    context_parts = []
    
    # 2. Get dynamic info values
    if matching_keys:
        infos = DynamicInfo.objects.filter(
            key__in=matching_keys,
            is_active=True
        )
        for info in infos:
            # Limit long values
            value = info.value
            if len(value) > 1500:
                value = value[:1500] + "... (truncated)"
            context_parts.append(f"{info.description or info.key}: {value}")
    
    result = '\n'.join(context_parts)
    if len(result) > 3000:
        result = result[:3000] + "\n... (more data available)"
    
    final_result = result if context_parts else ''
    
    # Cache result - 1 soat
    cache.set(cache_key, final_result, 3600)
    
    return final_result


def is_university_related(question):
    """Check if question is related to university/education."""
    q_lower = question.lower()
    
    # Greetings - always allow
    greetings = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'salom']
    if any(g in q_lower for g in greetings):
        return True
    
    # University-specific keywords (must match at least one)
    university_keywords = [
        'uzswlu', 'university', 'universitet', 'oliy', 'talaba',
        'admission', 'qabul', 'faculty', 'fakultet', 'faculties',
        'tuition', 'kontrakt', 'fee', 'scholarship', 'grant', 'shartnoma', 'to\'lov', 'to‘lov', 'to`lov', 'pul',
        'bachelor', 'bakalavr', 'master', 'magistr', 'phd', 'doktorant',
        'degree', 'daraja', 'diploma', 'study', 'o\'qish',
        'course', 'department', 'kafedra', 'dean', 'dekan', 'rector',
        'dormitory', 'yotoqxona', 'library', 'kutubxona',
        'english', 'german', 'french', 'russian', 'chinese',
        'japanese', 'korean', 'arabic', 'spanish', 'italian',
        'language', 'til', 'translation', 'tarjima', 'linguistics',
        'philology', 'filologiya', 'exam', 'imtihon', 'semester',
        'certificate', 'sertifikat', 'address', 'manzil',
        'phone', 'telefon', 'contact', 'aloqa', 'location',
        'tashkent', 'toshkent', 'uzbekistan', 'o\'zbekiston',
        'exchange', 'program', 'dastur', 'international', 'xalqaro',
        'partner', 'joint', 'birgalikda', 'education', 'ta\'lim',
        'dtm', 'test', 'imtihon', 'grant', 'stipendiya',
        'working hours', 'ish vaqti', 'schedule', 'jadval',
    ]
    
    # Block clearly unrelated topics
    blocked_topics = [
        'pizza', 'weather', 'football', 'movie', 'song', 'game',
        'cook', 'recipe', 'sport', 'news', 'politics', 'joke',
        'music', 'car', 'travel', 'hotel', 'restaurant',
    ]
    
    # If contains blocked topic, reject
    if any(blocked in q_lower for blocked in blocked_topics):
        return False
    
    # Must contain at least one university keyword
    return any(kw in q_lower for kw in university_keywords)


def detect_intent(question):
    """Simple intent detection based on keywords."""
    q_lower = question.lower()
    if any(kw in q_lower for kw in ['admission', 'qabul', 'hujjat', 'deadline']):
        return 'admission'
    if any(kw in q_lower for kw in ['tuition', 'kontrakt', 'fee', 'price', 'to\'lov']):
        return 'tuition'
    if any(kw in q_lower for kw in ['faculty', 'fakultet', 'kafedra', 'department']):
        return 'academics'
    if any(kw in q_lower for kw in ['dormitory', 'yotoqxona', 'hostel']):
        return 'dormitory'
    if any(kw in q_lower for kw in ['hello', 'hi', 'salom', 'hey']):
        return 'greeting'
    if any(kw in q_lower for kw in ['thank', 'rahmat', 'thanks']):
        return 'gratitude'
    return 'general'


class ChatbotResponseViewSet(viewsets.ViewSet):
    """Main chatbot API viewset."""
    permission_classes = [AllowAny]

    def _handle_greeting(self, question, language='uz'):
        """Handle simple greetings - ko'p tilli."""
        q_lower = question.lower().strip()
        
        # Tilga mos greeting'lar
        greetings = {
            'uz': {
                'pure': ['salom', 'assalomu alaykum', 'hello', 'hi', 'hey'],
                'responses': {
                    'salom': "Salom! Men UzSWLU chatbot'iman. Qanday yordam bera olaman?",
                    'assalomu alaykum': "Assalomu alaykum! Men UzSWLU chatbot'iman. Savolingizni bering.",
                    'hello': "Salom! Men UzSWLU chatbot'iman. Qanday yordam bera olaman?",
                    'hi': "Salom! Men UzSWLU chatbot'iman. Qanday yordam bera olaman?",
                    'hey': "Salom! Men UzSWLU chatbot'iman. Qanday yordam bera olaman?",
                },
                'starts': [
                    ('salom', "Salom! Men UzSWLU chatbot'iman. Qanday yordam bera olaman?"),
                    ('assalomu alaykum', "Assalomu alaykum! Men UzSWLU chatbot'iman. Savolingizni bering."),
                ]
            },
            'ru': {
                'pure': ['привет', 'здравствуйте', 'добрый день', 'доброе утро', 'добрый вечер', 'hello', 'hi'],
                'responses': {
                    'привет': "Привет! Я чат-бот UzSWLU. Чем могу помочь?",
                    'здравствуйте': "Здравствуйте! Я чат-бот UzSWLU. Чем могу помочь?",
                    'добрый день': "Добрый день! Я чат-бот UzSWLU. Чем могу помочь?",
                    'доброе утро': "Доброе утро! Я чат-бот UzSWLU. Чем могу помочь?",
                    'добрый вечер': "Добрый вечер! Я чат-бот UzSWLU. Чем могу помочь?",
                    'hello': "Привет! Я чат-бот UzSWLU. Чем могу помочь?",
                    'hi': "Привет! Я чат-бот UzSWLU. Чем могу помочь?",
                },
                'starts': [
                    ('привет', "Привет! Я чат-бот UzSWLU. Чем могу помочь?"),
                    ('здравствуйте', "Здравствуйте! Я чат-бот UzSWLU. Чем могу помочь?"),
                    ('добрый день', "Добрый день! Я чат-бот UzSWLU. Чем могу помочь?"),
                    ('доброе утро', "Доброе утро! Я чат-бот UzSWLU. Чем могу помочь?"),
                    ('добрый вечер', "Добрый вечер! Я чат-бот UzSWLU. Чем могу помочь?"),
                ]
            },
            'en': {
                'pure': ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening'],
                'responses': {
                    'hello': "Hello! I'm UzSWLU chatbot. How can I help you today?",
                    'hi': "Hi! I'm UzSWLU chatbot. How can I help you today?",
                    'hey': "Hey! I'm UzSWLU chatbot. How can I help you today?",
                    'good morning': "Good morning! I'm UzSWLU chatbot. How can I assist you?",
                    'good afternoon': "Good afternoon! I'm UzSWLU chatbot. What would you like to know?",
                    'good evening': "Good evening! I'm UzSWLU chatbot. How can I help you?",
                },
                'starts': [
                    ('hello', "Hello! I'm UzSWLU chatbot. How can I help you today?"),
                    ('hi', "Hi! I'm UzSWLU chatbot. How can I help you today?"),
                    ('good morning', "Good morning! I'm UzSWLU chatbot. How can I assist you?"),
                    ('good afternoon', "Good afternoon! I'm UzSWLU chatbot. What would you like to know?"),
                    ('good evening', "Good evening! I'm UzSWLU chatbot. How can I help you?"),
                ]
            }
        }
        
        lang_greetings = greetings.get(language, greetings['uz'])
        
        # Faqat sof greeting bo'lsa
        for greeting in lang_greetings['pure']:
            if q_lower == greeting:
                return lang_greetings['responses'].get(greeting, lang_greetings['responses'].get('hello', "Hello!"))
        
        # Greeting bilan boshlansa va qisqa bo'lsa
        for greeting, response in lang_greetings['starts']:
            if q_lower.startswith(greeting) and len(q_lower) < 30:
                return response
        
        return None

    @action(detail=False, methods=['get'])
    def health(self, request):
        """Comprehensive health check endpoint - 10,000+ user uchun monitoring."""
        import redis
        from django.conf import settings
        
        status_data = {
            'status': 'healthy',
            'service': 'chatbot',
            'rag_enabled': RAG_ENABLED,
            'timestamp': time.time(),
        }
        all_healthy = True
        
        # Check database
        try:
            db_start = time.time()
            ChatSession.objects.count()
            db_time = time.time() - db_start
            status_data['database'] = {
                'status': 'ok',
                'response_time_ms': round(db_time * 1000, 2)
            }
        except Exception as e:
            status_data['database'] = {
                'status': 'error',
                'error': str(e)[:100]
            }
            all_healthy = False
        
        # Check Redis (Cache)
        try:
            redis_start = time.time()
            cache.set('health_check', 'ok', 10)
            cache.get('health_check')
            redis_time = time.time() - redis_start
            status_data['redis'] = {
                'status': 'ok',
                'response_time_ms': round(redis_time * 1000, 2)
            }
        except Exception as e:
            status_data['redis'] = {
                'status': 'error',
                'error': str(e)[:100]
            }
            all_healthy = False
        
        # Check RAG service (ChromaDB)
        if RAG_ENABLED:
            try:
                chroma_start = time.time()
                rag = get_rag_service()
                doc_count = rag.collection.count()
                chroma_time = time.time() - chroma_start
                status_data['chromadb'] = {
                    'status': 'ok',
                    'docs_count': doc_count,
                    'response_time_ms': round(chroma_time * 1000, 2)
                }
            except Exception as e:
                status_data['chromadb'] = {
                    'status': 'error',
                    'error': str(e)[:100]
                }
                all_healthy = False
        
        # Check Ollama
        try:
            ollama_start = time.time()
            import requests
            ollama_url = getattr(settings, 'OLLAMA_URL', 'http://ollama:11434')
            response = requests.get(f"{ollama_url}/api/tags", timeout=5)
            ollama_time = time.time() - ollama_start
            if response.status_code == 200:
                status_data['ollama'] = {
                    'status': 'ok',
                    'response_time_ms': round(ollama_time * 1000, 2)
                }
            else:
                status_data['ollama'] = {
                    'status': 'error',
                    'error': f'HTTP {response.status_code}'
                }
                all_healthy = False
        except Exception as e:
            status_data['ollama'] = {
                'status': 'error',
                'error': str(e)[:100]
            }
            all_healthy = False
        
        # Overall status
        if not all_healthy:
            status_data['status'] = 'unhealthy'
        
        # Statistics
        try:
            status_data['stats'] = {
                'total_sessions': ChatSession.objects.filter(is_active=True).count(),
                'total_analytics': ChatAnalytics.objects.count(),
            }
        except Exception:
            pass
        
        return Response(status_data, status=200 if all_healthy else 503)

    def _get_or_create_session(self, session_id_str=None, user=None, language='uz'):
        """Get existing session or create new one - Query Optimization bilan."""
        if session_id_str:
            try:
                # Handle both UUID object and string
                if isinstance(session_id_str, str):
                    session_id = uuid.UUID(session_id_str)
                else:
                    session_id = session_id_str
                
                # Query Optimization: select_related user bilan
                session = ChatSession.objects.select_related('user').filter(
                    session_id=session_id, 
                    is_active=True
                ).first()
                
                if session:
                    # Update language if provided
                    if language and session.language != language:
                        session.language = language
                        session.save(update_fields=['language', 'updated_at'])
                    return session
            except (ValueError, TypeError, ChatSession.DoesNotExist):
                pass
        
        # Create new session
        session = ChatSession.objects.create(
            user=user if user and user.is_authenticated else None,
            language=language
        )
        # Ensure memory exists
        SessionMemory.objects.get_or_create(session=session)
        return session

    def _update_session_memory(self, session, user_msg, bot_msg):
        """Update SessionMemory with latest interaction summary."""
        try:
            memory, _ = SessionMemory.objects.get_or_create(session=session)
            # Simple heuristic: Keep last 3 interactions in memory
            new_entry = f"U: {user_msg[:100]} | A: {bot_msg[:100]}"
            if memory.summary:
                parts = memory.summary.split('\n')
                if len(parts) > 2:
                    parts = parts[-2:]
                parts.append(new_entry)
                memory.summary = '\n'.join(parts)
            else:
                memory.summary = new_entry
            memory.interaction_count += 1
            memory.save(update_fields=['summary', 'interaction_count', 'updated_at'])
        except Exception as e:
            logger.warning(f"Error updating session memory: {e}")
    
    def _build_conversation_context(self, session, limit=5):
        """Build conversation context from SessionMemory (Summary)."""
        try:
            # Get memory
            memory, created = SessionMemory.objects.get_or_create(session=session)
            if memory.summary:
                return f"Previous conversation summary: {memory.summary}\n\n"
            
            # Fallback to recent logs if summary is empty (first few turns)
            history = list(
                session.logs.only('user_message', 'bot_response')
                .order_by('-turn_number')[:2]
                .values('user_message', 'bot_response')
            )[::-1]
            
            if not history:
                return ""
            
            context_parts = ["Recent interactions:"]
            for turn in history:
                context_parts.append(f"Q: {turn['user_message']}")
                context_parts.append(f"A: {turn['bot_response']}")
            
            return "\n".join(context_parts) + "\n\n"
        except Exception as e:
            logger.warning(f"Error building conversation context: {e}")
            return ""
    
    @action(detail=False, methods=['post'])
    def ask(self, request):
        """Answer questions about UzSWLU."""
        question = request.data.get('question', '').strip()
        session_id_str = request.data.get('session_id')
        language = request.data.get('language', 'uz').lower()  # Default: uz
        if language not in ['uz', 'ru', 'en']:
            language = 'uz'
        
        # Auto-detect language if enabled using langdetect
        if detect and len(question) > 5:
            try:
                detected_lang = detect(question)
                if detected_lang in ['uz', 'ru', 'en'] and detected_lang != language:
                    language = detected_lang
                    logger.debug(f"Auto-detected language: {language}")
            except Exception as e:
                logger.warning(f"Language detection error: {e}", exc_info=True)

        start_time = time.time()
        
        # Validation
        if not question:
            return Response(
                {'error': 'Question is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(question) > 500:
            return Response(
                {'error': 'Question too long (max 500 characters)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get or create session
        session = self._get_or_create_session(
            session_id_str=session_id_str,
            user=request.user,
            language=language
        )
        
        # Handle greetings - tilga mos
        greeting_response = self._handle_greeting(question, language=language)
        if greeting_response:
            # Save to ChatLog
            turn_number = session.total_turns + 1
            ChatLog.objects.create(
                session=session,
                turn_number=turn_number,
                user_message=question,
                bot_response=greeting_response,
                intent='greeting',
                metadata={'confidence': 1.0, 'is_greeting': True}
            )
            session.total_turns = turn_number
            session.last_intent = 'greeting'
            session.save()
            # Update Memory
            self._update_session_memory(session, question, greeting_response)
            
            return Response({
                'id': 0, # Legacy ID placeholder
                'session_id': str(session.session_id),
                'question': question,
                'response': greeting_response,
                'confidence': 1.0,
                'sources': [],
                'created_at': timezone.now().isoformat()
            }, status=status.HTTP_201_CREATED)
        
        # Check if university related
        if not is_university_related(question):
            return Response({
                'error': 'I only answer questions about UzSWLU (Uzbekistan State World Languages University).',
                'hint': 'Please ask about admission, faculties, programs, tuition, or contact information.',
                'examples': [
                    'When does admission start?',
                    'What faculties are there?',
                    'How much is the tuition fee?',
                    'Where is UzSWLU located?'
                ]
            }, status=status.HTTP_200_OK)
        
        try:
            # Get conversation history for context
            conversation_context = self._build_conversation_context(session, limit=5)
            
            # Check cache first
            # Use the 'language' variable already detected/provided above
            cache_key = get_cache_key(question, language)
            cached_response = cache.get(cache_key)
            
            if cached_response:
                # Save to ChatLog even if cached
                turn_number = session.total_turns + 1
                ChatLog.objects.create(
                    session=session,
                    turn_number=turn_number,
                    user_message=question,
                    bot_response=cached_response['response'],
                    intent=detect_intent(question),
                    metadata={
                        'confidence': cached_response['confidence'],
                        'was_cached': True,
                        'response_time': time.time() - start_time,
                        'sources': cached_response.get('sources', [])
                    }
                )
                session.total_turns = turn_number
                session.last_intent = detect_intent(question)
                session.save()
                # Update Memory
                self._update_session_memory(session, question, cached_response['response'])
                
                # Analytics Tracking - cached response uchun ham
                try:
                    ChatAnalytics.objects.create(
                        session=session,
                        query=question,
                        query_length=len(question),
                        intent=detect_intent(question),
                        detected_language=language,
                        response=cached_response['response'],
                        response_length=len(cached_response['response']),
                        response_time=0.001,  # Caching is near-instant
                        was_cached=True,
                        confidence_score=cached_response['confidence'],
                        sources_count=len(cached_response.get('sources', [])),
                        top_source_confidence=cached_response['confidence'],
                        sources_used=cached_response.get('sources', []),
                        search_type='cached',
                        error_occurred=False,
                    )
                except Exception as analytics_error:
                    logger.warning(f"Analytics tracking error (cached): {analytics_error}", exc_info=True)
                
                return Response({
                    'id': 0,
                    'session_id': str(session.session_id),
                    'question': question,
                    'response': cached_response['response'],
                    'confidence': cached_response['confidence'],
                    'sources': cached_response['sources'],
                    'cached': True,
                    'created_at': cached_response['created_at']
                }, status=status.HTTP_200_OK)
            
            # 1. DYNAMIC INFO CHECK (AI BYPASS)
            dynamic_context = get_dynamic_context(question)
            
            # 2. RAG/FAQ RETRIEVAL
            context = ""
            sources = []
            confidence = 0.5
            
            if RAG_ENABLED:
                rag = get_rag_service()
                result = rag.retrieve_with_sources(question, top_k=5)
                context = result.get('context', '')
                confidence = result.get('top_source', {}).get('confidence', 0.5) if result.get('top_source') else 0.5
                
                # Extract sources
                for src in result.get('sources', [])[:3]:
                    sources.append({
                        'file': src.get('source_type', 'faq'),
                        'title': src.get('title', 'UzSWLU'),
                        'relevance': round(src.get('confidence', 0) * 100, 1),
                        'type': src.get('source_type', 'faq')
                    })

            # 3. AI BYPASS DECISION (DIRECT RETURN)
            # If high confidence FAQ or specific Dynamic Match, skip LLM
            # (Note: dynamic_context alone might be too much info, but if it matches intent we can return it)
            
            response_text = ""
            was_ai_bypassed = False
            
            # Case A: High Confidence FAQ (Score >= 0.75)
            if confidence >= 0.75 and sources and sources[0]['type'] == 'faq':
                response_text = context.split('\n', 1)[1] if '\n' in context else context
                # Clean up context markers if any
                if response_text.startswith('[') and ']' in response_text[:50]:
                    response_text = response_text.split(']', 1)[1].strip()
                was_ai_bypassed = True
                logger.info("🚀 AI Bypassed: High confidence FAQ")
            
            # Case B: Dynamic Info Match (Only if it's the primary match)
            elif dynamic_context and not context:
                response_text = dynamic_context
                was_ai_bypassed = True
                logger.info("🚀 AI Bypassed: Dynamic Info Only")
            
            # If not bypassed, follow standard flow
            if not response_text:
                # Add dynamic info to context for LLM
                if dynamic_context:
                    context = f"Current Information:\n{dynamic_context}\n\n{context}"
                    sources.append({
                        'file': 'dynamic',
                        'title': 'Current Data',
                        'relevance': 95.0,
                        'type': 'dynamic'
                    })
                
                # Combine conversation history with context
                full_context = conversation_context + context if conversation_context else context
                
                # NO-ANSWER DETECTION: If confidence too low
                if confidence < 0.3 and not dynamic_context:
                    fallbacks = {
                        'uz': "Bu savol bo‘yicha rasmiy hujjatlarda aniq ma’lumot topilmadi.",
                        'ru': "По данному вопросу в официальных документах точной информации не найдено.",
                        'en': "No specific information was found in the official documents regarding this question."
                    }
                    response_text = fallbacks.get(language, fallbacks['uz'])
                else:
                    # Generate response with Ollama
                    response_text = ollama_client.generate(question, context=full_context, language=language)
            
            # Clean up response
            response_text = response_text.strip()
            if not response_text:
                response_text = (
                    "I couldn't find relevant information. "
                    "Please visit uzswlu.uz for more details."
                )
            
            response_time = time.time() - start_time
            
            # Save to ChatLog
            turn_number = session.total_turns + 1
            ChatLog.objects.create(
                session=session,
                turn_number=turn_number,
                user_message=question,
                bot_response=response_text,
                intent=detect_intent(question),
                metadata={
                    'confidence': confidence,
                    'response_time': response_time,
                    'sources': sources,
                    'is_fallback': confidence < 0.3 and not dynamic_context
                }
            )
            session.total_turns = turn_number
            session.last_intent = detect_intent(question)
            session.save()
            
            # Update Memory
            self._update_session_memory(session, question, response_text)
            
            # Analytics Tracking - 10,000+ user uchun monitoring
            try:
                ChatAnalytics.objects.create(
                    session=session,
                    query=question,
                    query_length=len(question),
                    intent=detect_intent(question),
                    detected_language=language,
                    response=response_text,
                    response_length=len(response_text),
                    response_time=response_time,
                    was_cached=False,
                    confidence_score=confidence,
                    sources_count=len(sources),
                    top_source_confidence=confidence,
                    sources_used=sources,
                    search_type='hybrid',
                    error_occurred=False,
                )
            except Exception as analytics_error:
                # Analytics xatolik bo'lsa ham asosiy flow ishlashi kerak
                logger.warning(f"Analytics tracking error: {analytics_error}", exc_info=True)
            
            # Cache the response
            if response_text and confidence >= 0.3:
                cache_data = {
                    'response': response_text,
                    'confidence': round(confidence, 2),
                    'sources': sources,
                    'created_at': timezone.now().isoformat()
                }
                cache.set(cache_key, cache_data, CACHE_TIMEOUT)
            
            return Response({
                'id': 0,
                'session_id': str(session.session_id),
                'question': question,
                'response': response_text,
                'confidence': round(confidence, 2),
                'sources': sources,
                'cached': False,
                'created_at': timezone.now().isoformat()
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            import traceback
            error_message = str(e)
            error_traceback = traceback.format_exc()
            
            # Error Logging - 10,000+ user uchun monitoring
            logger.error(f"Chatbot ask() error: {str(e)}", exc_info=True)
            import traceback
            
            # Error Analytics Tracking
            try:
                session = self._get_or_create_session(
                    session_id_str=request.data.get('session_id'),
                    user=request.user,
                    language=language
                )
                ChatAnalytics.objects.create(
                    session=session,
                    query=question,
                    query_length=len(question) if question else 0,
                    intent='error',
                    detected_language=language,
                    response='',
                    response_length=0,
                    response_time=time.time() - start_time,
                    was_cached=False,
                    confidence_score=0.0,
                    sources_count=0,
                    error_occurred=True,
                    error_message=error_message[:500],  # Limit error message length
                )
            except Exception as analytics_error:
                logger.error(f"Error analytics tracking failed: {analytics_error}", exc_info=True)
            
            return Response({
                'error': 'An error occurred. Please try again.',
                'question': question
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def stream(self, request):
        """Stream response for real-time output."""
        try:
            question = request.data.get('question', '').strip()
            session_id_str = request.data.get('session_id')
            language = request.data.get('language', 'uz').lower()  # Default: uz
            # Validate language
            if language not in ['uz', 'ru', 'en']:
                language = 'uz'
            
            # Auto-detect language
            if detect and len(question) > 5:
                try:
                    detected_lang = detect(question)
                    if detected_lang in ['uz', 'ru', 'en'] and detected_lang != language:
                        language = detected_lang
                except Exception:
                    pass

            start_time = time.time()
            
            if not question:
                return Response({'error': 'Question is required'}, status=400)
            
            # Get or create session
            try:
                session = self._get_or_create_session(
                    session_id_str=session_id_str,
                    user=request.user,
                    language=language
                )
            except Exception as e:
                logger.error(f"Error creating/getting session: {e}", exc_info=True)
                return Response({'error': f'Session error: {str(e)}'}, status=500)
            
            # Handle greetings - tilga mos
            greeting_response = self._handle_greeting(question, language=language)
            if greeting_response:
                # Save to ChatLog
                turn_number = session.total_turns + 1
                ChatLog.objects.create(
                    session=session,
                    turn_number=turn_number,
                    user_message=question,
                    bot_response=greeting_response,
                    intent='greeting',
                    metadata={'confidence': 1.0, 'is_greeting': True}
                )
                session.total_turns = turn_number
                session.last_intent = 'greeting'
                session.save()
                # Update Memory
                self._update_session_memory(session, question, greeting_response)
                
                def greeting_gen():
                    yield f"data: {json.dumps({'chunk': greeting_response, 'session_id': str(session.session_id)})}\n\n"
                    yield f"data: {json.dumps({'done': True, 'session_id': str(session.session_id)})}\n\n"
                return StreamingHttpResponse(
                    greeting_gen(),
                    content_type='text/event-stream'
                )
            
            # Get conversation history for context
            try:
                conversation_context = self._build_conversation_context(session, limit=5)
            except Exception as e:
                logger.warning(f"Error getting conversation context: {e}", exc_info=True)
                conversation_context = ""
            
            # Get context from RAG
            context = ""
            sources = []
            confidence = 0.5  # Default confidence for streaming
            try:
                if RAG_ENABLED:
                    rag = get_rag_service()
                    
                    # MULTILINGUAL STRATEGY: Multilingual embedding bilan qidirish
                    # Hujjatlar qanday tilda bo'lishidan qat'iy nazar, bir xil embedding space'da qidiriladi
                    result = rag.retrieve_with_sources(question, top_k=5)
                    context = result.get('context', '')
                    confidence = result.get('top_source', {}).get('confidence', 0.5) if result.get('top_source') else 0.5
                    
                    # Extract sources
                    for src in result.get('sources', [])[:3]:
                        sources.append({
                            'file': src.get('source_type', 'faq'),
                            'title': src.get('title', 'UzSWLU'),
                            'relevance': round(src.get('confidence', 0) * 100, 1),
                            'type': src.get('source_type', 'faq')
                        })
            except Exception as e:
                logger.error(f"Error getting RAG context: {e}", exc_info=True)
            
            # Add dynamic info context
            dynamic_context = get_dynamic_context(question)
            if dynamic_context:
                context = f"Current Information:\n{dynamic_context}\n\n{context}"
                sources.append({
                    'file': 'dynamic',
                    'title': 'Current Data',
                    'relevance': 95.0,
                    'type': 'dynamic'
                })
            
            # Combine conversation history with RAG context
            full_context = conversation_context + context if conversation_context else context
            
            # NO-ANSWER DETECTION: If confidence too low, give honest response
            if confidence < 0.3 and not dynamic_context:
                fallbacks = {
                    'uz': "Bu savol bo‘yicha rasmiy hujjatlarda aniq ma’lumot topilmadi.",
                    'ru': "По данному вопросу в official'nyh dokumentah tochnoy informatsii ne naydeno.",
                    'en': "No specific information was found in the official documents regarding this question."
                }
                fallback_msg = fallbacks.get(language, fallbacks['uz'])
                
                def fallback_gen():
                    yield f"data: {json.dumps({'session_id': str(session.session_id)})}\n\n"
                    yield f"data: {json.dumps({'chunk': fallback_msg})}\n\n"
                    yield f"data: {json.dumps({'done': True, 'sources': []})}\n\n"
                return StreamingHttpResponse(fallback_gen(), content_type='text/event-stream')

            full_response_text = ""
            
            def generate():
                nonlocal full_response_text
                try:
                    # Send session_id first
                    yield f"data: {json.dumps({'session_id': str(session.session_id)})}\n\n"
                    
                    for chunk in ollama_client.generate_stream(question, context=full_context, language=language):
                        full_response_text += chunk
                        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                    
                    # Save to ChatLog after streaming is complete
                    try:
                        response_time = time.time() - start_time
                        turn_number = session.total_turns + 1
                        ChatLog.objects.create(
                            session=session,
                            turn_number=turn_number,
                            user_message=question,
                            bot_response=full_response_text,
                            intent=detect_intent(question),
                            metadata={
                                'confidence': 0.5,
                                'response_time': response_time,
                                'sources': sources,
                                'is_stream': True
                            }
                        )
                        session.total_turns = turn_number
                        session.last_intent = detect_intent(question)
                        session.save()
                        
                        # Update Memory
                        self._update_session_memory(session, question, full_response_text)
                        
                    except Exception as db_error:
                        # Log database error but don't fail the stream
                        logger.error(f"Database error in stream: {db_error}", exc_info=True)
                    
                    yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"
                except Exception as e:
                    logger.error(f"Streaming error: {e}", exc_info=True)
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
            response = StreamingHttpResponse(
                generate(),
                content_type='text/event-stream'
            )
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response
        except Exception as e:
            logger.error(f"Stream endpoint error: {e}", exc_info=True)
            return Response({
                'error': f'Server error: {str(e)}'
            }, status=500)

    @action(detail=False, methods=['post'])
    def feedback(self, request):
        """Save user feedback - Updated to use ChatLog."""
        log_id = request.data.get('log_id') or request.data.get('response_id')
        rating = request.data.get('rating')  # 'positive' or 'negative'
        feedback_text = request.data.get('feedback_text', '')
        
        if not log_id:
            return Response(
                {'error': 'log_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if rating not in ['positive', 'negative']:
            return Response(
                {'error': 'rating must be "positive" or "negative"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            chat_log = ChatLog.objects.get(id=log_id)
        except ChatLog.DoesNotExist:
            return Response(
                {'error': 'Chat log not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create or update feedback
        feedback, created = Feedback.objects.get_or_create(
            chat_log=chat_log,
            user=request.user if request.user.is_authenticated else None,
            defaults={
                'rating': rating,
                'admin_notes': feedback_text if feedback_text else ''
            }
        )
        
        if not created:
            feedback.rating = rating
            if feedback_text:
                feedback.admin_notes = feedback_text
            feedback.save()
        
        return Response({
            'success': True,
            'message': 'Feedback saved successfully',
            'feedback_id': feedback.id
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get conversation history for a session - Query Optimized."""
        session_id_str = request.query_params.get('session_id')
        if not session_id_str:
            return Response(
                {'error': 'session_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        session = self._get_or_create_session(session_id_str=session_id_str)
        if not session:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get logs - Optimized
        history_data = list(
            session.logs.only(
                'turn_number', 'user_message', 'bot_response', 'intent', 'timestamp'
            )
            .order_by('turn_number')[:50]
            .values('turn_number', 'user_message', 'bot_response', 'intent', 'timestamp')
        )
        
        # Format timestamps
        for item in history_data:
            item['timestamp'] = item['timestamp'].isoformat()
            item['user'] = item.pop('user_message')
            item['bot'] = item.pop('bot_response')
            
        return Response({
            'session_id': str(session.session_id),
            'language': session.language,
            'history': history_data
        })




class DocumentViewSet(viewsets.ModelViewSet):
    """
    Document management - PDF, Word, URL yuklash va qayta ishlash.
    Frontend'dan hujjat yuklash uchun API endpoint.
    """
    queryset = Document.objects.all().order_by('-created_at')
    serializer_class = DocumentSerializer
    permission_classes = [AllowAny]  # Production'da IsAuthenticated qilish kerak
    
    def get_queryset(self):
        """Filter by status if needed."""
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset
    
    def perform_create(self, serializer):
        """Create document and auto-process if enabled."""
        document = serializer.save()
        
        # Auto-processing - background task orqali
        # TODO: Celery task qo'shish kerak
        try:
            # Import here to avoid circular import
            from document_processor import DocumentRAGIntegration
            
            # Process immediately (sync) - Production'da Celery task qilish kerak
            integration = DocumentRAGIntegration()
            result = integration.process_and_store(document)
            
            logger.info(f"Document {document.id} processed: {result}")
        except Exception as e:
            logger.error(f"Auto-processing error for document {document.id}: {e}", exc_info=True)
            document.status = 'failed'
            document.error_message = str(e)[:500]
            document.save()
    
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Manually trigger document processing."""
        document = self.get_object()
        
        if document.status == 'processing':
            return Response(
                {'error': 'Document is already being processed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from document_processor import DocumentRAGIntegration
            
            # Update status
            document.status = 'processing'
            document.save()
            
            # Process document
            integration = DocumentRAGIntegration()
            result = integration.process_and_store(document)
            
            # Refresh from DB
            document.refresh_from_db()
            
            serializer = self.get_serializer(document)
            return Response({
                'success': True,
                'message': 'Document processed successfully',
                'document': serializer.data,
                'result': result
            })
        except Exception as e:
            logger.error(f"Processing error: {e}", exc_info=True)
            document.status = 'failed'
            document.error_message = str(e)[:500]
            document.save()
            
            return Response(
                {'error': f'Processing failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get document statistics."""
        from django.db.models import Count, Q
        
        stats = Document.objects.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='pending')),
            processing=Count('id', filter=Q(status='processing')),
            completed=Count('id', filter=Q(status='completed')),
            failed=Count('id', filter=Q(status='failed')),
        )
        
        return Response(stats)
