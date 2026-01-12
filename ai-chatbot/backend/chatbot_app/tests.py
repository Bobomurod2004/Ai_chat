"""
Unit Tests for UzSWLU Chatbot
Tests RAG service, views, and integration.
"""
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock

from .models import FAQ, ChatSession, ChatbotResponse, Category


class FAQModelTests(TestCase):
    """Tests for FAQ model."""
    
    def setUp(self):
        self.category = Category.objects.create(name='Test', slug='test')
        self.faq = FAQ.objects.create(
            question='Test question about UzSWLU?',
            answer='Test answer about UzSWLU.',
            keywords='test, uzswlu, university',
            category=self.category,
            priority=5
        )
    
    def test_faq_creation(self):
        """Test FAQ creation."""
        self.assertEqual(self.faq.question, 'Test question about UzSWLU?')
        self.assertTrue(self.faq.is_active)
    
    def test_searchable_text(self):
        """Test searchable text generation."""
        text = self.faq.get_searchable_text()
        self.assertIn('Test question', text)
        self.assertIn('Test answer', text)
    
    def test_record_view(self):
        """Test view counter increment."""
        initial_count = self.faq.view_count
        self.faq.record_view()
        self.faq.refresh_from_db()
        self.assertEqual(self.faq.view_count, initial_count + 1)


class ChatbotViewTests(APITestCase):
    """Tests for chatbot API views."""
    
    def setUp(self):
        self.client = Client()
        self.ask_url = '/api/chatbot/ask/'
        self.health_url = '/api/chatbot/health/'
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get(self.health_url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['database'], 'ok')
    
    def test_empty_question(self):
        """Test empty question returns error."""
        response = self.client.post(
            self.ask_url,
            {'question': ''},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_long_question(self):
        """Test too long question returns error."""
        long_question = 'a' * 501
        response = self.client.post(
            self.ask_url,
            {'question': long_question},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_greeting_response(self):
        """Test greeting questions get quick response."""
        greetings = ['hello', 'hi', 'salom']
        for greeting in greetings:
            response = self.client.post(
                self.ask_url,
                {'question': greeting},
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 201)
    
    def test_non_university_question(self):
        """Test non-university questions are filtered."""
        response = self.client.post(
            self.ask_url,
            {'question': 'What is the weather today?'},
            content_type='application/json'
        )
        data = response.json()
        self.assertIn('error', data)


class UniversityFilterTests(TestCase):
    """Tests for university topic filter."""
    
    def test_university_related_questions(self):
        """Test university-related questions are accepted."""
        from chatbot_app.views import is_university_related
        
        related_questions = [
            'What faculties does UzSWLU have?',
            'When is admission to university?',
            'How much is the tuition fee?',
            "What are bachelor's programs?",
        ]
        
        for q in related_questions:
            self.assertTrue(
                is_university_related(q),
                f"Should be related: {q}"
            )
    
    def test_unrelated_questions(self):
        """Test non-university questions are rejected."""
        from chatbot_app.views import is_university_related
        
        unrelated = [
            'How to cook pizza?',
            'What is the capital of France?',
            'Tell me a joke',
        ]
        
        for q in unrelated:
            self.assertFalse(
                is_university_related(q),
                f"Should not be related: {q}"
            )


class RAGServiceTests(TestCase):
    """Tests for RAG service."""
    
    @patch('rag_service.RAGService.search_chromadb')
    def test_search_returns_results(self, mock_search):
        """Test semantic search returns results."""
        mock_search.return_value = [{
            'text': 'Test content',
            'similarity': 0.8,
            'source': 'faq'
        }]
        
        from rag_service import get_rag_service
        rag = get_rag_service()
        results = rag.search_chromadb('test query')
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['similarity'], 0.8)


class CachingTests(APITestCase):
    """Tests for response caching."""
    
    def test_cache_key_generation(self):
        """Test cache key is consistent."""
        from chatbot_app.views import get_cache_key
        
        key1 = get_cache_key('What is admission?', 'en')
        key2 = get_cache_key('what is admission?', 'en')
        key3 = get_cache_key('What is admission?', 'uz')
        
        # Same question (case-insensitive) should have same key
        self.assertEqual(key1, key2)
        
        # Different language should have different key
        self.assertNotEqual(key1, key3)


class SessionTests(TestCase):
    """Tests for chat sessions."""
    
    def test_session_creation(self):
        """Test session is created correctly."""
        session = ChatSession.objects.create()
        self.assertIsNotNone(session.session_id)
    
    def test_response_linked_to_session(self):
        """Test response is linked to session."""
        session = ChatSession.objects.create()
        response = ChatbotResponse.objects.create(
            session=session,
            question='Test?',
            response='Answer.'
        )
        
        self.assertEqual(response.session, session)
        self.assertEqual(session.messages.count(), 1)
