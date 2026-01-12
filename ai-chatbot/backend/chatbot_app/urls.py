"""
UzSWLU Chatbot URLs - Clean Version
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatbotResponseViewSet, DocumentViewSet

router = DefaultRouter()
router.register(r'chatbot', ChatbotResponseViewSet, basename='chatbot')
router.register(r'documents', DocumentViewSet, basename='documents')

urlpatterns = [
    path('', include(router.urls)),
]
