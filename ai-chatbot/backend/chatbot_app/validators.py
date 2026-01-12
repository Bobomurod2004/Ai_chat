# flake8: noqa
"""
Response Validator - Hallucination Detection va Quality Control
AI javoblarini tekshirish va xavfsiz javoblar yaratish.
"""
import re
from typing import Dict, List, Any, Optional, Tuple
from difflib import SequenceMatcher


class ResponseValidator:
    """
    AI javoblarini validatsiya qilish:
    1. Grounding check - context da asoslangan javobmi?
    2. Relevance check - savol bilan mos keladimi?
    3. Factual check - raqamlar va faktlar to'g'rimi?
    4. Completeness check - javob to'liqmi?
    5. Hallucination risk - soxta ma'lumot bormi?
    """
    
    def __init__(self):
        # Unsafe response patterns
        self.hallucination_patterns = [
            r"bilmayman.*lekin",  # "Bilmayman, lekin..." - taxmin
            r"menimcha",  # Opinion without source
            r"o'ylaymanki",
            r"ehtimol.*bo'lishi",  # Uncertainty
            r"aniq bilmayman",
        ]
        
        # Good response patterns (grounded in context)
        self.grounded_patterns = [
            r"kontekstga ko'ra",
            r"ma'lumotlarga asosan",
            r"hujjatda",
            r"rasmiy ma'lumot",
        ]
    
    def validate_response(
        self, 
        query: str, 
        response: str, 
        context: str, 
        sources: List[Dict]
    ) -> Dict[str, Any]:
        """
        Comprehensive response validation.
        
        Args:
            query: Foydalanuvchi savoli
            response: AI javobi
            context: RAG context
            sources: Manba ma'lumotlari
        
        Returns:
            {
                'is_safe': bool,
                'safe_response': str,
                'checks': dict,
                'safety_score': float,
                'warning': str (optional),
                'suggestions': list
            }
        """
        checks = {
            'grounded_in_context': self.check_grounding(response, context),
            'relevance': self.check_relevance(query, response),
            'confidence': self.calculate_confidence(sources),
            'completeness': self.check_completeness(response),
            'factual_consistency': self.check_facts(response, context),
            'hallucination_risk': self.check_hallucination_risk(response, context)
        }
        
        # Overall safety score
        # Hallucination risk is inverted (lower = better)
        weighted_scores = [
            checks['grounded_in_context'] * 0.3,
            checks['relevance'] * 0.2,
            checks['confidence'] * 0.2,
            checks['completeness'] * 0.1,
            checks['factual_consistency'] * 0.1,
            (1 - checks['hallucination_risk']) * 0.1  # Inverted
        ]
        safety_score = sum(weighted_scores)
        
        # Determine if safe
        # O'zbek tili uchun threshold'lar juda past - 
        # faqat juda xavfli javoblarni bloklash
        is_safe = (
            checks['grounded_in_context'] >= 0.05 and  # Minimal grounding talab
            checks['hallucination_risk'] <= 0.85 and   # Faqat juda xavfli bloklash
            safety_score >= 0.15                        # Juda past threshold
        )
        
        # Generate result
        result = {
            'is_safe': is_safe,
            'checks': checks,
            'safety_score': round(safety_score, 3),
            'suggestions': []
        }
        
        if is_safe:
            result['safe_response'] = response
        else:
            result['safe_response'] = self.generate_fallback_response(
                query, sources, checks
            )
            result['warning'] = self._generate_warning(checks)
            result['original_response'] = response
            result['suggestions'] = self._generate_suggestions(checks)
        
        return result
    
    def check_grounding(self, response: str, context: str) -> float:
        """
        Context da asoslangan javobmi?
        Returns: 0.0 to 1.0 (1.0 = fully grounded)
        """
        if not context or not response:
            return 0.0
        
        response_lower = response.lower()
        context_lower = context.lower()
        
        # Method 1: Word overlap (Jaccard-like)
        response_words = set(self._tokenize(response_lower))
        context_words = set(self._tokenize(context_lower))
        
        if not response_words:
            return 0.0
        
        # Content words only (exclude stop words)
        stop_words = {
            'va', 'yoki', 'bu', 'u', 'men', 'siz', 'bilan', 'uchun',
            'dan', 'ga', 'da', 'ni', 'ning', 'ham', 'bo\'lsa', 'esa',
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be',
            'qanday', 'nima', 'kim', 'qayerda', 'qachon'
        }
        
        response_content = response_words - stop_words
        context_content = context_words - stop_words
        
        if not response_content:
            return 0.5  # Only stop words - neutral
        
        overlap = response_content.intersection(context_content)
        grounding_score = len(overlap) / len(response_content)
        
        # Method 2: Sequence matching for key phrases
        matcher = SequenceMatcher(None, response_lower, context_lower)
        sequence_score = matcher.ratio()
        
        # Combined score
        final_score = (grounding_score * 0.7) + (sequence_score * 0.3)
        
        return min(1.0, final_score)
    
    def check_relevance(self, query: str, response: str) -> float:
        """
        Savol bilan javob mos keladimi?
        Returns: 0.0 to 1.0
        """
        if not query or not response:
            return 0.0
        
        query_lower = query.lower()
        response_lower = response.lower()
        
        # Extract query keywords
        query_words = set(self._tokenize(query_lower))
        response_words = set(self._tokenize(response_lower))
        
        # Question type analysis
        question_types = {
            'who': ['kim', 'who', 'kimlar'],
            'what': ['nima', 'nimalar', 'what', 'qanaqa'],
            'when': ['qachon', 'when', 'nechanchi'],
            'where': ['qayerda', 'where', 'qaerda'],
            'how': ['qanday', 'how', 'qay tarzda'],
            'how_much': ['qancha', 'necha', 'how much', 'narxi']
        }
        
        # Check if response addresses the question type
        question_type = None
        for q_type, keywords in question_types.items():
            if any(kw in query_lower for kw in keywords):
                question_type = q_type
                break
        
        # Basic word overlap
        if not query_words:
            return 0.5
        
        overlap = query_words.intersection(response_words)
        base_relevance = len(overlap) / len(query_words)
        
        # Bonus for addressing question type
        type_bonus = 0
        if question_type == 'who' and any(w in response_lower for w in ['ism', 'professor', 'direktor', 'rektor']):
            type_bonus = 0.2
        elif question_type == 'when' and re.search(r'\d{4}|\d{1,2}[/-]\d{1,2}', response):
            type_bonus = 0.2
        elif question_type == 'how_much' and re.search(r'\d+\s*(so\'m|sum|dollar|\$|mln|ming)', response_lower):
            type_bonus = 0.2
        elif question_type == 'where' and any(w in response_lower for w in ['manzil', 'joylashgan', 'ko\'cha']):
            type_bonus = 0.2
        
        return min(1.0, base_relevance + type_bonus)
    
    def calculate_confidence(self, sources: List[Dict]) -> float:
        """Source confidence average"""
        if not sources:
            return 0.0
        
        confidences = [s.get('confidence', 0) for s in sources]
        return sum(confidences) / len(confidences)
    
    def check_completeness(self, response: str) -> float:
        """Javob to'liqmi?"""
        if not response:
            return 0.0
        
        # Length check
        if len(response) < 20:
            return 0.3
        elif len(response) < 50:
            return 0.5
        
        # Has proper sentence structure
        has_punctuation = bool(re.search(r'[.!?]', response))
        
        # Doesn't end abruptly
        ends_properly = response.strip()[-1] in '.!?)'
        
        # Has content (not just filler)
        filler_ratio = len(re.findall(r'\b(va|yoki|ham|esa|bu)\b', response.lower())) / max(len(response.split()), 1)
        
        score = 0.5
        if has_punctuation:
            score += 0.2
        if ends_properly:
            score += 0.2
        if filler_ratio < 0.3:
            score += 0.1
        
        return min(1.0, score)
    
    def check_facts(self, response: str, context: str) -> float:
        """
        Faktlar context da bormi?
        Raqamlar, sanalar, ismlarni tekshirish.
        """
        if not context:
            return 0.5  # No context to check against
        
        context_str = str(context).lower()
        response_str = response.lower()
        
        # Extract facts from response
        # Numbers
        response_numbers = set(re.findall(r'\b\d+\b', response_str))
        # Years (4 digits)
        response_years = set(re.findall(r'\b(19|20)\d{2}\b', response_str))
        # Percentages
        response_percentages = set(re.findall(r'\d+\s*%', response_str))
        
        all_facts = response_numbers | response_years | response_percentages
        
        if not all_facts:
            return 0.8  # No specific facts to check
        
        # Check how many facts are in context
        verified_facts = 0
        for fact in all_facts:
            if fact in context_str:
                verified_facts += 1
        
        return verified_facts / len(all_facts) if all_facts else 0.8
    
    def check_hallucination_risk(self, response: str, context: str) -> float:
        """
        Soxta ma'lumot xavfi.
        Returns: 0.0 to 1.0 (1.0 = high risk)
        """
        if not response:
            return 0.0
        
        response_lower = response.lower()
        risk_score = 0.0
        
        # Check for uncertainty patterns
        for pattern in self.hallucination_patterns:
            if re.search(pattern, response_lower):
                risk_score += 0.15
        
        # Check for grounded patterns (reduces risk)
        for pattern in self.grounded_patterns:
            if re.search(pattern, response_lower):
                risk_score -= 0.1
        
        # Long response without context = higher risk
        if len(response) > 500 and (not context or len(context) < 100):
            risk_score += 0.2
        
        # Contains specific claims not in context
        if context:
            context_lower = context.lower()
            
            # Specific names
            names_in_response = re.findall(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', response)
            for name in names_in_response:
                if name.lower() not in context_lower:
                    risk_score += 0.1
            
            # Specific numbers
            numbers_in_response = re.findall(r'\b\d{4,}\b', response)
            for num in numbers_in_response:
                if num not in context_lower:
                    risk_score += 0.05
        
        return min(1.0, max(0.0, risk_score))
    
    def generate_fallback_response(
        self, 
        query: str, 
        sources: List[Dict],
        checks: Dict[str, float]
    ) -> str:
        """Xavfsiz fallback javob yaratish"""
        
        base_response = "Kechirasiz, bu savolga aniq javob topilmadi."
        
        # If we have good sources, point to them
        if sources and len(sources) > 0:
            top_source = sources[0]
            if top_source.get('confidence', 0) > 0.4:
                base_response = (
                    f"Bu mavzu bo'yicha quyidagi ma'lumot topildi:\n\n"
                    f"📚 Manba: {top_source.get('title', 'Hujjat')}\n"
                )
                
                # Add snippet from source
                content = top_source.get('content', '')[:300]
                if content:
                    base_response += f"\n{content}..."
        
        # Add contact info for uncertain cases
        if checks.get('confidence', 0) < 0.5:
            base_response += (
                "\n\n💡 Aniqroq ma'lumot olish uchun "
                "UzSWLU rasmiy veb-saytiga murojaat qiling: uzswlu.uz"
            )
        
        return base_response
    
    def _generate_warning(self, checks: Dict[str, float]) -> str:
        """Warning message yaratish"""
        warnings = []
        
        if checks['grounded_in_context'] < 0.4:
            warnings.append("Context da yetarli asos topilmadi")
        
        if checks['hallucination_risk'] > 0.5:
            warnings.append("Soxta ma'lumot xavfi yuqori")
        
        if checks['confidence'] < 0.4:
            warnings.append("Manba ishonchliligi past")
        
        return "; ".join(warnings) if warnings else "Umumiy sifat past"
    
    def _generate_suggestions(self, checks: Dict[str, float]) -> List[str]:
        """Yaxshilash bo'yicha takliflar"""
        suggestions = []
        
        if checks['grounded_in_context'] < 0.5:
            suggestions.append("Knowledge base ni yangilash kerak")
        
        if checks['confidence'] < 0.4:
            suggestions.append("Ko'proq manba qo'shish tavsiya etiladi")
        
        if checks['relevance'] < 0.5:
            suggestions.append("Savol qayta formulirovka qilish kerak")
        
        return suggestions
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        text = re.sub(r'[^\w\s]', ' ', text)
        return [w for w in text.split() if len(w) > 2]


# Singleton instance
_validator = None

def get_validator() -> ResponseValidator:
    """Get or create validator singleton"""
    global _validator
    if _validator is None:
        _validator = ResponseValidator()
    return _validator
