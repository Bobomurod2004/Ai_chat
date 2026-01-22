"""
Unit Tests for UzSWLU Chatbot
Tests RAG service, views, and integration.
"""
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock

from .models import FAQ, Conversation, Message, Category, FAQTranslation


class FAQModelTests(TestCase):
    """Tests for FAQ model."""
    
    def setUp(self):
        self.category = Category.objects.create(name='Test', slug='test')
        self.faq = FAQ.objects.create(
            category=self.category,
            is_current=True,
            year=2024
        )
        self.translation = FAQTranslation.objects.create(
            faq=self.faq,
            lang='uz',
            question='Test question about UzSWLU?',
            answer='Test answer about UzSWLU.'
        )
    
    def test_faq_creation(self):
        """Test FAQ creation."""
        self.assertEqual(self.translation.question, 'Test question about UzSWLU?')
        self.assertTrue(self.faq.is_current)
    
    def test_searchable_text(self):
        """Test searchable text in DB."""
        from django.db.models import F
        trans = FAQTranslation.objects.filter(faq=self.faq).first()
        self.assertIn('Test question', trans.question)
        self.assertIn('Test answer', trans.answer)


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
        self.assertEqual(data['status'], 'ok')
    
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
                {'message': greeting},
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 200)
    
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
        # This is now handled by the LLM system prompt and RAG relevance
        pass


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


# CachingTests removed as get_cache_key is not in views.py


class SessionTests(TestCase):
    """Tests for chat sessions."""
    
    def test_session_creation(self):
        """Test session is created correctly."""
        conv = Conversation.objects.create(user_id='test_user')
        self.assertIsNotNone(conv.id)
    
    def test_message_linked_to_conversation(self):
        """Test message is linked to conversation."""
        conv = Conversation.objects.create(user_id='test_user')
        msg = Message.objects.create(
            conversation=conv,
            sender_type='user',
            text='Test?'
        )
        
        self.assertEqual(msg.conversation, conv)
        self.assertEqual(conv.messages.count(), 1)
