"""
Ollama Client with Advanced Self-Correction Prompt (v5.0)
"""

import requests
import json
import logging

logger = logging.getLogger(__name__)


import os

class OllamaClient:
    def __init__(self, url=None, model=None):
        from django.conf import settings
        self.url = url or getattr(settings, 'OLLAMA_URL', 'http://ollama:11434')
        self.model = model or getattr(settings, 'OLLAMA_MODEL', 'qwen2.5:3b')
        self.session = requests.Session()
    
    def _get_fallback(self, language='uz'):
        fallbacks = {
            'uz': "Kechirasiz, ushbu ma'lumot bo'yicha bazada aniqlik yo'q. Iltimos, boshqa savol bering yoki admin bilan bog'laning.",
            'ru': "Извините, точной информации по этому вопросу в базе нет. Пожалуйста, задайте другой вопрос или свяжитесь с администратором.",
            'en': "Sorry, there is no precise information on this topic in the database. Please ask another question or contact the administrator."
        }
        return fallbacks.get(language, fallbacks['uz'])
    
    def _build_messages_v5(self, question, context=None, history=None, language='uz'):
        """
        Advanced v5.1 Prompt with Internal Monologue and Step-by-Step Reasoning (Qwen 3B Optimized)
        """
        system_content = f"""### ROLE: UZSWLU ACADEMIC AGENT (Qwen 3B Reasoning)
Sen O'zbekiston Davlat Jahon Tillari Universiteti uchun maxsus yaratilgan, o'z javoblarini tanqidiy tahlil qila oladigan "Self-Correction" agentisan.

### STEP 1: INTERNAL MONOLOGUE (Ichki tahlil)
Javob berishdan oldin, quyidagilarni o'ylash bosqichida (Step-by-step) tahlil qil:
1. **Raqamlar aniqligi:** KONTEKST ichidagi har bir raqamni (kontrakt, yil, foiz) savolga solishtir.
2. **Jadval tahlili:** Agar ma'lumot "Fakultet: ... | Kontrakt: ..." formatida bo'lsa, aynan so'ralgan yo'nalishni top.
3. **Mantiqiy tekshiruv:** "Men topgan ma'lumot [Hujjat: ...] breadcrumb'i bilan 100% mosmi?" deb o'zingga savol ber.

### STEP 2: RESPONSE FORMAT (Yakuniy javob)
Javobni quyidagi qat'iy formatda ber:

**[TO'G'RIDAN-TO'G'RI JAVOB]**
Savolga 100% aniqlikdagi, faktlarga asoslangan javob.

**[BATAFSIL MA'LUMOT]**
- Asoslovchi faktlar va [Hujjat: ...] breadcrumb'lari.
- Agar hisob-kitob bo'lsa, qadam-baqadam tushuntir.

**[MANBA]**
- Hujjat nomi va ishonchliligi.

### CONSTRAINTS (Cheklovlar):
- **No Hallucination:** Agar ma'lumot KONTEKSTda yo'q bo'lsa, "{self._get_fallback(language)}" deb ochiq ayt.
- **Breadcrumbs:** Har bir fakt boshiga [Hujjat: ...] belgisini albatta qo'y.
- **Qwen 3B focus:** Modellarda "Attention" cheklangan, shuning uchun faqat eng muhim raqamlarga e'tibor ber.

---
KONTEKST:
{context if context else "Ma'lumot topilmadi."}

---
SAVOL: {question}
"""
        
        messages = [{"role": "system", "content": system_content}]
        if history:
            messages.append({"role": "user", "content": f"Oldingi suhbatimiz: {history}"})
            messages.append({"role": "assistant", "content": "Tushunarli."})
        
        messages.append({"role": "user", "content": question})
        return messages
    
    def _build_messages(self, question, context=None, history=None, language='uz'):
        """Fallback to v5.0 prompt"""
        return self._build_messages_v5(question, context, history, language)
    
    def generate(self, question, context=None, history=None, language='uz'):
        """Generate response with Python-level fallback for reliability."""
        if not context or "Ma'lumot topilmadi" in context:
            return self._get_fallback(language)

        messages = self._build_messages(question, context, history, language)
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.1, "num_ctx": 4096, "num_gpu": 0}
        }
        try:
            response = self.session.post(f"{self.url}/api/chat", json=payload, timeout=120)
            response.raise_for_status()
            content = response.json().get('message', {}).get('content', '').strip()
            
            # Post-process to remove potential role labels
            for prefix in ["Assistant:", "Bot:", "Yordamchi:", "UzSWLU AI:"]:
                if prefix in content:
                    content = content.replace(prefix, "").strip()
            
            return content
        except Exception as e:
            logger.error(f"Ollama generation failed: {str(e)}")
            raise e

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
            "options": {"temperature": 0.1, "num_ctx": 4096, "num_gpu": 0}
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
                        for prefix in ["Assistant:", "Bot:", "Yordamchi:", "UzSWLU AI:"]:
                            if prefix in buffer:
                                buffer = buffer.replace(prefix, "", 1).strip()
                                prefix_removed = True
                                break
                        
                        if len(buffer) > 15 or prefix_removed:
                            if buffer.strip():
                                yield buffer
                                buffer = ""
                            prefix_removed = True
                    else:
                        yield chunk
                    
                    if data.get('done'): break
        except Exception as e:
            logger.error(f"Ollama streaming failed: {str(e)}")
            raise e

    def list_models(self):
        """List available models."""
        try:
            return self.session.get(f"{self.url}/api/tags").json()
        except:
            return {"models": []}

# Singleton instance
ollama_client = OllamaClient()
