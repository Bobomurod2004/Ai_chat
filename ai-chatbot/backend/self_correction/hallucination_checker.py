"""
Hallucination Checker - Node 4 in LangGraph workflow

Validates that the generated answer is grounded in the provided context.
Detects and flags hallucinated claims.
"""

import re
from typing import Dict, List


class HallucinationChecker:
    """Javobning kontekstga asoslanganligini tekshiradi."""
    
    def __init__(self):
        # Patterns that indicate potential hallucination
        self.hallucination_indicators = [
            r'ehtimol',  # "probably" - uncertainty
            r'taxminan',  # "approximately" when exact data should exist
            r'ko\'p hollarda',  # "in many cases" - vague
            r'odatda',  # "usually" - generalization
        ]
    
    def check(self, answer: str, context: str) -> Dict:
        """
        Javobni tekshirish.
        
        Args:
            answer: LLM tomonidan yaratilgan javob
            context: Berilgan kontekst
        
        Returns:
            {
                'is_grounded': bool,
                'hallucinated_claims': list,
                'confidence': float (0-1),
                'reason': str
            }
        """
        a_lower = answer.lower()
        c_lower = context.lower()
        
        hallucinated_claims = []
        
        # 1. Check for uncertainty indicators
        for pattern in self.hallucination_indicators:
            if re.search(pattern, a_lower):
                hallucinated_claims.append(f"Noaniq ifoda topildi: '{pattern}'")
        
        # 2. Extract factual claims from answer (numbers, dates, names)
        answer_facts = self._extract_facts(answer)
        
        # 3. Verify each fact against context
        ungrounded_facts = []
        for fact in answer_facts:
            if fact.lower() not in c_lower:
                ungrounded_facts.append(fact)
                hallucinated_claims.append(f"Kontekstda topilmagan fakt: '{fact}'")
        
        # 4. Check for contradictions
        contradictions = self._check_contradictions(answer, context)
        if contradictions:
            hallucinated_claims.extend(contradictions)
        
        # 5. Calculate grounding confidence
        if not answer_facts:
            # No factual claims to verify - likely a generic answer
            confidence = 0.7
        else:
            grounded_ratio = 1 - (len(ungrounded_facts) / len(answer_facts))
            confidence = grounded_ratio
        
        # 6. Determine if answer is grounded
        is_grounded = confidence >= 0.8 and len(hallucinated_claims) == 0
        
        if is_grounded:
            reason = "Javob kontekstga to'liq asoslangan"
        else:
            reason = f"{len(hallucinated_claims)} ta muammo topildi"
        
        return {
            'is_grounded': is_grounded,
            'hallucinated_claims': hallucinated_claims,
            'confidence': confidence,
            'reason': reason
        }
    
    def _extract_facts(self, text: str) -> List[str]:
        """Javobdan faktik ma'lumotlarni ajratib olish."""
        facts = []
        
        # Extract numbers (prices, dates, percentages)
        numbers = re.findall(r'\d[\d\s,\.]*\d+', text)
        facts.extend(numbers)
        
        # Extract capitalized entities (names, places)
        entities = re.findall(r'\b[A-ZА-ЯЎҚҒҲЎʼ][a-zа-яўқғҳўʼ]+(?:\s+[A-ZА-ЯЎҚҒҲЎʼ][a-zа-яўқғҳўʼ]+)*\b', text)
        facts.extend(entities)
        
        return facts[:10]  # Limit to top 10 facts
    
    def _check_contradictions(self, answer: str, context: str) -> List[str]:
        """Ziddiyatlarni aniqlash."""
        contradictions = []
        
        # Check for "yes" in answer but "no" in context
        if any(word in answer.lower() for word in ['ha', 'bor', 'mavjud', 'yes']):
            if any(word in context.lower() for word in ['yo\'q', 'mavjud emas', 'no', 'нет']):
                contradictions.append("Javobda 'ha' deyilgan, lekin kontekstda 'yo'q' mavjud")
        
        # Check for "no" in answer but "yes" in context
        if any(word in answer.lower() for word in ['yo\'q', 'mavjud emas', 'no']):
            if any(word in context.lower() for word in ['ha', 'bor', 'mavjud', 'yes', 'да']):
                contradictions.append("Javobda 'yo'q' deyilgan, lekin kontekstda 'ha' mavjud")
        
        return contradictions
