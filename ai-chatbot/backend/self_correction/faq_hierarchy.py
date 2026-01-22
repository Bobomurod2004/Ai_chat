"""
FAQ Hierarchy Enforcer

Ensures that FAQ answers always take precedence over Nizom/Charter documents
when there's a conflict between sources.
"""

from typing import Dict, List, Optional


class FAQHierarchyEnforcer:
    """FAQ > Nizom iyerarxiyasini ta'minlaydi."""
    
    def __init__(self):
        # Keywords that indicate conflicting information
        self.conflict_indicators = {
            'uz': ['yo\'q', 'mavjud emas', 'mumkin emas', 'ta\'qiqlangan'],
            'ru': ['нет', 'отсутствует', 'невозможно', 'запрещено'],
            'en': ['no', 'not available', 'impossible', 'prohibited']
        }
    
    def resolve_conflict(self, sources: List[Dict], question: str, lang_code: str = 'uz') -> Dict:
        """
        Manbalar o'rtasidagi ziddiyatni hal qilish.
        
        Args:
            sources: List of retrieved sources with metadata
            question: User's question
            lang_code: Language code
        
        Returns:
            {
                'primary_source': dict,  # FAQ if conflict exists, otherwise highest ranked
                'conflict_detected': bool,
                'resolution_reason': str
            }
        """
        # Separate FAQ and non-FAQ sources
        faq_sources = [s for s in sources if s.get('source_type') == 'faq']
        doc_sources = [s for s in sources if s.get('source_type') != 'faq']
        
        if not faq_sources or not doc_sources:
            # No conflict possible
            return {
                'primary_source': sources[0] if sources else None,
                'conflict_detected': False,
                'resolution_reason': "Faqat bitta manba turi mavjud"
            }
        
        # Check for contradictions
        conflict_detected = self._detect_contradiction(
            faq_sources[0]['text'],
            doc_sources[0]['text'],
            lang_code
        )
        
        if conflict_detected:
            # FAQ always wins
            return {
                'primary_source': faq_sources[0],
                'conflict_detected': True,
                'resolution_reason': "FAQ ma'lumoti Nizomdan ustun turadi (Hierarchy of Truth)"
            }
        else:
            # No conflict, use highest ranked source
            return {
                'primary_source': sources[0],
                'conflict_detected': False,
                'resolution_reason': "Manbalar o'rtasida ziddiyat yo'q"
            }
    
    def _detect_contradiction(self, faq_text: str, doc_text: str, lang_code: str) -> bool:
        """
        Ikki matn o'rtasida ziddiyat borligini aniqlash.
        
        Example:
            FAQ: "Yotoqxona mavjud"
            Nizom: "Magistratura talabalari uchun yotoqxona yo'q"
            -> Contradiction detected!
        """
        faq_lower = faq_text.lower()
        doc_lower = doc_text.lower()
        
        negative_indicators = self.conflict_indicators.get(lang_code, self.conflict_indicators['uz'])
        
        # Check if FAQ is positive and Doc is negative
        faq_is_positive = any(word in faq_lower for word in ['ha', 'bor', 'mavjud', 'yes', 'да'])
        doc_is_negative = any(word in doc_lower for word in negative_indicators)
        
        if faq_is_positive and doc_is_negative:
            return True
        
        # Check if FAQ is negative and Doc is positive
        faq_is_negative = any(word in faq_lower for word in negative_indicators)
        doc_is_positive = any(word in doc_lower for word in ['ha', 'bor', 'mavjud', 'yes', 'да'])
        
        if faq_is_negative and doc_is_positive:
            return True
        
        return False
    
    def prioritize_sources(self, sources: List[Dict]) -> List[Dict]:
        """
        Manbalarni iyerarxiya bo'yicha tartiblash.
        
        Priority order:
        1. FAQ (highest)
        2. Official Documents (Nizom, Charter)
        3. General Documents
        """
        faq_sources = [s for s in sources if s.get('source_type') == 'faq']
        official_docs = [s for s in sources if 'nizom' in s.get('title', '').lower() or 'charter' in s.get('title', '').lower()]
        other_docs = [s for s in sources if s not in faq_sources and s not in official_docs]
        
        # Combine in priority order
        return faq_sources + official_docs + other_docs
