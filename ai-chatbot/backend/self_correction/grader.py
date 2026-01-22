"""
Relevance Grader - Node 2 in LangGraph workflow

Checks if retrieved context is relevant to the user's question.
If not relevant, suggests query refinement.
"""

import re
from typing import Dict, List


class RelevanceGrader:
    """Kontekstning savolga mosligini baholaydi."""
    
    def __init__(self):
        # Intent-specific keywords for better grading
        self.intent_keywords = {
            'financial': ['kontrakt', 'narx', 'to\'lov', 'price', 'fee', 'tuition', 'summa'],
            'dormitory': ['yotoqxona', 'turar', 'joy', 'dormitory', 'hostel', 'общежитие'],
            'academic': ['fakultet', 'kafedra', 'ta\'lim', 'o\'quv', 'faculty', 'department'],
            'admission': ['qabul', 'kirish', 'imtihon', 'admission', 'entrance', 'прием']
        }
    
    def grade(self, question: str, context: str, intent: str = None) -> Dict:
        """
        Kontekstni baholash.
        
        Args:
            question: Foydalanuvchi savoli
            context: Topilgan kontekst
            intent: Aniqlangan niyat (optional)
        
        Returns:
            {
                'is_relevant': bool,
                'confidence': float (0-1),
                'reason': str,
                'suggested_refinement': str  # agar mos bo'lmasa
            }
        """
        q_lower = question.lower()
        c_lower = context.lower()
        
        # 1. Check if context is empty or generic
        if not context or len(context.strip()) < 50:
            return {
                'is_relevant': False,
                'confidence': 0.0,
                'reason': "Kontekst bo'sh yoki juda qisqa",
                'suggested_refinement': self._suggest_refinement(question, intent)
            }
        
        # 2. Extract key entities from question
        question_entities = self._extract_entities(question)
        
        # 3. Check if any entity appears in context
        entity_matches = sum(1 for entity in question_entities if entity.lower() in c_lower)
        entity_coverage = entity_matches / max(len(question_entities), 1)
        
        # 4. Intent-specific keyword matching
        intent_score = 0.0
        if intent and intent in self.intent_keywords:
            keywords = self.intent_keywords[intent]
            keyword_matches = sum(1 for kw in keywords if kw in c_lower)
            intent_score = keyword_matches / len(keywords)
        
        # 5. Calculate overall confidence
        confidence = (entity_coverage * 0.6) + (intent_score * 0.4)
        
        # 6. Determine relevance
        is_relevant = confidence >= 0.3  # Lowered from 0.4 to 0.3 for better recall
        
        if not is_relevant:
            reason = f"Kontekstda savolning asosiy tushunchalari ({', '.join(question_entities[:3])}) topilmadi"
            refinement = self._suggest_refinement(question, intent)
        else:
            reason = f"Kontekst savolga mos ({confidence:.0%} ishonch)"
            refinement = None
        
        return {
            'is_relevant': is_relevant,
            'confidence': confidence,
            'reason': reason,
            'suggested_refinement': refinement
        }
    
    def _extract_entities(self, text: str) -> List[str]:
        """Savoldan asosiy tushunchalarni ajratib olish."""
        # Remove common words
        stop_words = {'haqida', 'nima', 'qanday', 'qancha', 'bormi', 'yo\'q', 'bor', 
                      'kerak', 'mumkin', 'о', 'в', 'на', 'и', 'the', 'is', 'are'}
        
        words = re.findall(r'\b\w+\b', text.lower())
        entities = [w for w in words if len(w) > 3 and w not in stop_words]
        
        return entities[:5]  # Top 5 entities
    
    def _suggest_refinement(self, question: str, intent: str = None) -> str:
        """Savolni qayta shakllantirish taklifi."""
        if intent == 'financial':
            return f"{question} (2025-2026 o'quv yili uchun)"
        elif intent == 'dormitory':
            return f"{question} (bakalavr talabalari uchun)"
        elif intent == 'academic':
            return f"{question} (fakultetlar ro'yxati)"
        else:
            # Generic refinement: add more specific terms
            return f"{question} (batafsil ma'lumot)"
