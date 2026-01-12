"""
Translator Service for UzSWLU Chatbot
Translates English responses to Uzbek using Ollama
"""

import re
from typing import Optional
import ollama


class UzbekTranslator:
    """
    Translates English text to Uzbek using Ollama.
    Includes caching and common phrase dictionary for better performance.
    """
    
    # Common phrases dictionary for faster and more accurate translation
    COMMON_PHRASES = {
        # University terms
        "UzSWLU": "UzSWLU",
        "Uzbekistan State World Languages University": "O'zbekiston Davlat Jahon Tillari Universiteti",
        "University": "Universitet",
        "Faculty": "Fakultet",
        "Department": "Kafedra",
        "Dean": "Dekan",
        "Rector": "Rektor",
        "Professor": "Professor",
        "Student": "Talaba",
        "Students": "Talabalar",
        "Teacher": "O'qituvchi",
        "Teachers": "O'qituvchilar",
        
        # Programs
        "Bachelor": "Bakalavr",
        "Bachelor's degree": "Bakalavr darajasi",
        "Master": "Magistr",
        "Master's degree": "Magistratura",
        "PhD": "PhD",
        "Doctoral": "Doktorantura",
        
        # Admission
        "Admission": "Qabul",
        "Admission Process": "Qabul jarayoni",
        "Tuition": "Kontrakt to'lovi",
        "Scholarship": "Stipendiya",
        "Grant": "Grant",
        "Exam": "Imtihon",
        "State Testing Center": "Davlat test markazi",
        
        # Languages
        "English": "Ingliz tili",
        "German": "Nemis tili",
        "French": "Fransuz tili",
        "Russian": "Rus tili",
        "Chinese": "Xitoy tili",
        "Arabic": "Arab tili",
        "Japanese": "Yapon tili",
        "Korean": "Koreys tili",
        "Spanish": "Ispan tili",
        "Italian": "Italyan tili",
        "Turkish": "Turk tili",
        
        # Time periods
        "years": "yil",
        "year": "yil",
        "months": "oy",
        "month": "oy",
        "weeks": "hafta",
        "week": "hafta",
        "days": "kun",
        "day": "kun",
        "semester": "semestr",
        "semesters": "semestr",
        
        # Months
        "January": "Yanvar",
        "February": "Fevral",
        "March": "Mart",
        "April": "Aprel",
        "May": "May",
        "June": "Iyun",
        "July": "Iyul",
        "August": "Avgust",
        "September": "Sentyabr",
        "October": "Oktyabr",
        "November": "Noyabr",
        "December": "Dekabr",
        
        # Contact
        "Address": "Manzil",
        "Phone": "Telefon",
        "Email": "Elektron pochta",
        "Website": "Veb-sayt",
        "Official website": "Rasmiy sayt",
        
        # Common responses
        "Yes": "Ha",
        "No": "Yo'q",
        "Available": "Mavjud",
        "Not available": "Mavjud emas",
        "Required": "Talab qilinadi",
        "Optional": "Ixtiyoriy",
        
        # Common sentences/phrases
        "begins in": "boshlanadi",
        "starts in": "boshlanadi",
        "is in": "bo'ladi",
        "The admission": "Qabul",
        "takes place": "o'tkaziladi",
        "is held": "o'tkaziladi",
        "per year": "yiliga",
        "annually": "har yili",
        "please visit": "murojaat qiling",
        "for more info": "qo'shimcha ma'lumot uchun",
        "for more information": "qo'shimcha ma'lumot uchun",
        "I don't have": "Men haqida ma'lumotim yo'q",
        "information about": "haqida ma'lumot",
        
        # Education
        "Education": "Ta'lim",
        "Study": "O'qish",
        "Learning": "O'rganish",
        "Teaching": "O'qitish",
        "Diploma": "Diplom",
        "Certificate": "Sertifikat",
        "Degree": "Daraja",
        
        # Facilities
        "Library": "Kutubxona",
        "Dormitory": "Yotoqxona",
        "Sports hall": "Sport zali",
        "Fitness center": "Fitnes markazi",
        
        # Career
        "Career": "Karera",
        "Job": "Ish",
        "Employment": "Ish bilan bandlik",
        "Translator": "Tarjimon",
        "Interpreter": "Tarjimon",
        "Translation": "Tarjima",
        
        # Other
        "International": "Xalqaro",
        "Program": "Dastur",
        "Programs": "Dasturlar",
        "Exchange": "Almashinuv",
        "Partnership": "Hamkorlik",
        "Information": "Ma'lumot",
        "Contact": "Aloqa",
        "Location": "Joylashuv",
        "Metro": "Metro",
        "Tashkent": "Toshkent",
        "Uzbekistan": "O'zbekiston",
        
        # Additional common words
        "The": "",
        "is": "",
        "are": "",
        "period": "davri",
        "between": "oralig'ida",
        "about": "haqida",
        "approximately": "taxminan",
        "around": "atrofida",
    }
    
    # Amount translations
    AMOUNT_PATTERNS = {
        r'(\d+)-(\d+) million soums': r"\1-\2 million so'm",
        r'(\d+) million soums': r"\1 million so'm",
        r'(\d+)-(\d+) thousand soums': r"\1-\2 ming so'm",
        r'(\d+) thousand soums': r"\1 ming so'm",
    }
    
    def __init__(self, model: str = "mistral:latest"):
        """Initialize translator with specified model."""
        self.model = model
        self._cache = {}
    
    def _apply_dictionary(self, text: str) -> str:
        """Apply common phrase dictionary to text."""
        result = text
        
        # Apply amount patterns first
        for pattern, replacement in self.AMOUNT_PATTERNS.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        # Apply common phrases (case-insensitive but preserve original where possible)
        for eng, uzb in self.COMMON_PHRASES.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(eng) + r'\b'
            result = re.sub(pattern, uzb, result, flags=re.IGNORECASE)
        
        return result
    
    def translate_with_ollama(self, text: str) -> str:
        """Translate text using Ollama model."""
        # Check cache first
        cache_key = text.strip().lower()
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # First apply dictionary for common terms
        pre_translated = self._apply_dictionary(text)
        
        # If text is mostly translated by dictionary, return it
        english_words = re.findall(r'[a-zA-Z]{4,}', pre_translated)
        if len(english_words) < 3:
            self._cache[cache_key] = pre_translated
            return pre_translated
        
        try:
            prompt = f"""Translate the following English text to Uzbek (Latin script).
Keep names, numbers, and technical terms unchanged.
Translate naturally and fluently.

English: {pre_translated}

Uzbek translation:"""
            
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                options={
                    "temperature": 0.3,
                    "num_predict": 300,
                    "top_p": 0.9,
                }
            )
            
            translated = response['response'].strip()
            
            # Clean up any extra text
            if "English:" in translated:
                translated = translated.split("English:")[0].strip()
            if "Uzbek:" in translated:
                translated = translated.split("Uzbek:")[-1].strip()
            
            # Cache the result
            self._cache[cache_key] = translated
            
            return translated
            
        except Exception as e:
            print(f"Translation error: {e}")
            # Return dictionary-translated version on error
            return pre_translated
    
    def translate(self, text: str, use_ollama: bool = True) -> str:
        """
        Main translation method.
        
        Args:
            text: English text to translate
            use_ollama: If True, use Ollama for full translation; if False, use only dictionary
            
        Returns:
            Uzbek translation
        """
        if not text or not text.strip():
            return text
        
        # For short texts or texts with mostly known terms, use dictionary only
        if use_ollama:
            return self.translate_with_ollama(text)
        else:
            return self._apply_dictionary(text)
    
    def translate_streaming(self, text: str):
        """
        Translate with streaming output.
        Yields chunks of translated text.
        """
        pre_translated = self._apply_dictionary(text)
        
        # Check if mostly translated
        english_words = re.findall(r'[a-zA-Z]{4,}', pre_translated)
        if len(english_words) < 3:
            yield pre_translated
            return
        
        try:
            prompt = f"""Translate the following English text to Uzbek (Latin script).
Keep names, numbers, and technical terms unchanged.
Translate naturally and fluently.

English: {pre_translated}

Uzbek translation:"""
            
            stream = ollama.generate(
                model=self.model,
                prompt=prompt,
                stream=True,
                options={
                    "temperature": 0.3,
                    "num_predict": 300,
                    "top_p": 0.9,
                }
            )
            
            for chunk in stream:
                if chunk.get('response'):
                    yield chunk['response']
                    
        except Exception as e:
            print(f"Streaming translation error: {e}")
            yield pre_translated


# Singleton instance
_translator = None

def get_translator(model: str = "mistral:latest") -> UzbekTranslator:
    """Get or create translator instance."""
    global _translator
    if _translator is None:
        _translator = UzbekTranslator(model=model)
    return _translator


def translate_to_uzbek(text: str, use_ollama: bool = True) -> str:
    """
    Convenience function to translate English text to Uzbek.
    
    Args:
        text: English text to translate
        use_ollama: Whether to use Ollama for translation
        
    Returns:
        Uzbek translation
    """
    translator = get_translator()
    return translator.translate(text, use_ollama=use_ollama)


# Test function
if __name__ == "__main__":
    translator = UzbekTranslator()
    
    test_texts = [
        "The admission process starts in June.",
        "UzSWLU has 23,168 students.",
        "Bachelor's degree takes 4 years to complete.",
        "The tuition fee is 12-15 million soums per year.",
        "The university is located in Tashkent near Oybek metro station.",
    ]
    
    print("Testing translator:")
    print("-" * 50)
    for text in test_texts:
        result = translator.translate(text, use_ollama=False)
        print(f"EN: {text}")
        print(f"UZ: {result}")
        print("-" * 50)
