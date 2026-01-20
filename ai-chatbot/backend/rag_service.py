"""
RAG Service for UzSWLU Chatbot
Retrieves context from both ChromaDB and PostgreSQL database.
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
import logging
import os
from django.conf import settings

# Setup logging
logger = logging.getLogger(__name__)
logger.info("✅ RAG Service loading...")


class RAGService:
    def __init__(self, persist_directory="/app/chroma_db"):
        self.persist_directory = persist_directory
        self.collection_name = "uzswlu_knowledge"
        
        # ChromaDB client - telemetry o'chirilgan (xatoliklarni oldini olish uchun)
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Telemetry xatoliklarini yashirish
        import logging
        logging.getLogger("chromadb").setLevel(logging.WARNING)
        logging.getLogger("posthog").setLevel(logging.CRITICAL)
        
        # PostHog capture() error monkeypatch (if library is causing issues)
        try:
            import posthog
            if hasattr(posthog, 'capture'):
                orig_capture = posthog.capture
                def silent_capture(*args, **kwargs):
                    return None
                posthog.capture = silent_capture
        except ImportError:
            pass
        
        # Embedding function - nomic-embed-text via Ollama API
        # Avval Ollama'da model mavjudligini tekshirish
        embedding_function = None
        try:
            # Try Ollama nomic-embed-text first (as per prompt requirements)
            from ollama_integration.embedding import OllamaEmbeddingFunction
            import requests
            
            # Test if model exists
            from django.conf import settings as django_settings
            test_url = getattr(django_settings, 'OLLAMA_URL', 'http://ollama:11434')
            try:
                test_response = requests.post(
                    f"{test_url}/api/embeddings",
                    json={"model": "nomic-embed-text", "prompt": "test"},
                    timeout=(5, 10)
                )
                if test_response.status_code == 404:
                    logger.warning("⚠️ nomic-embed-text model Ollama'da topilmadi. Fallback ishlatiladi.")
                    raise ValueError("Model not found")
                elif test_response.status_code != 200:
                    logger.warning(f"⚠️ nomic-embed-text test xatolik: {test_response.status_code}. Fallback ishlatiladi.")
                    raise ValueError("Model test failed")
            except (requests.exceptions.RequestException, ValueError) as test_error:
                logger.warning(f"⚠️ nomic-embed-text test xatolik: {test_error}. Fallback ishlatiladi.")
                raise
            
            # If test passed, use nomic-embed-text
            embedding_function = OllamaEmbeddingFunction(model_name="nomic-embed-text")
            logger.info("✅ Using Ollama nomic-embed-text embedding model")
            
        except Exception as e1:
            logger.warning(f"⚠️ Ollama nomic-embed-text yuklashda xatolik: {e1}")
            # Fallback to multilingual SentenceTransformer (matches existing collection dimension 384)
            try:
                from chromadb.utils import embedding_functions
                embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="paraphrase-multilingual-MiniLM-L12-v2"
                )
                logger.info("✅ Using Multilingual SentenceTransformer (fallback - matches existing collection)")
            except Exception as e2:
                logger.warning(f"⚠️ SentenceTransformer yuklashda xatolik: {e2}")
                try:
                    # Final fallback: Default embedding function
                    embedding_function = embedding_functions.DefaultEmbeddingFunction()
                    logger.info("✅ Using DefaultEmbeddingFunction (final fallback)")
                except Exception as e3:
                    logger.warning(f"⚠️ Default embedding function yuklashda xatolik: {e3}")
                    embedding_function = None
        
        self.embedding_fn = embedding_function
        
        try:
            self.collection = self.client.get_collection(
                self.collection_name,
                embedding_function=self.embedding_fn
            )
            count = self.collection.count()
            logger.info(f"✅ ChromaDB: {count} docs")
            
            # Avtomatik sync - agar FAQ'lar yo'q bo'lsa yoki kam bo'lsa
            if count == 0:
                logger.info("⚠️ ChromaDB bo'sh, FAQ'larni sync qilmoqda...")
                try:
                    self.sync_from_database()
                    logger.info("✅ FAQ'lar ChromaDB'ga sync qilindi")
                except Exception as e:
                    logger.warning(f"⚠️ Avtomatik sync xatolik: {e}")
        except Exception as e:
            logger.info(f"⚠️ Collection topilmadi yoki xatolik: {e}")
            # Collection yaratish - explicit embedding function bilan
            self.collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=embedding_function,
                metadata={"description": "UzSWLU knowledge base"}
            )
            logger.info("✅ Created ChromaDB collection")
            
            # Yangi collection yaratilganda avtomatik sync
            try:
                logger.info("⚠️ Yangi collection, FAQ'larni sync qilmoqda...")
                self.sync_from_database()
                logger.info("✅ FAQ'lar ChromaDB'ga sync qilindi")
            except Exception as e:
                logger.warning(f"⚠️ Avtomatik sync xatolik: {e}")
    
    def sync_from_database(self):
        """Sync FAQ translations from PostgreSQL to ChromaDB."""
        try:
            import django
            django.setup()
            from chatbot_app.models import FAQTranslation
            
            translations = FAQTranslation.objects.filter(faq__status='published')
            if not translations.exists():
                logger.info("No published FAQ translations to sync")
                return 0
            
            try:
                self.client.delete_collection(self.collection_name)
            except:
                pass
            
            # Use stored embedding function
            self.collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_fn
            )
            
            texts = []
            metadatas = []
            ids = []
            
            for trans in translations:
                # Combine question and answer for embedding
                search_text = f"Question: {trans.question}\nAnswer: {trans.answer}"
                texts.append(search_text)
                metadatas.append({
                    'faq_id': trans.faq_id,
                    'trans_id': trans.id,
                    'lang': trans.lang,
                    'category': trans.faq.category.name if trans.faq.category else 'General',
                    'type': 'faq',
                    'is_current': trans.faq.is_current,
                    'year': trans.faq.year
                })
                ids.append(f"faq_trans_{trans.id}")
            
            if texts:
                self.collection.add(documents=texts, metadatas=metadatas, ids=ids)
                logger.info(f"✅ Synced {len(texts)} FAQ translations to ChromaDB")
            
            return len(texts)
        except Exception as e:
            logger.error(f"❌ Sync error: {e}")
            return 0
    
    def search_database(self, query_text: str, lang_code: str = 'uz', limit: int = 5) -> List[Dict]:
        """Search FAQ translations from PostgreSQL using Full-Text Search on search_tsv."""
        try:
            from chatbot_app.models import FAQTranslation
            from django.contrib.postgres.search import SearchQuery, SearchRank, TrigramSimilarity
            from django.db.models import F, Value

            # Language to Postgres Search Config mapping
            lang_configs = {
                'uz': 'simple',
                'en': 'english',
                'ru': 'russian'
            }
            search_config = lang_configs.get(lang_code, 'simple')
            
            # Define search_query for FTS using language-specific config
            search_query = SearchQuery(query_text, config=search_config, search_type='plain')

            # Hybrid Search Ranking: 
            # - Exact/Stemmed Keyword Match (FTS)
            # - Fuzzy Keyword Match (Trigram Similarity)
            # - High weight to Question, slightly lower to Answer
            trans_results = FAQTranslation.objects.filter(
                lang=lang_code,
                faq__status='published'
            ).annotate(
                q_rank=SearchRank(F('question_tsv'), search_query),
                a_rank=SearchRank(F('answer_tsv'), search_query),
                q_sim=TrigramSimilarity('question', query_text),
                a_sim=TrigramSimilarity('answer', query_text),
                # Hybrid score calculation (Higher weighting for exact matches and trigrams in questions)
                rank=(F('q_rank') * 2.0 + F('a_rank') * 0.5 + F('q_sim') * 3.0 + F('a_sim') * 1.0)
            ).filter(rank__gte=0.1).order_by('-rank')[:limit]
            
            results = []
            for trans in trans_results:
                # POWER BOOST for exact keyword hits in the question
                # This overcomes the 'dilution' caused by common words like 'haqida' or 'ma'lumot'
                boost = 1.0
                core_keywords = {
                    'rektor': ['rektor', 'rector'],
                    'faq': ['fakultet', 'faculty'],
                    'adm': ['qabul', 'admission'],
                    'tel': ['aloqa', 'bog\'lanish', 'contact', 'telefon'],
                    'hist': ['tarix', 'history']
                }
                
                query_lower = query_text.lower()
                q_text_lower = trans.question.lower()
                
                for _, keywords in core_keywords.items():
                    if any(kw in query_lower for kw in keywords) and any(kw in q_text_lower for kw in keywords):
                        boost = 2.5 # Significant boost for matching core intent
                        break

                results.append({
                    'faq_id': trans.faq_id,
                    'question': trans.question,
                    'answer': trans.answer,
                    'category': trans.faq.category.name if trans.faq.category else 'General',
                    'relevance': min(1.0, float(trans.rank) * boost * (1.2 if trans.faq.is_current else 0.8)),
                    'source': 'db_fts',
                    'lang': trans.lang,
                    'is_current': trans.faq.is_current,
                    'year': trans.faq.year
                })
            
            # 2. Fallback search (if no results in target language, try others)
            if not results:
                other_trans = FAQTranslation.objects.filter(
                    faq__status='published'
                ).exclude(lang=lang_code).annotate(
                    q_rank=SearchRank(F('question_tsv'), search_query),
                    a_rank=SearchRank(F('answer_tsv'), search_query),
                    q_sim=TrigramSimilarity('question', query_text),
                    a_sim=TrigramSimilarity('answer', query_text),
                    rank=(F('q_rank') * 2.0 + F('a_rank') * 0.5 + F('q_sim') * 3.0 + F('a_sim') * 1.0)
                ).filter(rank__gte=0.1).order_by('-rank')[:limit]
                
                for trans in other_trans:
                    results.append({
                        'faq_id': trans.faq_id,
                        'question': trans.question,
                        'answer': trans.answer,
                        'category': trans.faq.category.name if trans.faq.category else 'General',
                        'relevance': float(trans.rank) * 0.8, # Penalty for different language
                        'source': 'db_fts_fallback',
                        'lang': trans.lang
                    })
            
            # 3. Last fallback: icontains search
            if not results:
                icontains_results = FAQTranslation.objects.filter(
                    faq__status='published',
                    question__icontains=query_text
                )[:limit]
                for trans in icontains_results:
                    results.append({
                        'faq_id': trans.faq_id,
                        'question': trans.question,
                        'answer': trans.answer,
                        'category': trans.faq.category.name if trans.faq.category else 'General',
                        'relevance': 0.1,
                        'source': 'db_icontains',
                        'lang': trans.lang
                    })
            
            return results
        except Exception as e:
            logger.error(f"Database search error: {e}")
            return []
    
    def search_chromadb(self, query: str, lang_code: str = 'uz', top_k: int = 5) -> List[Dict]:
        """Semantic search in ChromaDB with language awareness."""
        if self.collection.count() == 0:
            return []
        
        try:
            # Prefer matching language in metadata
            where_clause = {"lang": lang_code}
            
            n_results = min(top_k * 2, self.collection.count())
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_clause
            )
            
            # If no results for language, try all
            if not results['documents'][0]:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=n_results
                )
        except Exception as e:
            logger.error(f"❌ ChromaDB search error: {e}")
            return []
        
        documents = []
        if results and results.get('documents'):
            for i, doc in enumerate(results['documents'][0]):
                meta = results['metadatas'][0][i] if results.get('metadatas') else {}
                dist = results['distances'][0][i] if results.get('distances') else 1.0
                # Stricter similarity: cosine distance usually 0-2 (0 is same)
                similarity = max(0, 1 - dist)
                
                documents.append({
                    'text': doc,
                    'title': meta.get('title', 'Knowledge Base'),
                    'category': meta.get('category', 'General'),
                    'faq_id': meta.get('faq_id'),
                    'lang': meta.get('lang'),
                    'similarity': similarity * (1.1 if meta.get('is_current', True) else 0.9),
                    'is_current': meta.get('is_current', True),
                    'year': meta.get('year', 2024),
                    'source': meta.get('source', 'semantic')
                })
        
        return sorted(documents, key=lambda x: x['similarity'], reverse=True)[:top_k]

    def retrieve_with_sources(self, question: str, lang_code: str = 'uz', top_k: int = 5) -> Dict[str, Any]:
        """
        Prioritized retrieval with language support.
        1. Intent-Based Filtering & Category Matching
        2. Database FTS Search (with FAQ boosting)
        3. ChromaDB Semantic Search
        4. Rule-Based Reranking
        """
        # --- 1. Intent Detection ---
        intent_category = None
        q_lower = question.lower()
        
        # Simple keywords for intent matching
        intents = {
            'Talaba hayoti': ['yotoqxona', 'hostel', 'turar joy', 'student life'],
            'Qabul': ['qabul', 'admission', 'hujjat topshirish', 'imtihon'],
            'Kontrakt': ['kontrakt', 'to\'lov', 'payment', 'tuition'],
            'Magistratura': ['magistr', 'master', 'postgraduate']
        }
        
        for cat, keywords in intents.items():
            if any(kw in q_lower for kw in keywords):
                intent_category = cat
                break

        # --- 2. Database FTS Search ---
        db_results = self.search_database(question, lang_code=lang_code, limit=top_k)
        
        # High confidence check (Direct Match)
        if db_results and db_results[0]['relevance'] >= 0.5:
            best = db_results[0]
            # Verify category if intent found
            if not intent_category or best['category'] == intent_category:
                return {
                    'context': f"[{best['category']}]\n{best['answer']}",
                    'top_answer': best['answer'],
                    'top_question': best['question'],
                    'sources': [{
                        'title': best['question'],
                        'category': best['category'],
                        'source_type': 'faq',
                        'relevance': 100,
                        'faq_id': best['faq_id']
                    }],
                    'total_found': len(db_results)
                }
        
        # 2. ChromaDB Semantic Search
        semantic_results = self.search_chromadb(question, lang_code=lang_code, top_k=top_k)
        
        merged_results = []
        seen_faq_ids = set()
        
        # Add DB results (FAQ Boosting: multiply score by 1.25)
        for r in db_results:
            confidence = r['relevance'] * 1.25
            
            # Boost if category matches intent
            if intent_category and r['category'] == intent_category:
                confidence *= 1.2

            seen_faq_ids.add(r['faq_id'])
            merged_results.append({
                'text': r['answer'],
                'title': r['question'],
                'category': r['category'],
                'confidence': min(0.99, confidence),
                'source_type': 'faq',
                'faq_id': r['faq_id']
            })
            
        # Add Semantic results if not seen
        for r in semantic_results:
            if r['faq_id'] and r['faq_id'] in seen_faq_ids:
                continue
            
            confidence = r['similarity']
            # Boost if category matches intent
            if intent_category and r['category'] == intent_category:
                confidence *= 1.2
            # Penalize if intent category exists but result is NOT in it (Filtering)
            elif intent_category and r['category'] != intent_category:
                confidence *= 0.5

            merged_results.append({
                'text': r['text'],
                'title': r['title'],
                'category': r['category'],
                'confidence': min(0.99, confidence),
                'source_type': 'semantic',
                'faq_id': r['faq_id']
            })
            
        merged_results.sort(key=lambda x: x['confidence'], reverse=True)
        
        # --- 4. Rule-Based Reranking ---
        # If we have a high-confidence FAQ (>0.75), prioritize it and limit other docs
        has_high_conf_faq = any(r['source_type'] == 'faq' and r['confidence'] > 0.75 for r in merged_results)
        
        if has_high_conf_faq:
            top_results = [r for r in merged_results if r['confidence'] >= 0.15]
        else:
            top_results = [r for r in merged_results if r['confidence'] >= 0.15]

        top_results = top_results[:top_k]
        
        context_blocks = []
        for r in top_results:
            source_tag = f"FAQ #{r['faq_id']}" if r['source_type'] == 'faq' else f"Hujjat: {r['title']}"
            context_blocks.append(f"MANBA: {source_tag}\nMATN: {r['text']}")
        
        context = "\n---\n".join(context_blocks)
        sources = [{
            'title': r['title'],
            'category': r['category'],
            'source_type': r['source_type'],
            'relevance': round(r['confidence'] * 100),
            'faq_id': r.get('faq_id')
        } for r in top_results]
        
        return {
            'context': context,
            'top_confidence': top_results[0]['confidence'] if top_results else 0,
            'sources': sources,
            'total_found': len(merged_results)
        }


_rag_service = None

def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service

def sync_faqs_to_chromadb():
    service = get_rag_service()
    return service.sync_from_database()
