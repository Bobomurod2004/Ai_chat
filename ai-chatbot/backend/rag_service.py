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
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )
            count = self.collection.count()
            logger.info(f"✅ ChromaDB: {count} docs (Space: Cosine)")
            
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
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=embedding_function,
                metadata={"hnsw:space": "cosine", "description": "UzSWLU knowledge base"}
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
                
                # Use nomic prefix for indexing
                if hasattr(self.embedding_fn, '__call__'):
                    # ChromaDB handles the embedding function call internals, 
                    # but we might need to manually pass prefix if our class supports it
                    pass

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
                # v6.1: Manual embedding for nomic prefix
                if hasattr(self.embedding_fn, 'model_name') and "nomic" in self.embedding_fn.model_name:
                    embeddings = self.embedding_fn(texts, prefix="search_document: ")
                    self.collection.add(documents=texts, embeddings=embeddings, metadatas=metadatas, ids=ids)
                else:
                    self.collection.add(documents=texts, metadatas=metadatas, ids=ids)
                
                logger.info(f"✅ Synced {len(texts)} FAQ translations to ChromaDB")
            
            return len(texts)
        except Exception as e:
            logger.error(f"❌ Sync error: {e}")
            return 0
    

    
    def _detect_category(self, question: str):
        """
        v6.0: Detect category from question using intent keywords.
        Returns Category object or None.
        """
        try:
            from chatbot_app.models import Category
            
            q_lower = question.lower()
            categories = Category.objects.filter(is_active=True)
            
            for category in categories:
                if category.intent_keywords:
                    for keyword in category.intent_keywords:
                        if keyword.lower() in q_lower:
                            logger.info(f"🎯 Category detected: {category.name}")
                            return category
        except Exception as e:
            logger.warning(f"Category detection error: {e}")
        
        return None
    
    def _resolve_dynamic_variables(self, answer: str, variables: list, lang_code: str = 'uz') -> str:
        """
        v6.0: Replace {{variable}} placeholders with actual DynamicInfo values.
        """
        try:
            from chatbot_app.models import DynamicInfo
            
            for var_key in variables:
                try:
                    dynamic_info = DynamicInfo.objects.get(key=var_key, is_active=True)
                    value = getattr(dynamic_info, f'value_{lang_code}', None) or dynamic_info.value_uz or dynamic_info.value
                    answer = answer.replace(f"{{{{{var_key}}}}}", value)
                    logger.info(f"✅ Resolved: {var_key}")
                except DynamicInfo.DoesNotExist:
                    logger.warning(f"⚠️ Variable not found: {var_key}")
        except Exception as e:
            logger.warning(f"Dynamic variable resolution error: {e}")
        
        return answer

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
            # v6.1: Manually handle prefix for nomic if needed by querying text directly
            # Note: Custom embedding functions in ChromaDB are called automatically.
            # We must ensure our __call__ uses 'search_query: ' for queries.
            
            # Since we can't easily change prefix in Chroma's automatic call, 
            # we'll use manual embedding for query if it's nomic.
            if hasattr(self.embedding_fn, 'model_name') and "nomic" in self.embedding_fn.model_name:
                query_embeddings = self.embedding_fn([query], prefix="search_query: ")
                results = self.collection.query(
                    query_embeddings=query_embeddings,
                    n_results=n_results,
                    where=where_clause
                )
            else:
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
                    'source': meta.get('source', 'semantic'),
                    'source_type': meta.get('source', 'semantic') # Added for consistency
                })
        
        return sorted(documents, key=lambda x: x['similarity'], reverse=True)[:top_k]

    def retrieve_with_sources(self, question: str, lang_code: str = 'uz', top_k: int = 4, category_filter: str = None) -> Dict[str, Any]:
        """
        Prioritized retrieval with language support.
        1. Intent-Based Filtering & Category Matching
        2. Database FTS Search (with FAQ boosting)
        3. ChromaDB Semantic Search
        4. Rule-Based Reranking
        """
        # --- 1. Intent Detection (Database Driven) ---
        q_lower = question.lower()
        intent_category = self._detect_category(question)
        intent_name = intent_category.name if intent_category else None
        
        # Financial query priority: If 'kontrakt' or 'to'lov' detected, proactively check DynamicInfo
        financial_keywords = ['kontrakt', 'to\'lov', 'shartnoma', 'price', 'fee', 'tuition']
        is_financial = any(kw in q_lower for kw in financial_keywords)
        
        # 2. DynamicInfo Proactive Check for Financials
        dynamic_context = ""
        if is_financial:
            try:
                from chatbot_app.models import DynamicInfo
                # Seek for min/max contract info
                fees = DynamicInfo.objects.filter(key__icontains='contract', is_active=True)
                if fees.exists():
                    fee_details = []
                    for f in fees:
                        val = getattr(f, f'value_{lang_code}', None) or f.value_uz or f.value
                        if val: fee_details.append(f"{f.key}: {val}")
                    if fee_details:
                        dynamic_context = "DINAMIK MA'LUMOTLAR (Kontrakt):\n" + "\n".join(fee_details)
                        logger.info("⚡ Proactive DynamicInfo injection for financial query")
            except Exception as e:
                logger.warning(f"Proactive DynamicInfo error: {e}")

        # --- 2. Database FTS Search ---
        db_results = self.search_database(question, lang_code=lang_code, limit=top_k)
        
        # 2. ChromaDB Semantic Search
        semantic_results = self.search_chromadb(question, lang_code=lang_code, top_k=top_k)
        
        merged_results = []
        seen_faq_ids = set()
        
        # Add DB results (FAQ Boosting: reduced for balance)
        for r in db_results:
            confidence = r['relevance'] * 1.1 # Reduced from 1.25
            
            # Boost if category matches intent
            if intent_name and r['category'] == intent_name:
                confidence *= 1.3 # Reduced from 1.5
            # Penalize if intent category exists but result is NOT in it
            elif intent_name and r['category'] != intent_name:
                confidence *= 0.3 

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
            if intent_name and r['category'] == intent_name:
                confidence *= 1.4 
            elif intent_name and r['category'] != intent_name:
                confidence *= 0.3 

            merged_results.append({
                'text': r['text'],
                'title': r['title'],
                'category': r['category'],
                'confidence': min(0.99, confidence),
                'source_type': r['source_type'],
                'faq_id': r['faq_id']
            })
            
        merged_results.sort(key=lambda x: x['confidence'], reverse=True)
        
        # --- 4. Diverse Retrieval Logic ---
        # Ensure at least 1-2 document sources if available
        top_results = []
        doc_count = 0
        faq_count = 0
        
        for r in merged_results:
            if len(top_results) >= top_k:
                break
                
            # Diversity rule: don't fill all slots with just FAQs if documents are available
            if r['source_type'] == 'faq':
                if faq_count < (top_k - 1) or not any(x['source_type'] == 'document' for x in merged_results[merged_results.index(r):]):
                    top_results.append(r)
                    faq_count += 1
            else:
                top_results.append(r)
                doc_count += 1

        top_results = top_results[:top_k]
        
        context_blocks = []
        if dynamic_context:
            context_blocks.append(dynamic_context)

        for r in top_results:
            source_tag = f"FAQ #{r['faq_id']}" if r['source_type'] == 'faq' else f"Hujjat: {r['title']}"
            context_blocks.append(f"MANBA: {source_tag}\nMATN: {r['text']}")
        
        context = "\n---\n".join(context_blocks)
        sources = [{
            'title': r['title'],
            'category': r['category'],
            'source_type': r['source_type'],
            'confidence': r['confidence'],
            'relevance': round(r['confidence'] * 100),
            'faq_id': r.get('faq_id')
        } for r in top_results]
        
        return {
            'context': context,
            'top_confidence': top_results[0]['confidence'] if top_results else 0,
            'sources': sources,
            'total_found': len(merged_results)
        }



    
    def retrieve_with_self_correction(self, question: str, lang_code: str = 'uz', top_k: int = 4, max_iterations: int = 3):
        """
        v5.0 + v6.0: Self-Correction with Category Pre-filtering and Query Refinement.
        """
        from self_correction.grader import RelevanceGrader
        grader = RelevanceGrader()
        
        current_query = question
        refinement_history = []
        best_retrieval = None
        
        for i in range(max_iterations):
            logger.info(f"🔄 Self-Correction Iteration {i+1} for: {current_query}")
            
            # 1. Detect category for the CURRENT query
            detected_category = self._detect_category(current_query)
            category_filter = detected_category.name if detected_category else None
            
            # 2. Retrieve sources
            retrieval = self.retrieve_with_sources(current_query, lang_code, top_k, category_filter=category_filter)
            
            # 3. Grade the retrieval
            grade_result = grader.grade(current_query, retrieval['context'], intent=category_filter)
            
            # Store history
            refinement_history.append({
                'iteration': i + 1,
                'query': current_query,
                'is_relevant': grade_result['is_relevant'],
                'confidence': grade_result['confidence'],
                'reason': grade_result['reason']
            })
            
            # Update best retrieval if this one is better
            if best_retrieval is None or grade_result['confidence'] > best_retrieval['grading_result']['confidence']:
                best_retrieval = retrieval
                best_retrieval['grading_result'] = grade_result
                best_retrieval['iterations_used'] = i + 1
                best_retrieval['refinement_history'] = refinement_history
            
            # 4. Decide: Exit or Refine
            if grade_result['is_relevant'] and grade_result['confidence'] >= 0.7:
                logger.info(f"✅ Sufficient relevance found ({grade_result['confidence']:.2f})")
                return best_retrieval
            
            if i < max_iterations - 1:
                # Refine query
                refined_query = grade_result.get('suggested_refinement')
                if refined_query and refined_query != current_query:
                    logger.info(f"🔍 Refining query: {current_query} -> {refined_query}")
                    current_query = refined_query
                else:
                    # If no refinement suggested, break
                    break
        
        return best_retrieval

_rag_service = None

def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service

def sync_faqs_to_chromadb():
    service = get_rag_service()
    return service.sync_from_database()
