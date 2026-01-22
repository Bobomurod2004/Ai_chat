"""
Ollama Embedding Function for ChromaDB
Uses nomic-embed-text model via Ollama API
"""
import requests
from typing import List
import logging
import numpy as np
from django.conf import settings

logger = logging.getLogger(__name__)


class OllamaEmbeddingFunction:
    """Custom embedding function using Ollama's nomic-embed-text model."""
    
    def __init__(self, model_name: str = "nomic-embed-text", url: str = None):
        self.model_name = model_name
        self.url = url or getattr(settings, 'OLLAMA_URL', 'http://ollama:11434')
        self.session = requests.Session()
        
        # Connection pool settings
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=3,
            pool_block=False
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        logger.info(f"✅ OllamaEmbeddingFunction initialized with model: {model_name}")
    
    def __call__(self, input_texts: List[str], prefix: str = "") -> List[List[float]]:
        """Generate embeddings with optional nomic prefixes."""
        embeddings = []
        
        for text in input_texts:
            # v6.1: Add nomic prefixes if model is nomic-embed-text
            if "nomic" in self.model_name and prefix:
                full_text = f"{prefix}{text}"
            else:
                full_text = text

            try:
                # Ollama embeddings API
                response = self.session.post(
                    f"{self.url}/api/embeddings",
                    json={
                        "model": self.model_name,
                        "prompt": full_text
                    },
                    timeout=(10, 30)  # 10s connect, 30s read
                )
                response.raise_for_status()
                data = response.json()
                embedding = data.get('embedding', [])
                
                if embedding:
                    # Normalize the vector to unit length for better similarity tracking
                    v = np.array(embedding)
                    norm = np.linalg.norm(v)
                    if norm > 0:
                        v = v / norm
                    embeddings.append(v.tolist())
                else:
                    logger.warning(f"⚠️ Empty embedding for text: {text[:50]}...")
                    raise ValueError("Empty embedding returned")
                    
            except requests.exceptions.HTTPError as e:
                if e.response and e.response.status_code == 404:
                    # Model topilmadi - exception raise qilish, fallback ishlatish uchun
                    logger.error(f"❌ Embedding model '{self.model_name}' topilmadi (404). Fallback ishlatiladi.")
                    raise ValueError(f"Model {self.model_name} not found")
                else:
                    logger.error(f"❌ Embedding HTTP error for text '{text[:50]}...': {e}")
                    raise
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Embedding connection error for text '{text[:50]}...': {e}")
                raise
            except Exception as e:
                logger.error(f"❌ Unexpected embedding error: {e}")
                raise
        
        return embeddings

