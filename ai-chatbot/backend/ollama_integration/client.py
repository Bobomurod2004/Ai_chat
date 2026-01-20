"""
Ollama Client for UzSWLU Chatbot
Smart response generation based on question type.
"""
import requests
import json
from django.conf import settings


class OllamaClient:
    """Professional Ollama client for UzSWLU AI Agent."""
    
    def __init__(self):
        self.url = getattr(settings, 'OLLAMA_URL', 'http://ollama:11434')
        self.model = getattr(settings, 'OLLAMA_MODEL', 'qwen2.5:3b')
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # Localized fallback messages
        self.FALLBACK_MESSAGES = {
            'uz': "Kechirasiz, ushbu ma'lumot bo'yicha bazada aniqlik yo'q. Batafsil ma'lumot uchun universitet dekanatiga murojaat qiling.",
            'ru': "К сожалению, в базе нет точной информации по этому вопросу. Для получения подробной информации, пожалуйста, обратитесь в деканат университета.",
            'en': "Sorry, there is no exact information in the database for this query. For more details, please contact the university dean's office."
        }
    
    def _get_fallback(self, language='uz'):
        return self.FALLBACK_MESSAGES.get(language, self.FALLBACK_MESSAGES['uz'])

    def _build_messages(self, question, context=None, history=None, language='uz'):
        """Builds clean messages for the /api/chat endpoint."""
        language_names = {'uz': 'O\'zbek', 'ru': 'Русский', 'en': 'English'}
        answer_language = language_names.get(language, 'O\'zbek')
        
        system_content = f"""### ROLE: UNIVERSITY INTELLIGENT AGENT
Sening isming: "UzSWLU AI Assistant"
Sening identifikatoring: O'zbekiston Davlat Jahon Tillari Universiteti (UzSWLU)ning rasmiy intellektual agentisan.

### KNOWLEDGE GROUNDING (RAG)
Senga quyidagi ma'lumotlar manbasi taqdim etiladi:
1. **Context Chunks:** Universitet hujjatlaridan olingan matn bo'laklari
2. **FAQ Data:** Oldindan tayyorlangan aniq savol-javoblar
3. **Dynamic Stats:** Telefon raqamlari, rektor ism-sharifi kabi tez o'zgaruvchan faktlar

### OPERATIONAL GUIDELINES:
1. **Accuracy (Aniqlik):** FAQAT taqdim etilgan kontekstga tayan. Agar kontekstda javob bo'lmasa, o'zingdan fakt to'qima ("Hallucination" taqiqlanadi).
   Javob topilmasa, FOYDALANUVCHI TILIDAGI standart xabarni qaytar: "{self._get_fallback(language)}"
2. **Multilingual Consistency:** Foydalanuvchi {answer_language} tilida so'ragan, shuning uchun javobni ham {answer_language} tilida ber.
3. **Hybrid Logic:**
   - Agar savol faktik bo'lsa (masalan: "IELTS ball necha?"), qisqa va aniq javob ber.
   - Agar savol tushuntirish talab qilsa, mantiqiy ketma-ketlikda javob ber.
4. **Source Attribution:** Har doim javobing oxirida foydalanilgan manbani ko'rsat.
   Misol: "7 ta fakultet mavjud. [Manba: FAQ #157]"

### REASONING STEPS (AI agent ichki mantiqi):
1. Foydalanuvchi so'rovini tushunish va tilni aniqlash
2. Kontekst ichidan eng dolzarb ma'lumotni saralash
3. Javobni shakllantirish va manbani ko'rsatish
4. "Assistant:", "Bot:" kabi prefikslarni ASLO ishlatmaslik

### RESPONSE FORMATTING (Professional UI uchun):
- **Sarlavhalar:** Muhim bo'limlar uchun ### ishlating
- **Ajratish:** Muhim ma'lumotlarni (sana, narx, bino raqami) **bold** qilib yozing
- **Ro'yxatlar:** Tushunish oson bo'lishi uchun bullet-points (* yoki -) ishlating

---
### KONTEKST:
{context if context else "Ma'lumot topilmadi."}

MUHIM: Javob oxirida [Manba: ...] yozishni ALBATTA unutma!"""

        messages = [{"role": "system", "content": system_content}]
        if history:
            messages.append({"role": "user", "content": f"Oldingi suhbatimiz: {history}"})
            messages.append({"role": "assistant", "content": "Tushunarli."})
        
        messages.append({"role": "user", "content": question})
        return messages
    
    def generate(self, question, context=None, history=None, language='uz'):
        """Generate response with Python-level fallback for reliability."""
        if not context or "Ma'lumot topilmadi" in context:
            return self._get_fallback(language)

        messages = self._build_messages(question, context, history, language)
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.1, "num_ctx": 4096}
        }
        try:
            response = self.session.post(f"{self.url}/api/chat", json=payload, timeout=120)
            response.raise_for_status()
            content = response.json().get('message', {}).get('content', '').strip()
            
            # Post-process to remove potential role labels (at start or in middle)
            for prefix in ["Assistant:", "Bot:", "Yordamchi:", "UzSWLU AI:"]:
                if prefix in content:
                    # Remove all occurrences
                    content = content.replace(prefix, "").strip()
                    # Clean up any double spaces or newlines
                    content = " ".join(content.split())
            
            return content
        except Exception as e:
            return f"Xato: {str(e)}"

    def generate_stream(self, question, context=None, history=None, language='uz'):
        """Stream response with Python-level fallback."""
        if not context or "Ma'lumot topilmadi" in context:
            yield self._get_fallback(language)
            return

        messages = self._build_messages(question, context, history, language)
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": 0.1, "num_ctx": 4096}
        }
        try:
            response = self.session.post(f"{self.url}/api/chat", json=payload, stream=True, timeout=120)
            response.raise_for_status()
            
            buffer = ""
            prefix_removed = False
            
            for line in response.iter_lines():
                if line:
                    data = json.loads(line.decode('utf-8'))
                    chunk = data.get('message', {}).get('content', '')
                    
                    if not prefix_removed:
                        buffer += chunk
                        # Check if buffer contains a prefix
                        for prefix in ["Assistant:", "Bot:", "Yordamchi:", "UzSWLU AI:"]:
                            if prefix in buffer:
                                buffer = buffer.replace(prefix, "", 1).strip()
                                prefix_removed = True
                                break
                        
                        # If buffer is long enough and no prefix found, start yielding
                        if len(buffer) > 15 or prefix_removed:
                            if buffer.strip():
                                yield buffer
                                buffer = ""
                            prefix_removed = True
                    else:
                        yield chunk
                    
                    if data.get('done'): break
        except Exception as e:
            yield f"Oqim xatosi: {str(e)}"

    def list_models(self):
        """List available models."""
        try:
            return self.session.get(f"{self.url}/api/tags").json()
        except:
            return {"models": []}

# Singleton instance
ollama_client = OllamaClient()


# Singleton instance
ollama_client = OllamaClient()
