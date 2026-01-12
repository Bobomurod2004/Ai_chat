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
        logging.getLogger("posthog").setLevel(logging.CRITICAL)  # PostHog xatoliklarini butunlay yashirish
        
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
        
        try:
            self.collection = self.client.get_collection(
                self.collection_name,
                embedding_function=embedding_function
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
        """Sync FAQs from PostgreSQL to ChromaDB."""
        try:
            import django
            django.setup()
            from chatbot_app.models import FAQ
            
            faqs = FAQ.objects.filter(is_active=True)
            if not faqs.exists():
                print("No FAQs to sync")
                return 0
            
            try:
                self.client.delete_collection(self.collection_name)
            except:
                pass
            
            # Embedding function - Multilingual support (same as above)
            embedding_function = None
            try:
                from chromadb.utils import embedding_functions
                try:
                    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                        model_name="paraphrase-multilingual-MiniLM-L12-v2"
                    )
                except:
                    embedding_function = embedding_functions.DefaultEmbeddingFunction()
            except Exception:
                embedding_function = None
            
            self.collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=embedding_function,
                metadata={"description": "UzSWLU knowledge base"}
            )
            
            texts = []
            metadatas = []
            ids = []
            
            for faq in faqs:
                search_text = faq.get_searchable_text()
                texts.append(search_text)
                metadatas.append({
                    'faq_id': faq.id,
                    'category': faq.category.name if faq.category else 'General',
                    'title': faq.question[:100],
                    'priority': faq.priority,
                    'type': 'faq'
                })
                ids.append(f"faq_{faq.id}")
                faq.embedding_updated = True
                faq.save(update_fields=['embedding_updated'])
            
            self.collection.add(documents=texts, metadatas=metadatas, ids=ids)
            logger.info(f"✅ Synced {len(texts)} FAQs to ChromaDB")
            return len(texts)
        except Exception as e:
            logger.error(f"❌ Sync error: {e}")
            return 0
    
    def search_database(self, query: str, limit: int = 5) -> List[Dict]:
        """Search FAQs from PostgreSQL using Full-Text Search + keyword matching."""
        try:
            from chatbot_app.models import FAQ
            from django.db.models import Q
            from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
            
            results = []
            query_lower = query.lower()
            query_words = [w for w in query_lower.split() if len(w) > 2]
            
            # METHOD 1: Full-Text Search (PostgreSQL FTS) - for English/Russian
            try:
                # Simple Uzbek/Russian normalization - remove common suffixes
                def normalize_uz_ru(text):
                    text = text.lower()
                    # Uzbek suffixes
                    suffixes = ['lar', 'ning', 'dan', 'ga', 'ni', 'da', 'mi', 'chi', 'si', 'im', 'ing']
                    words = text.split()
                    normalized_words = []
                    for word in words:
                        for s in suffixes:
                            if word.endswith(s) and len(word) > len(s) + 2:
                                word = word[:-len(s)]
                        normalized_words.append(word)
                    return " ".join(normalized_words)

                normalized_query = normalize_uz_ru(query)
                vector = SearchVector('question', weight='A', config='simple') + \
                         SearchVector('keywords', weight='B', config='simple') + \
                         SearchVector('answer', weight='C', config='simple')
                
                search_query = SearchQuery(normalized_query, config='simple')
                
                faqs_fts = FAQ.objects.annotate(
                    rank=SearchRank(vector, search_query)
                ).filter(
                    Q(rank__gte=0.05) | Q(question__icontains=query),
                    is_active=True
                ).select_related('category').order_by('-rank', '-priority', '-view_count')[:limit]
                
                for faq in faqs_fts:
                    results.append({
                        'faq_id': faq.id,
                        'question': faq.question,
                        'answer': faq.answer,
                        'category': faq.category.name if faq.category else 'General',
                        'priority': faq.priority,
                        'relevance': float(faq.rank) + 0.2,  # Boost FTS results
                        'source': 'database_fts'
                    })
            except Exception as e:
                logger.warning(f"FTS search error: {e}")
            
            # METHOD 2: Keyword matching (icontains) - works for all languages including Uzbek
            if query_words:
                q_filter = Q(is_active=True)
                keyword_filter = Q()
                
                for word in query_words:
                    keyword_filter |= (
                        Q(question__icontains=word) |
                        Q(answer__icontains=word) |
                        Q(keywords__icontains=word)
                    )
                
                q_filter &= keyword_filter
                
                faqs_keyword = FAQ.objects.filter(q_filter).select_related('category')[:limit * 2]
                
                seen_ids = {r['faq_id'] for r in results}
                
                for faq in faqs_keyword:
                    if faq.id in seen_ids:
                        continue
                    
                    # Calculate relevance score
                    relevance = self._calculate_relevance(query, faq)
                    
                    # Boost if exact match in question
                    if query_lower in faq.question.lower():
                        relevance = min(relevance + 0.3, 1.0)
                    
                    results.append({
                        'faq_id': faq.id,
                        'question': faq.question,
                        'answer': faq.answer,
                        'category': faq.category.name if faq.category else 'General',
                        'priority': faq.priority,
                        'relevance': relevance,
                        'source': 'database_keyword'
                    })
            
            # Sort by relevance and priority
            results = sorted(results, key=lambda x: (x['relevance'], x['priority']), reverse=True)
            
            # Record views for top results
            for result in results[:limit]:
                try:
                    faq = FAQ.objects.get(pk=result['faq_id'])
                    faq.record_view()
                except:
                    pass
            
            return results[:limit]
        except Exception as e:
            logger.error(f"Database search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _calculate_relevance(self, query: str, faq) -> float:
        """
        Calculates relevance score using multiple methods:
        - Exact match (1.0)
        - Keyword overlap (0.7 weight)
        - Start-of-sentence match boost
        """
        query_lower = query.lower().strip()
        question_lower = faq.question.lower().strip()
        
        # 1. Exact match (case insensitive)
        if query_lower == question_lower:
            return 1.0
            
        # 2. Start-of-sentence match boost
        if question_lower.startswith(query_lower) or query_lower.startswith(question_lower):
            return 0.95

        score = 0.0
        query_words = set(query_lower.split())
        if not query_words:
            return 0.0
            
        # 3. Keyword overlap
        question_words = set(question_lower.split())
        overlap = len(query_words & question_words) / max(len(query_words), 1)
        score += overlap * 0.7
        
        # 4. Keyword field boost
        if faq.keywords:
            keyword_list = set(faq.keywords.lower().replace(',', ' ').split())
            kw_overlap = len(query_words & keyword_list) / max(len(query_words), 1)
            score += kw_overlap * 0.3
        
        # 5. Priority boost (small)
        score += (faq.priority / 10) * 0.05
        
        return min(score, 0.99) # Only exact match gets 1.0
    
    # Minimum similarity threshold - reject irrelevant results
    SIMILARITY_THRESHOLD = 0.25
    
    def search_chromadb(self, query: str, top_k: int = 5) -> List[Dict]:
        """Semantic search in ChromaDB (includes FAQs and Documents)."""
        if self.collection.count() == 0:
            return []
        
        try:
            # Get more results for better coverage
            n_results = min(top_k * 3, self.collection.count())
            
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
        except Exception as e:
            # Dimension mismatch xatolik bo'lsa, fallback embedding function ishlatish kerak
            error_str = str(e)
            if "dimension" in error_str.lower() or "InvalidDimensionException" in error_str:
                logger.error(f"❌ Embedding dimension mismatch: {e}")
                logger.info("⚠️ Collection eski embedding function bilan yaratilgan. Fallback embedding function ishlatiladi.")
                # Fallback embedding function bilan qayta urinish
                try:
                    from chromadb.utils import embedding_functions
                    fallback_embedding = embedding_functions.SentenceTransformerEmbeddingFunction(
                        model_name="paraphrase-multilingual-MiniLM-L12-v2"
                    )
                    # Collection'ni fallback embedding function bilan qayta olish
                    self.collection = self.client.get_collection(
                        self.collection_name,
                        embedding_function=fallback_embedding
                    )
                    n_results = min(top_k * 3, self.collection.count())
                    results = self.collection.query(
                        query_texts=[query],
                        n_results=n_results
                    )
                    logger.info("✅ Fallback embedding function bilan search muvaffaqiyatli")
                except Exception as e2:
                    logger.error(f"❌ Fallback embedding function ham ishlamadi: {e2}")
                    return []
            else:
                logger.error(f"❌ ChromaDB search xatolik: {e}")
                return []
        
        documents = []
        if results and results.get('documents'):
            for i, doc in enumerate(results['documents'][0]):
                meta = results['metadatas'][0][i] if results.get('metadatas') else {}
                dist = results['distances'][0][i] if results.get('distances') else 1.0
                similarity = max(0, 1 - (dist / 2))
                
                # Skip results below threshold
                if similarity < self.SIMILARITY_THRESHOLD:
                    continue
                
                # Determine source type
                src_type = meta.get('source', meta.get('type', 'semantic'))
                
                documents.append({
                    'text': doc,
                    'title': meta.get('title', meta.get('document_title', 'UzSWLU')),
                    'category': meta.get('category', 'General'),
                    'faq_id': meta.get('faq_id'),
                    'document_id': meta.get('document_id'),
                    'chunk_index': meta.get('chunk_index', 0),
                    'similarity': similarity,
                    'source': src_type
                })
        
        # Return more results, let retrieve_with_sources filter
        return documents
    
    def search_documents(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search only in uploaded documents."""
        if self.collection.count() == 0:
            return []
        
        results = self.collection.query(
            query_texts=[query],
            n_results=min(top_k * 2, self.collection.count()),
            where={"source": "document"}  # Filter only documents
        )
        
        documents = []
        if results and results.get('documents'):
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i] if results.get('metadatas') else {}
                distance = results['distances'][0][i] if results.get('distances') else 1.0
                similarity = max(0, 1 - (distance / 2))
                
                documents.append({
                    'text': doc[:500],
                    'title': metadata.get('document_title', 'Document'),
                    'document_id': metadata.get('document_id'),
                    'chunk_index': metadata.get('chunk_index', 0),
                    'similarity': similarity,
                    'source': 'document'
                })
        
        return documents[:top_k]
    
    def keyword_search_documents(self, query: str) -> Dict[str, List[str]]:
        """
        Keyword-based search in documents - finds exact word matches.
        Returns: {doc_id: [matching_chunk_texts]}
        """
        doc_chunks = {}  # {doc_id: [chunk_texts]}
        # Include shorter words too (2+ chars)
        query_words = [w.lower() for w in query.split() if len(w) > 2]
        
        try:
            # Get all document chunks
            doc_results = self.collection.get(where={"source": "document"})
            if not doc_results or not doc_results['documents']:
                return doc_chunks
            
            for i, text in enumerate(doc_results['documents']):
                text_lower = text.lower()
                match_score = 0
                matched_words = []
                
                # Count all matching words for better ranking
                for word in query_words:
                    if word in text_lower:
                        match_score += text_lower.count(word)
                        matched_words.append(word)
                
                if match_score > 0:
                    meta = doc_results['metadatas'][i] if doc_results.get('metadatas') else {}
                    doc_id = meta.get('document_id')
                    if doc_id:
                        if doc_id not in doc_chunks:
                            doc_chunks[doc_id] = []
                        # Store with score for ranking
                        doc_chunks[doc_id].append({
                            'text': text,
                            'score': match_score,
                            'chunk_index': meta.get('chunk_index', 0)
                        })
                        print(f"📄 Keyword match {matched_words} (score: {match_score}) in doc {doc_id}")
                        
        except Exception as e:
            print(f"Keyword search error: {e}")
        
        return doc_chunks
    
    def get_all_document_chunks(self, doc_id: str) -> List[str]:
        """Get ALL chunks for a document in correct order."""
        try:
            doc_results = self.collection.get(
                where={"document_id": doc_id}
            )
            if not doc_results or not doc_results['documents']:
                return []
            
            # Sort by chunk_index
            chunks_with_index = []
            for i, doc in enumerate(doc_results['documents']):
                meta = doc_results['metadatas'][i] if doc_results.get('metadatas') else {}
                chunks_with_index.append({
                    'text': doc,
                    'index': meta.get('chunk_index', i)
                })
            
            chunks_with_index.sort(key=lambda x: x['index'])
            return [c['text'] for c in chunks_with_index]
        except Exception as e:
            print(f"Error getting document chunks: {e}")
            return []
    
    def retrieve_with_sources(self, question: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Prioritized retrieval:
        1. DynamicInfo (Handled in views, but we can check here too if needed)
        2. FAQ (Postgres Keyword/Exact Match) -> If score > 0.9, STOP.
        3. ChromaDB (Documents Semantic Search)
        """
        question_lower = question.lower().strip()
        
        # 1. DATABASE FAQ SEARCH (Prioritized over Chroma)
        db_results = self.search_database(question, limit=top_k)
        
        # Check for exact or very high confidence FAQ match
        best_faq = db_results[0] if db_results else None
        if best_faq and best_faq.get('relevance', 0) >= 0.75:
            logger.info(f"🎯 High confidence FAQ match found ({best_faq['relevance']}).")
            return {
                'context': f"[{best_faq['category']} - {int(best_faq['relevance']*100)}%]\n{best_faq['answer']}",
                'sources': [{
                    'rank': 1,
                    'title': best_faq['question'],
                    'category': best_faq['category'],
                    'source_type': 'faq',
                    'confidence': best_faq['relevance'],
                    'faq_id': best_faq['faq_id']
                }],
                'top_source': {
                    'title': best_faq['question'],
                    'confidence': best_faq['relevance'],
                    'source_type': 'faq'
                },
                'total_found': len(db_results)
            }

        # 2. DOCUMENT SEARCH (Keyword match in documents as fallback)
        keyword_results = self.keyword_search_documents(question)
        
        # 3. CHROMADB SEMANTIC SEARCH (General fallback)
        chroma_results = self.search_chromadb(question, top_k=top_k)
        
        merged_results = []
        seen_faq_ids = set()
        doc_ids_processed = set()
        
        # Add high-confidence FAQ results from DB search
        for result in db_results:
            faq_id = result.get('faq_id')
            if faq_id:
                seen_faq_ids.add(faq_id)
                merged_results.append({
                    'text': result['answer'],
                    'title': result['question'][:80],
                    'category': result['category'],
                    'confidence': result['relevance'],
                    'source_type': 'faq',
                    'faq_id': faq_id,
                    'is_faq': True
                })

        # Add document keyword matches
        for doc_id, chunk_data in keyword_results.items():
            if doc_id in doc_ids_processed: continue
            doc_ids_processed.add(doc_id)
            
            sorted_chunks = sorted(chunk_data, key=lambda x: -x['score'])
            all_chunks = self.get_all_document_chunks(doc_id)
            if all_chunks:
                full_text = '\n\n'.join(all_chunks)
                confidence = min(0.6 + (sorted_chunks[0]['score'] * 0.05), 0.95)
                merged_results.append({
                    'text': full_text,
                    'title': f"Document ID: {doc_id}", # Titles should be retrieved from metadata ideally
                    'category': 'Document',
                    'confidence': confidence,
                    'source_type': 'document',
                    'document_id': doc_id,
                    'is_full_document': True
                })

        # Add remaining ChromaDB semantic results
        for result in chroma_results:
            fid = result.get('faq_id')
            did = result.get('document_id')
            
            if fid and fid not in seen_faq_ids:
                seen_faq_ids.add(fid)
                merged_results.append({
                    'text': result['text'],
                    'title': result['title'],
                    'category': result.get('category', 'General'),
                    'confidence': result['similarity'],
                    'source_type': 'semantic',
                    'faq_id': fid
                })
            elif did and did not in doc_ids_processed:
                doc_ids_processed.add(did)
                all_chunks = self.get_all_document_chunks(did)
                if all_chunks:
                    merged_results.append({
                        'text': '\n\n'.join(all_chunks),
                        'title': result['title'],
                        'category': 'Document',
                        'confidence': result['similarity'],
                        'source_type': 'document',
                        'document_id': did,
                        'is_full_document': True
                    })

        # Sort merged results by confidence (FAQ priority)
        merged_results.sort(key=lambda x: (x.get('is_faq', False), x['confidence']), reverse=True)
        
        final_results = merged_results[:top_k]
        
        if not final_results:
            return {'context': '', 'sources': [], 'top_source': None, 'total_found': 0}
        
        context_parts = []
        sources = []
        for i, doc in enumerate(final_results):
            conf_pct = int(doc['confidence'] * 100)
            if doc.get('is_full_document'):
                text = doc['text'][:4000]
                context_parts.append(f"[DOCUMENT: {doc['title']} - {conf_pct}%]\n{text}")
            else:
                text = doc['text'][:800]
                context_parts.append(f"[{doc['category']} - {conf_pct}%]\n{text}")
            
            sources.append({
                'rank': i + 1,
                'title': doc['title'],
                'category': doc['category'],
                'source_type': doc['source_type'],
                'confidence': doc['confidence'],
                'faq_id': doc.get('faq_id')
            })
            
        return {
            'context': '\n\n'.join(context_parts),
            'sources': sources,
            'top_source': sources[0] if sources else None,
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
