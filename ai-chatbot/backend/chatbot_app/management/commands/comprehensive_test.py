"""
Django Management Command: Comprehensive Test
Tizimning barcha komponentlarini to'liq test qiladi
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from chatbot_app.models import FAQTranslation, DynamicInfo, Category
from rag_service import get_rag_service
import time
import json

# ANSI color codes
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    WHITE = '\033[97m'
    RESET = '\033[0m'


class Command(BaseCommand):
    help = 'Run comprehensive system tests'

    def __init__(self):
        super().__init__()
        self.results = {
            'database_tests': [],
            'rag_tests': [],
            'search_tests': [],
            'performance_tests': [],
            'summary': {}
        }

    def handle(self, *args, **options):
        self.stdout.write(Colors.CYAN + '\n' + '='*70)
        self.stdout.write(Colors.CYAN + '🧪 COMPREHENSIVE SYSTEM TEST')
        self.stdout.write(Colors.CYAN + '='*70 + '\n')
        
        # Run all tests
        self.test_database_integrity()
        self.test_rag_service()
        self.test_search_functionality()
        self.test_multilingual_support()
        self.test_performance()
        
        # Generate report
        self.generate_report()
        
        self.stdout.write(Colors.GREEN + '\n✅ All tests completed!\n')

    def test_database_integrity(self):
        """Test database models and data integrity"""
        self.stdout.write(Colors.YELLOW + '\n📊 Testing Database Integrity...')
        self.stdout.write('-' * 70)
        
        tests = []
        
        # Test 1: Categories
        cat_count = Category.objects.count()
        test_result = {
            'name': 'Categories Count',
            'expected': '≥ 5',
            'actual': cat_count,
            'passed': cat_count >= 5
        }
        tests.append(test_result)
        self._print_test_result(test_result)
        
        # Test 2: FAQs
        faq_count = FAQTranslation.objects.count()
        test_result = {
            'name': 'FAQ Translations Count',
            'expected': '≥ 20',
            'actual': faq_count,
            'passed': faq_count >= 20
        }
        tests.append(test_result)
        self._print_test_result(test_result)
        
        # Test 3: Multilingual FAQs
        uz_count = FAQTranslation.objects.filter(lang='uz').count()
        ru_count = FAQTranslation.objects.filter(lang='ru').count()
        en_count = FAQTranslation.objects.filter(lang='en').count()
        
        test_result = {
            'name': 'Multilingual Coverage',
            'expected': 'uz, ru, en all > 0',
            'actual': f'uz:{uz_count}, ru:{ru_count}, en:{en_count}',
            'passed': uz_count > 0 and ru_count > 0 and en_count > 0
        }
        tests.append(test_result)
        self._print_test_result(test_result)
        
        # Test 4: Search Vectors
        with_tsv = FAQTranslation.objects.exclude(question_tsv=None).count()
        test_result = {
            'name': 'Search Vectors Generated',
            'expected': f'{faq_count}',
            'actual': with_tsv,
            'passed': with_tsv == faq_count
        }
        tests.append(test_result)
        self._print_test_result(test_result)
        
        # Test 5: Dynamic Info
        dynamic_count = DynamicInfo.objects.filter(is_active=True).count()
        test_result = {
            'name': 'Active Dynamic Info',
            'expected': '≥ 10',
            'actual': dynamic_count,
            'passed': dynamic_count >= 10
        }
        tests.append(test_result)
        self._print_test_result(test_result)
        
        self.results['database_tests'] = tests

    def test_rag_service(self):
        """Test RAG service initialization and ChromaDB"""
        self.stdout.write(Colors.YELLOW + '\n🔍 Testing RAG Service...')
        self.stdout.write('-' * 70)
        
        tests = []
        
        try:
            # Test 1: RAG Service Initialization
            start_time = time.time()
            rag = get_rag_service()
            init_time = time.time() - start_time
            
            test_result = {
                'name': 'RAG Service Init',
                'expected': '< 5s',
                'actual': f'{init_time:.2f}s',
                'passed': init_time < 5
            }
            tests.append(test_result)
            self._print_test_result(test_result)
            
            # Test 2: ChromaDB Collection
            collection_count = rag.collection.count()
            test_result = {
                'name': 'ChromaDB Documents',
                'expected': '> 0',
                'actual': collection_count,
                'passed': collection_count > 0
            }
            tests.append(test_result)
            self._print_test_result(test_result)
            
            # Test 3: Sync Functionality
            if collection_count == 0:
                self.stdout.write(Colors.YELLOW + '  ⚠️  Syncing FAQs to ChromaDB...')
                synced = rag.sync_from_database()
                test_result = {
                    'name': 'ChromaDB Sync',
                    'expected': '> 0',
                    'actual': synced,
                    'passed': synced > 0
                }
                tests.append(test_result)
                self._print_test_result(test_result)
            
        except Exception as e:
            test_result = {
                'name': 'RAG Service Error',
                'expected': 'No errors',
                'actual': str(e),
                'passed': False
            }
            tests.append(test_result)
            self._print_test_result(test_result)
        
        self.results['rag_tests'] = tests

    def test_search_functionality(self):
        """Test search functionality with real queries"""
        self.stdout.write(Colors.YELLOW + '\n🔎 Testing Search Functionality...')
        self.stdout.write('-' * 70)
        
        tests = []
        rag = get_rag_service()
        
        # Test queries in different languages
        test_queries = [
            {'query': 'Qabul qachon boshlanadi?', 'lang': 'uz', 'min_relevance': 0.5},
            {'query': 'Qanday fakultetlar mavjud?', 'lang': 'uz', 'min_relevance': 0.5},
            {'query': 'Kontrakt to\'lovi qancha?', 'lang': 'uz', 'min_relevance': 0.5},
            {'query': 'Когда начинается прием?', 'lang': 'ru', 'min_relevance': 0.5},
            {'query': 'What faculties are available?', 'lang': 'en', 'min_relevance': 0.5},
            {'query': 'Rektor kim?', 'lang': 'uz', 'min_relevance': 0.5},
        ]
        
        for test_query in test_queries:
            start_time = time.time()
            
            # Database FTS search
            db_results = rag.search_database(
                test_query['query'], 
                lang_code=test_query['lang'],
                limit=3
            )
            
            search_time = time.time() - start_time
            
            relevance = db_results[0]['relevance'] if db_results else 0
            
            test_result = {
                'name': f"Search: {test_query['query'][:30]}...",
                'expected': f"relevance ≥ {test_query['min_relevance']}",
                'actual': f"{relevance:.2f} ({search_time*1000:.0f}ms)",
                'passed': relevance >= test_query['min_relevance']
            }
            tests.append(test_result)
            self._print_test_result(test_result)
            
            if db_results and relevance >= 0.7:
                self.stdout.write(Colors.GREEN + f"    ✓ Found: {db_results[0]['question'][:50]}...")
        
        self.results['search_tests'] = tests

    def test_multilingual_support(self):
        """Test multilingual support"""
        self.stdout.write(Colors.YELLOW + '\n🌍 Testing Multilingual Support...')
        self.stdout.write('-' * 70)
        
        tests = []
        
        languages = ['uz', 'ru', 'en']
        
        for lang in languages:
            count = FAQTranslation.objects.filter(lang=lang, faq__status='published').count()
            test_result = {
                'name': f'Language: {lang.upper()}',
                'expected': '> 5',
                'actual': count,
                'passed': count > 5
            }
            tests.append(test_result)
            self._print_test_result(test_result)
        
        # Test cross-language search
        rag = get_rag_service()
        
        # Uzbek query
        uz_results = rag.search_database('Qabul', lang_code='uz', limit=3)
        # Russian query
        ru_results = rag.search_database('Прием', lang_code='ru', limit=3)
        # English query
        en_results = rag.search_database('Admission', lang_code='en', limit=3)
        
        test_result = {
            'name': 'Cross-language Search',
            'expected': 'All languages return results',
            'actual': f'uz:{len(uz_results)}, ru:{len(ru_results)}, en:{len(en_results)}',
            'passed': len(uz_results) > 0 and len(ru_results) > 0 and len(en_results) > 0
        }
        tests.append(test_result)
        self._print_test_result(test_result)
        
        self.results['search_tests'].extend(tests)

    def test_performance(self):
        """Test system performance"""
        self.stdout.write(Colors.YELLOW + '\n⚡ Testing Performance...')
        self.stdout.write('-' * 70)
        
        tests = []
        rag = get_rag_service()
        
        # Test 1: Database query speed
        queries = [
            'Qabul qachon?',
            'Fakultetlar',
            'To\'lov',
            'Aloqa',
            'Rektor'
        ]
        
        total_time = 0
        for query in queries:
            start_time = time.time()
            rag.search_database(query, lang_code='uz', limit=5)
            query_time = time.time() - start_time
            total_time += query_time
        
        avg_time = total_time / len(queries)
        
        test_result = {
            'name': 'Avg DB Query Time',
            'expected': '< 0.5s',
            'actual': f'{avg_time:.3f}s',
            'passed': avg_time < 0.5
        }
        tests.append(test_result)
        self._print_test_result(test_result)
        
        # Test 2: ChromaDB query speed
        if rag.collection.count() > 0:
            total_time = 0
            for query in queries:
                start_time = time.time()
                rag.search_chromadb(query, lang_code='uz', top_k=5)
                query_time = time.time() - start_time
                total_time += query_time
            
            avg_time = total_time / len(queries)
            
            test_result = {
                'name': 'Avg ChromaDB Query Time',
                'expected': '< 1s',
                'actual': f'{avg_time:.3f}s',
                'passed': avg_time < 1
            }
            tests.append(test_result)
            self._print_test_result(test_result)
        
        # Test 3: Full retrieval pipeline
        start_time = time.time()
        result = rag.retrieve_with_sources('Qabul qachon boshlanadi?', lang_code='uz')
        retrieval_time = time.time() - start_time
        
        test_result = {
            'name': 'Full Retrieval Pipeline',
            'expected': '< 2s',
            'actual': f'{retrieval_time:.3f}s',
            'passed': retrieval_time < 2
        }
        tests.append(test_result)
        self._print_test_result(test_result)
        
        self.results['performance_tests'] = tests

    def generate_report(self):
        """Generate comprehensive test report"""
        self.stdout.write(Colors.CYAN + '\n' + '='*70)
        self.stdout.write(Colors.CYAN + '📋 TEST SUMMARY REPORT')
        self.stdout.write(Colors.CYAN + '='*70 + '\n')
        
        all_tests = (
            self.results['database_tests'] + 
            self.results['rag_tests'] + 
            self.results['search_tests'] + 
            self.results['performance_tests']
        )
        
        total = len(all_tests)
        passed = sum(1 for t in all_tests if t['passed'])
        failed = total - passed
        success_rate = (passed / total * 100) if total > 0 else 0
        
        self.stdout.write(f"Total Tests: {total}")
        self.stdout.write(Colors.GREEN + f"Passed: {passed}")
        self.stdout.write(Colors.RED + f"Failed: {failed}")
        self.stdout.write(Colors.CYAN + f"Success Rate: {success_rate:.1f}%\n")
        
        # Category breakdown
        categories = [
            ('Database Tests', self.results['database_tests']),
            ('RAG Tests', self.results['rag_tests']),
            ('Search Tests', self.results['search_tests']),
            ('Performance Tests', self.results['performance_tests']),
        ]
        
        for cat_name, cat_tests in categories:
            if cat_tests:
                cat_passed = sum(1 for t in cat_tests if t['passed'])
                cat_total = len(cat_tests)
                cat_rate = (cat_passed / cat_total * 100) if cat_total > 0 else 0
                
                color = Colors.GREEN if cat_rate == 100 else Colors.YELLOW if cat_rate >= 80 else Colors.RED
                self.stdout.write(color + f"{cat_name}: {cat_passed}/{cat_total} ({cat_rate:.0f}%)")
        
        # Failed tests detail
        if failed > 0:
            self.stdout.write(Colors.RED + '\n❌ Failed Tests:')
            for test in all_tests:
                if not test['passed']:
                    self.stdout.write(Colors.RED + f"  • {test['name']}")
                    self.stdout.write(f"    Expected: {test['expected']}")
                    self.stdout.write(f"    Actual: {test['actual']}")
        
        # Recommendations
        self.stdout.write(Colors.CYAN + '\n💡 Recommendations:')
        
        if success_rate == 100:
            self.stdout.write(Colors.GREEN + '  ✓ All tests passed! System is working perfectly.')
        elif success_rate >= 90:
            self.stdout.write(Colors.YELLOW + '  ⚠️  Minor issues detected. Review failed tests.')
        elif success_rate >= 70:
            self.stdout.write(Colors.YELLOW + '  ⚠️  Several issues detected. Needs attention.')
        else:
            self.stdout.write(Colors.RED + '  ❌ Critical issues detected. Immediate action required.')
        
        # Save report to file
        report_file = f'/tmp/test_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timezone.now().isoformat(),
                'summary': {
                    'total': total,
                    'passed': passed,
                    'failed': failed,
                    'success_rate': success_rate
                },
                'results': self.results
            }, f, indent=2, ensure_ascii=False)
        
        self.stdout.write(Colors.CYAN + f'\n📄 Detailed report saved to: {report_file}')
        self.stdout.write(Colors.CYAN + '='*70 + '\n')

    def _print_test_result(self, test):
        """Print individual test result"""
        if test['passed']:
            self.stdout.write(
                Colors.GREEN + f"  ✓ {test['name']:.<50} " + 
                Colors.WHITE + f"{test['actual']}"
            )
        else:
            self.stdout.write(
                Colors.RED + f"  ✗ {test['name']:.<50} " + 
                Colors.WHITE + f"{test['actual']} (expected: {test['expected']})"
            )
