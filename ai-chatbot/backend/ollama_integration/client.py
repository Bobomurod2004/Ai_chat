"""
Ollama Client for UzSWLU Chatbot
Smart response generation based on question type.
"""
import requests
import json
from django.conf import settings


class OllamaClient:
    """Smart Ollama client with adaptive response length."""
    
    def __init__(self):
        self.url = getattr(settings, 'OLLAMA_URL', 'http://ollama:11434')
        # Primary model only - no fallbacks for speed
        self.model = getattr(settings, 'OLLAMA_MODEL', 'qwen2.5:1.5b')
        self.fallback_models = []  # No fallbacks for faster response
        
        # Connection pool for better performance
        import requests
        self.session = requests.Session()
        # Connection pool settings
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=1,  # Reduced retries
            pool_block=False
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
    
    def _detect_question_type(self, question, context=None):
        """
        Detect question type to determine response length.
        Returns: 'short', 'medium', 'long', or 'document'
        """
        q = question.lower().strip()
        
        # Check if we have document context
        has_document = context and '[DOCUMENT:' in context
        
        # SHORT answers (80 tokens) - simple factual questions
        short_patterns = [
            'when', 'what time', 'how much', 'how many',
            'where is', 'what is the address', 'phone', 'email',
            'who is the rector', 'what year', 'how old'
        ]
        
        # LONG answers (400 tokens) - detailed explanations
        long_patterns = [
            'tell me about', 'explain', 'describe', 'what are the',
            'list all', 'give me details', 'full information',
            'biography', 'history', 'background', 'partner',
            'program', 'faculty', 'information about'
        ]
        
        # DOCUMENT answers (600 tokens) - when answering from documents
        if has_document:
            return 'document'
        
        # Check patterns
        for pattern in long_patterns:
            if pattern in q:
                return 'long'
        
        for pattern in short_patterns:
            if pattern in q:
                return 'short'
        
        # Default to medium
        return 'medium'
    
    def _get_response_settings(self, question_type):
        """Get AI settings based on question type - OPTIMIZED for SPEED."""
        settings_map = {
            'short': {
                'num_predict': 250,
                'num_ctx': 4096,
                'temperature': 0.1,
                'top_p': 0.9,
                'repeat_penalty': 1.15,
                'instruction': 'Give a brief, direct answer in 1-3 sentences.'
            },
            'medium': {
                'num_predict': 450,
                'num_ctx': 4096,
                'temperature': 0.2,
                'top_p': 0.9,
                'repeat_penalty': 1.15,
                'instruction': 'Give a clear, detailed answer. Do NOT repeat yourself.'
            },
            'long': {
                'num_predict': 800,
                'num_ctx': 4096,
                'temperature': 0.3,
                'top_p': 0.9,
                'repeat_penalty': 1.15,
                'instruction': 'Give a comprehensive answer with all available details. Do NOT repeat yourself.'
            },
            'document': {
                'num_predict': 1000,
                'num_ctx': 4096,
                'temperature': 0.2,
                'top_p': 0.9,
                'repeat_penalty': 1.15,
                'instruction': (
                    'Answer using ONLY the provided DOCUMENT. '
                    'Be detailed but concise. Do NOT invent information.'
                )
            }
        }
        return settings_map.get(question_type, settings_map['medium'])
    
    def _build_prompt(self, question, context=None, instruction="", language='uz'):
        """Build multilingual prompt - hujjatlar qanday tilda bo'lishidan qat'iy nazar ishlaydi."""
        
        # Language detection for answer
        language_names = {
            'uz': 'O\'zbek',
            'ru': 'Русский', 
            'en': 'English'
        }
        answer_language = language_names.get(language, 'O\'zbek')
        
        # Check if we have document context
        has_document = context and '[DOCUMENT:' in context
        
        # MULTILINGUAL SYSTEM PROMPT - Production-ready
        # STRICT context-only instruction for accuracy
        system = f"""You are the professional UzSWLU AI Assistant.
        Your goal is to provide accurate and complete information based STICTLY on the CONTEXT provided below.

        STRICT RULES:
        1. IF AND ONLY IF the information is in the CONTEXT, answer the question.
        2. IF information is NOT in the CONTEXT, respond: "Kechirasiz, ushbu savol boʻyicha bazada maʼlumot topilmadi. Batafsil maʼlumot uchun universitetning rasmiy sayti (uzswlu.uz) ga murojaat qilishingiz mumkin."
        3. Do NOT use any external knowledge. Do NOT invent dates, names, or programs.
        4. Answer entirely in {answer_language}.
        5. Be helpful and professional."""
        
        if context and context.strip():
            # Reduced context limit for faster processing
            ctx_limit = 2500 if has_document else 1500
            ctx = context[:ctx_limit]
            return f"""{system}

CONTEXT:
{ctx}

USER QUESTION:
{question}

ANSWER:"""
        else:
            return f"""{system}

USER QUESTION:
{question}

ANSWER:"""
    
    def generate(self, question, context=None, language='uz'):
        """Generate smart response based on question type."""
        # Detect question type (now considers context)
        q_type = self._detect_question_type(question, context)
        settings = self._get_response_settings(q_type)
        
        prompt = self._build_prompt(question, context, settings['instruction'], language)
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": settings.get('temperature', 0.3),
                "top_p": settings.get('top_p', 0.9),
                "repeat_penalty": settings.get('repeat_penalty', 1.1),
                "num_ctx": settings['num_ctx'],
                "num_predict": settings['num_predict'],
            }
        }
        
        # Try main model first, then fallback models
        models_to_try = [self.model] + self.fallback_models
        
        for model_name in models_to_try:
            try:
                payload['model'] = model_name
                # Reduced timeout for faster failures - 60s total
                timeout_value = (10, 60)  # (connect timeout, read timeout)
                response = self.session.post(
                    f"{self.url}/api/generate",
                    json=payload,
                    timeout=timeout_value
                )
                response.raise_for_status()
                data = response.json()
                result = data.get('response', '').strip()
                if result:
                    if model_name != self.model:
                        print(f"✅ Fallback model ishlatildi: {model_name}")
                    return result
            except requests.exceptions.HTTPError as e:
                if e.response:
                    status_code = e.response.status_code
                    if status_code == 500:
                        # Model yuklash muammosi - keyingi model'ni sinab ko'rish
                        print(f"⚠️ Model {model_name} yuklashda xatolik (500 - xotira yetishmayapti), keyingi model'ni sinab ko'ramiz...")
                        continue
                    elif status_code == 404:
                        # Model topilmadi - keyingi model'ni sinab ko'rish
                        print(f"⚠️ Model {model_name} topilmadi (404), keyingi model'ni sinab ko'ramiz...")
                        continue
                    else:
                        print(f"⚠️ Model {model_name} HTTP {status_code}: {str(e)}, keyingi model'ni sinab ko'ramiz...")
                        continue
                else:
                    print(f"⚠️ Model {model_name} HTTP error: {str(e)}, keyingi model'ni sinab ko'ramiz...")
                    continue
            except requests.exceptions.Timeout as e:
                print(f"⚠️ Model {model_name} timeout, keyingi model'ni sinab ko'ramiz...")
                continue
            except requests.exceptions.ConnectionError as e:
                print(f"⚠️ Model {model_name} connection error, keyingi model'ni sinab ko'ramiz...")
                continue
            except Exception as e:
                print(f"⚠️ Model {model_name} xatolik: {e}, keyingi model'ni sinab ko'ramiz...")
                continue
        
        # Barcha model'lar muvaffaqiyatsiz bo'lsa
        return "Kechirasiz, AI model yuklashda muammo yuz berdi. Iltimos, bir necha soniyadan keyin qayta urinib ko'ring."
    
    def generate_stream(self, question, context=None, language='uz'):
        """Stream response for real-time output with smart length."""
        # Detect question type and get appropriate settings
        question_type = self._detect_question_type(question, context)
        settings = self._get_response_settings(question_type)

        prompt = self._build_prompt(question, context, settings['instruction'], language)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": settings.get('temperature', 0.3),
                "top_p": settings.get('top_p', 0.9),
                "repeat_penalty": settings.get('repeat_penalty', 1.1),
                "num_ctx": settings['num_ctx'],
                "num_predict": settings['num_predict'],
            }
        }

        # Try main model first, then fallback models
        models_to_try = [self.model] + self.fallback_models
        last_error = None

        for model_name in models_to_try:
            try:
                payload['model'] = model_name
                # Timeout'ni oshirish - streaming uchun ham
                timeout_value = (30, 300)  # (connect timeout, read timeout) - 30s connect, 300s read
                response = self.session.post(
                    f"{self.url}/api/generate",
                    json=payload,
                    stream=True,
                    timeout=timeout_value
                )
                response.raise_for_status()
                
                # If successful, yield chunks
                if model_name != self.model:
                    yield f"[Fallback model: {model_name}]\n"
                
                for line in response.iter_lines():
                    if line:
                        try:
                            # Decode bytes to string if needed
                            if isinstance(line, bytes):
                                line = line.decode('utf-8')
                            data = json.loads(line)
                            if 'response' in data:
                                yield data['response']
                            if data.get('done', False):
                                break
                        except (json.JSONDecodeError, UnicodeDecodeError) as e:
                            print(f"⚠️ JSON decode error: {e}")
                            continue
                return  # Success, exit function
            except requests.exceptions.HTTPError as e:
                if e.response:
                    status_code = e.response.status_code
                    if status_code == 500:
                        last_error = f"Model {model_name} yuklashda xatolik (500 - xotira yetishmayapti)"
                        print(f"⚠️ {last_error}, keyingi model'ni sinab ko'ramiz...")
                        continue
                    elif status_code == 404:
                        last_error = f"Model {model_name} topilmadi (404)"
                        print(f"⚠️ {last_error}, keyingi model'ni sinab ko'ramiz...")
                        continue
                    else:
                        last_error = f"Model {model_name} HTTP {status_code}: {str(e)}"
                        print(f"⚠️ {last_error}, keyingi model'ni sinab ko'ramiz...")
                        continue
                else:
                    last_error = str(e)
                    continue
            except Exception as e:
                last_error = str(e)
                print(f"⚠️ Model {model_name} xatolik: {e}, keyingi model'ni sinab ko'ramiz...")
                continue
        
        # Barcha model'lar muvaffaqiyatsiz bo'lsa
        yield f"Kechirasiz, AI model yuklashda muammo yuz berdi: {last_error}. Iltimos, bir necha soniyadan keyin qayta urinib ko'ring."
    
    def list_models(self):
        """List available models."""
        try:
            response = requests.get(f"{self.url}/api/tags", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception:
            return {"models": []}


# Singleton instance
ollama_client = OllamaClient()
