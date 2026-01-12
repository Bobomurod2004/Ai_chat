"""
Celery Tasks for UzSWLU Chatbot
Asynchronous processing for Ollama requests and document processing
"""
from celery import shared_task
from django.core.cache import cache
import logging
import time

logger = logging.getLogger('chatbot_app')


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def process_ollama_request(self, question, context, language='uz', session_id=None):
    """
    Asynchronous Ollama request processing.
    Bu task Ollama'ga so'rov yuboradi va javobni qaytaradi.
    
    Args:
        question: Foydalanuvchi savoli
        context: RAG context
        language: Til (uz, ru, en)
        session_id: Session ID
        
    Returns:
        dict: {'response': str, 'error': str or None}
    """
    try:
        from ollama_integration.client import ollama_client
        
        logger.info(f"Processing Ollama request for session {session_id}: {question[:50]}")
        
        # Generate response
        response_text = ollama_client.generate(question, context=context, language=language)
        
        logger.info(f"Ollama response generated for session {session_id}")
        
        return {
            'response': response_text,
            'error': None,
            'session_id': session_id
        }
    except Exception as e:
        logger.error(f"Ollama task error: {e}", exc_info=True)
        
        # Retry on failure
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return {
            'response': None,
            'error': str(e),
            'session_id': session_id
        }


@shared_task(bind=True, max_retries=2)
def process_document_task(self, document_id):
    """
    Asynchronous document processing.
    Hujjatni RAG systemga qo'shadi.
    
    Args:
        document_id: Document model ID
        
    Returns:
        dict: {'success': bool, 'chunks': int, 'error': str or None}
    """
    try:
        from chatbot_app.models import Document
        from document_processor import DocumentRAGIntegration
        
        logger.info(f"Processing document {document_id}")
        
        # Get document
        try:
            document = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            logger.error(f"Document {document_id} not found")
            return {'success': False, 'error': 'Document not found'}
        
        # Update status
        document.status = 'processing'
        document.save()
        
        # Process document
        integration = DocumentRAGIntegration()
        result = integration.process_and_store(document)
        
        logger.info(f"Document {document_id} processed: {result}")
        
        return {
            'success': True,
            'chunks': result.get('chunks_created', 0),
            'error': None
        }
    except Exception as e:
        logger.error(f"Document processing error: {e}", exc_info=True)
        
        # Update document status
        try:
            document = Document.objects.get(id=document_id)
            document.status = 'failed'
            document.error_message = str(e)[:500]
            document.save()
        except Exception:
            pass
        
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def cleanup_old_sessions():
    """
    Clean up old inactive sessions (older than 7 days).
    Cronjob task - har kuni ishlatiladi.
    """
    from datetime import timedelta
    from django.utils import timezone
    from chatbot_app.models import ChatSession
    
    cutoff_date = timezone.now() - timedelta(days=7)
    
    # Delete old inactive sessions
    deleted_count = ChatSession.objects.filter(
        updated_at__lt=cutoff_date,
        is_active=False
    ).delete()[0]
    
    logger.info(f"Cleaned up {deleted_count} old sessions")
    
    return {'deleted': deleted_count}


@shared_task
def update_analytics_daily():
    """
    Calculate daily analytics statistics.
    Cronjob task - har kuni ishlatiladi.
    """
    from django.utils import timezone
    from datetime import timedelta
    from chatbot_app.models import ChatAnalytics, DailyStats
    from django.db.models import Count, Avg, Q
    
    yesterday = timezone.now().date() - timedelta(days=1)
    
    # Calculate stats for yesterday
    stats = ChatAnalytics.objects.filter(
        created_at__date=yesterday
    ).aggregate(
        total_queries=Count('id'),
        avg_response_time=Avg('response_time'),
        cached_queries=Count('id', filter=Q(was_cached=True)),
        error_queries=Count('id', filter=Q(error_occurred=True)),
        avg_confidence=Avg('confidence_score'),
    )
    
    # Create or update DailyStats
    DailyStats.objects.update_or_create(
        date=yesterday,
        defaults={
            'total_queries': stats['total_queries'] or 0,
            'avg_response_time': stats['avg_response_time'] or 0,
            'cached_queries': stats['cached_queries'] or 0,
            'error_queries': stats['error_queries'] or 0,
            'avg_confidence': stats['avg_confidence'] or 0,
        }
    )
    
    logger.info(f"Daily analytics updated for {yesterday}")
    
    return stats
