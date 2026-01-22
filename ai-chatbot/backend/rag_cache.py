"""
Redis Caching Layer for Advanced RAG v5.0

Caches frequently asked questions to reduce latency and Ollama API calls.
"""

import redis
import json
import hashlib
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class RAGCache:
    """Redis-based caching for RAG responses"""
    
    def __init__(self, redis_host='redis', redis_port=6379, ttl=3600):
        """
        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            ttl: Time to live in seconds (default: 1 hour)
        """
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=0,
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            self.ttl = ttl
            self.enabled = True
            logger.info(f"✅ Redis cache enabled (TTL: {ttl}s)")
        except Exception as e:
            logger.warning(f"⚠️ Redis unavailable, caching disabled: {e}")
            self.redis_client = None
            self.enabled = False
    
    def _generate_key(self, question: str, lang_code: str) -> str:
        """Generate cache key from question and language"""
        # Normalize question (lowercase, strip)
        normalized = question.lower().strip()
        # Create hash
        key_string = f"{lang_code}:{normalized}"
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"rag:v5:{key_hash}"
    
    def get(self, question: str, lang_code: str) -> Optional[Dict[str, Any]]:
        """
        Get cached response
        
        Returns:
            Cached response dict or None if not found
        """
        if not self.enabled:
            return None
        
        try:
            key = self._generate_key(question, lang_code)
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                logger.info(f"🎯 Cache HIT: {question[:50]}...")
                return json.loads(cached_data)
            else:
                logger.debug(f"❌ Cache MISS: {question[:50]}...")
                return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, question: str, lang_code: str, response: Dict[str, Any]) -> bool:
        """
        Cache a response
        
        Args:
            question: User's question
            lang_code: Language code
            response: Response dict to cache
        
        Returns:
            True if cached successfully
        """
        if not self.enabled:
            return False
        
        try:
            key = self._generate_key(question, lang_code)
            cached_data = json.dumps(response)
            self.redis_client.setex(key, self.ttl, cached_data)
            logger.info(f"💾 Cached: {question[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def invalidate(self, question: str, lang_code: str) -> bool:
        """Invalidate a specific cache entry"""
        if not self.enabled:
            return False
        
        try:
            key = self._generate_key(question, lang_code)
            self.redis_client.delete(key)
            logger.info(f"🗑️ Cache invalidated: {question[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Cache invalidate error: {e}")
            return False
    
    def clear_all(self) -> bool:
        """Clear all RAG cache entries"""
        if not self.enabled:
            return False
        
        try:
            # Find all keys matching pattern
            keys = self.redis_client.keys("rag:v5:*")
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"🗑️ Cleared {len(keys)} cache entries")
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.enabled:
            return {'enabled': False}
        
        try:
            keys = self.redis_client.keys("rag:v5:*")
            return {
                'enabled': True,
                'total_entries': len(keys),
                'ttl': self.ttl,
                'redis_info': self.redis_client.info('stats')
            }
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {'enabled': True, 'error': str(e)}


# Singleton instance
_rag_cache = None

def get_rag_cache() -> RAGCache:
    """Get or create RAG cache instance"""
    global _rag_cache
    if _rag_cache is None:
        _rag_cache = RAGCache()
    return _rag_cache
