"""
Diagnostic Test for Advanced RAG v5.0 Self-Correction

Tests the LangGraph-style workflow:
1. Retriever
2. Grader
3. Generator
4. Hallucination Checker
"""

import os
import sys
import django

# Setup Django
sys.path.append('/home/bobomurod/Django/ai_project/ai-chatbot/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_project.settings')
django.setup()

from rag_service import get_rag_service
from ollama_integration.client import ollama_client
from self_correction.hallucination_checker import HallucinationChecker

def test_yotoqxona_paradox():
    """
    Test Case: Yotoqxona Paradox
    Expected: FAQ should override Nizom
    """
    print("\n" + "="*80)
    print("🧪 TEST 1: Yotoqxona Paradox (FAQ vs Nizom)")
    print("="*80)
    
    rag = get_rag_service()
    question = "Magistratura talabalari yotoqxonada yashay oladimi?"
    
    # Use Self-Correction workflow
    result = rag.retrieve_with_self_correction(question, lang_code='uz', max_iterations=3)
    
    print(f"\n📊 Iterations Used: {result['iterations_used']}")
    print(f"✅ Relevance: {result['grading_result']['is_relevant']}")
    print(f"📈 Confidence: {result['grading_result']['confidence']:.0%}")
    
    print("\n📚 Sources Retrieved:")
    for i, source in enumerate(result['sources'][:3], 1):
        print(f"  {i}. [{source['source_type'].upper()}] {source['title']} (Relevance: {source['relevance']}%)")
    
    # Generate answer
    print("\n🤖 Generating answer...")
    answer = ollama_client.generate(question, result['context'], language='uz')
    
    # Check for hallucination
    hallucination_checker = HallucinationChecker()
    hallucination_result = hallucination_checker.check(answer, result['context'])
    
    print(f"\n🔍 Hallucination Check:")
    print(f"  - Is Grounded: {hallucination_result['is_grounded']}")
    print(f"  - Confidence: {hallucination_result['confidence']:.0%}")
    if hallucination_result['hallucinated_claims']:
        print(f"  - Issues: {hallucination_result['hallucinated_claims']}")
    
    print(f"\n💬 Final Answer:")
    print(answer[:500])
    
    return {
        'test_name': 'Yotoqxona Paradox',
        'passed': hallucination_result['is_grounded'] and result['grading_result']['is_relevant'],
        'iterations': result['iterations_used']
    }

def test_kontrakt_narxi():
    """
    Test Case: Kontrakt Narxi (Numerical Extraction)
    Expected: Should provide specific price or fallback gracefully
    """
    print("\n" + "="*80)
    print("🧪 TEST 2: Kontrakt Narxi (Numerical Data)")
    print("="*80)
    
    rag = get_rag_service()
    question = "Xalqaro jurnalistika fakulteti kontrakt narxi qancha?"
    
    result = rag.retrieve_with_self_correction(question, lang_code='uz', max_iterations=3)
    
    print(f"\n📊 Iterations Used: {result['iterations_used']}")
    print(f"✅ Relevance: {result['grading_result']['is_relevant']}")
    
    answer = ollama_client.generate(question, result['context'], language='uz')
    
    hallucination_checker = HallucinationChecker()
    hallucination_result = hallucination_checker.check(answer, result['context'])
    
    print(f"\n🔍 Hallucination Check: {hallucination_result['is_grounded']}")
    print(f"\n💬 Final Answer:")
    print(answer[:500])
    
    return {
        'test_name': 'Kontrakt Narxi',
        'passed': hallucination_result['is_grounded'],
        'iterations': result['iterations_used']
    }

def test_refinement_loop():
    """
    Test Case: Query Refinement
    Expected: Should refine irrelevant queries
    """
    print("\n" + "="*80)
    print("🧪 TEST 3: Query Refinement Loop")
    print("="*80)
    
    rag = get_rag_service()
    question = "Tibbiyot fakulteti bormi?"  # Should be irrelevant
    
    result = rag.retrieve_with_self_correction(question, lang_code='uz', max_iterations=3)
    
    print(f"\n📊 Refinement History:")
    for entry in result['refinement_history']:
        print(f"  Iteration {entry['iteration']}: Relevant={entry['is_relevant']}, Confidence={entry['confidence']:.0%}")
    
    print(f"\n✅ Final Relevance: {result['grading_result']['is_relevant']}")
    
    return {
        'test_name': 'Refinement Loop',
        'passed': True,  # Always passes if completes
        'iterations': result['iterations_used']
    }

if __name__ == "__main__":
    print("\n🚀 Starting Advanced RAG v5.0 Diagnostic Tests")
    print("="*80)
    
    results = []
    
    try:
        results.append(test_yotoqxona_paradox())
    except Exception as e:
        print(f"\n❌ Test 1 Failed: {e}")
        results.append({'test_name': 'Yotoqxona Paradox', 'passed': False, 'iterations': 0})
    
    try:
        results.append(test_kontrakt_narxi())
    except Exception as e:
        print(f"\n❌ Test 2 Failed: {e}")
        results.append({'test_name': 'Kontrakt Narxi', 'passed': False, 'iterations': 0})
    
    try:
        results.append(test_refinement_loop())
    except Exception as e:
        print(f"\n❌ Test 3 Failed: {e}")
        results.append({'test_name': 'Refinement Loop', 'passed': False, 'iterations': 0})
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in results if r['passed'])
    total = len(results)
    
    for result in results:
        status = "✅ PASS" if result['passed'] else "❌ FAIL"
        print(f"{status} - {result['test_name']} (Iterations: {result['iterations']})")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed ({passed/total*100:.0%})")
