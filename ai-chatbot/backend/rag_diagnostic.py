import os
import sys
import django

# Setup Django
sys.path.append('/home/bobomurod/Django/ai_project/ai-chatbot/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_project.settings')
django.setup()

from rag_service import get_rag_service
from ollama_integration.client import ollama_client

def run_diagnostic():
    rag = get_rag_service()
    ollama = ollama_client
    
    question = "Xalqaro jurnalistika fakulteti kontrakt narxi haqida batafsil ma'lumot ber"
    language = 'uz'
    
    print(f"🔍 Query: {question}")
    
    # 1. RAG Retrieval
    retrieval = rag.retrieve_with_sources(question, lang_code=language)
    context = retrieval['context']
    
    print("\n--- [DEBUG] RAG CONTEXT ---")
    print(context)
    print("--- [DEBUG] END CONTEXT ---\n")
    
    # 2. LLM Generation
    print("🤖 Generating response...")
    response = ollama.generate(question, context=context, language=language)
    
    print("\n--- [RESULT] LLM RESPONSE ---")
    print(response)
    print("--- [RESULT] END RESPONSE ---")

if __name__ == "__main__":
    run_diagnostic()
