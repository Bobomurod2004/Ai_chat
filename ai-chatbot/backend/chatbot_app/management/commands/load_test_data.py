"""
Django Management Command: Load Test Data
Barcha modellar uchun to'liq test ma'lumotlarini yuklaydi
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from chatbot_app.models import (
    Category, FAQ, FAQTranslation, DynamicInfo, 
    Document, DocumentChunk, Conversation, Message
)
from django.contrib.postgres.search import SearchVector
import uuid


class Command(BaseCommand):
    help = 'Load comprehensive test data for all models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before loading',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('🗑️  Clearing existing data...'))
            self.clear_data()
        
        self.stdout.write(self.style.SUCCESS('📊 Loading test data...'))
        
        # Load data in order
        categories = self.load_categories()
        self.load_faqs(categories)
        self.load_dynamic_info()
        self.load_documents()
        self.load_conversations()
        
        # Update search vectors
        self.update_search_vectors()
        
        self.print_statistics()
        self.stdout.write(self.style.SUCCESS('✅ Test data loaded successfully!'))

    def clear_data(self):
        """Clear all test data"""
        Message.objects.all().delete()
        Conversation.objects.all().delete()
        DocumentChunk.objects.all().delete()
        Document.objects.all().delete()
        DynamicInfo.objects.all().delete()
        FAQTranslation.objects.all().delete()
        FAQ.objects.all().delete()
        Category.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('  ✓ Data cleared'))

    def load_categories(self):
        """Load categories"""
        self.stdout.write('📁 Loading categories...')
        
        categories_data = [
            {'name': 'Qabul', 'icon': '🎓', 'order': 1},
            {'name': 'Fakultetlar', 'icon': '🏛️', 'order': 2},
            {'name': 'To\'lov', 'icon': '💰', 'order': 3},
            {'name': 'Aloqa', 'icon': '📞', 'order': 4},
            {'name': 'Tarix', 'icon': '📜', 'order': 5},
            {'name': 'Stipendiyalar', 'icon': '🏆', 'order': 6},
            {'name': 'Rektor', 'icon': '👔', 'order': 7},
        ]
        
        categories = {}
        for cat_data in categories_data:
            cat, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'slug': slugify(cat_data['name']),
                    'icon': cat_data['icon'],
                    'order': cat_data['order']
                }
            )
            categories[cat_data['name']] = cat
            self.stdout.write(f"  ✓ {cat_data['icon']} {cat_data['name']}")
        
        return categories

    def load_faqs(self, categories):
        """Load FAQs with translations"""
        self.stdout.write('❓ Loading FAQs...')
        
        faqs_data = [
            # Qabul
            {
                'category': 'Qabul',
                'order': 1,
                'translations': {
                    'uz': {
                        'question': 'Qabul qachon boshlanadi?',
                        'answer': 'Qabul har yili iyul oyining 15-kunidan boshlanadi va avgust oyining 30-kunigacha davom etadi. Aniq sanalar uchun rasmiy veb-saytimizni kuzatib boring.',
                        'variants': ['qabul sanalari', 'qachon qabul', 'qabul muddati']
                    },
                    'ru': {
                        'question': 'Когда начинается прием?',
                        'answer': 'Прием начинается 15 июля каждого года и продолжается до 30 августа. Следите за точными датами на нашем официальном сайте.',
                        'variants': ['даты приема', 'когда прием', 'срок приема']
                    },
                    'en': {
                        'question': 'When does admission start?',
                        'answer': 'Admission starts on July 15th every year and continues until August 30th. Follow our official website for exact dates.',
                        'variants': ['admission dates', 'when admission', 'admission period']
                    }
                }
            },
            {
                'category': 'Qabul',
                'order': 2,
                'translations': {
                    'uz': {
                        'question': 'Qabul uchun qanday hujjatlar kerak?',
                        'answer': 'Qabul uchun quyidagi hujjatlar talab qilinadi: 1) Pasport nusxasi, 2) Diplom yoki attestat, 3) 3x4 o\'lchamdagi 6 dona fotosurat, 4) Tibbiy ma\'lumotnoma (086-shakl), 5) Abituriyent anketi.',
                        'variants': ['kerakli hujjatlar', 'qanday hujjatlar', 'hujjatlar ro\'yxati']
                    },
                    'ru': {
                        'question': 'Какие документы нужны для поступления?',
                        'answer': 'Для поступления требуются следующие документы: 1) Копия паспорта, 2) Диплом или аттестат, 3) 6 фотографий размером 3x4, 4) Медицинская справка (форма 086), 5) Анкета абитуриента.',
                        'variants': ['необходимые документы', 'какие документы', 'список документов']
                    },
                    'en': {
                        'question': 'What documents are required for admission?',
                        'answer': 'The following documents are required for admission: 1) Passport copy, 2) Diploma or certificate, 3) 6 photos 3x4 size, 4) Medical certificate (form 086), 5) Applicant questionnaire.',
                        'variants': ['required documents', 'what documents', 'document list']
                    }
                }
            },
            {
                'category': 'Qabul',
                'order': 3,
                'translations': {
                    'uz': {
                        'question': 'Minimal ball nechta?',
                        'answer': 'Minimal qabul bali yo\'nalishga qarab farq qiladi. Odatda 56.7 balldan boshlanadi. Aniq ma\'lumot uchun qabul komissiyasiga murojaat qiling.',
                        'variants': ['minimal ball', 'qancha ball kerak', 'o\'tish bali']
                    },
                    'ru': {
                        'question': 'Какой минимальный балл?',
                        'answer': 'Минимальный проходной балл зависит от направления. Обычно начинается с 56.7 баллов. Для точной информации обратитесь в приемную комиссию.',
                        'variants': ['минимальный балл', 'сколько баллов нужно', 'проходной балл']
                    },
                    'en': {
                        'question': 'What is the minimum score?',
                        'answer': 'The minimum passing score depends on the direction. Usually starts from 56.7 points. Contact the admissions office for accurate information.',
                        'variants': ['minimum score', 'how many points needed', 'passing score']
                    }
                }
            },
            
            # Fakultetlar
            {
                'category': 'Fakultetlar',
                'order': 1,
                'translations': {
                    'uz': {
                        'question': 'Qanday fakultetlar mavjud?',
                        'answer': 'Universitetda quyidagi fakultetlar mavjud: 1) Ingliz tili fakulteti, 2) Nemis tili fakulteti, 3) Fransuz tili fakulteti, 4) Xitoy tili fakulteti, 5) Rus tili fakulteti, 6) Tarjimashunoslik fakulteti.',
                        'variants': ['fakultetlar ro\'yxati', 'qanday fakultetlar', 'fakultetlar haqida']
                    },
                    'ru': {
                        'question': 'Какие факультеты есть?',
                        'answer': 'В университете есть следующие факультеты: 1) Факультет английского языка, 2) Факультет немецкого языка, 3) Факультет французского языка, 4) Факультет китайского языка, 5) Факультет русского языка, 6) Факультет переводоведения.',
                        'variants': ['список факультетов', 'какие факультеты', 'о факультетах']
                    },
                    'en': {
                        'question': 'What faculties are available?',
                        'answer': 'The university has the following faculties: 1) Faculty of English, 2) Faculty of German, 3) Faculty of French, 4) Faculty of Chinese, 5) Faculty of Russian, 6) Faculty of Translation Studies.',
                        'variants': ['faculty list', 'what faculties', 'about faculties']
                    }
                }
            },
            
            # To'lov
            {
                'category': 'To\'lov',
                'order': 1,
                'translations': {
                    'uz': {
                        'question': 'Kontrakt to\'lovi qancha?',
                        'answer': 'Kontrakt to\'lovi yo\'nalishga qarab farq qiladi. 2024-2025 o\'quv yili uchun yillik to\'lov 8,000,000 so\'mdan 15,000,000 so\'mgacha. Aniq narxlar uchun qabul komissiyasiga murojaat qiling.',
                        'variants': ['kontrakt narxi', 'to\'lov summasi', 'qancha to\'lash kerak']
                    },
                    'ru': {
                        'question': 'Сколько стоит контракт?',
                        'answer': 'Стоимость контракта зависит от направления. На 2024-2025 учебный год годовая плата составляет от 8,000,000 до 15,000,000 сумов. Для точных цен обратитесь в приемную комиссию.',
                        'variants': ['цена контракта', 'сумма оплаты', 'сколько платить']
                    },
                    'en': {
                        'question': 'How much is the contract fee?',
                        'answer': 'Contract fees vary by direction. For the 2024-2025 academic year, annual fees range from 8,000,000 to 15,000,000 soums. Contact the admissions office for exact prices.',
                        'variants': ['contract price', 'payment amount', 'how much to pay']
                    }
                }
            },
            
            # Aloqa
            {
                'category': 'Aloqa',
                'order': 1,
                'translations': {
                    'uz': {
                        'question': 'Universitet bilan qanday bog\'lanish mumkin?',
                        'answer': 'Universitet bilan quyidagi yo\'llar orqali bog\'lanishingiz mumkin:\nTelefon: +998 71 230 12 87\nEmail: info@uzswlu.uz\nManzil: Toshkent sh., G\'afur G\'ulom ko\'chasi, 21-uy\nIsh vaqti: Dushanba-Juma 9:00-18:00',
                        'variants': ['telefon raqami', 'email manzil', 'qanday bog\'lanish']
                    },
                    'ru': {
                        'question': 'Как связаться с университетом?',
                        'answer': 'Вы можете связаться с университетом следующими способами:\nТелефон: +998 71 230 12 87\nEmail: info@uzswlu.uz\nАдрес: г. Ташкент, ул. Гафура Гуляма, 21\nРабочее время: Понедельник-Пятница 9:00-18:00',
                        'variants': ['номер телефона', 'email адрес', 'как связаться']
                    },
                    'en': {
                        'question': 'How to contact the university?',
                        'answer': 'You can contact the university through:\nPhone: +998 71 230 12 87\nEmail: info@uzswlu.uz\nAddress: Tashkent, Gafur Gulom Street, 21\nWorking hours: Monday-Friday 9:00-18:00',
                        'variants': ['phone number', 'email address', 'how to contact']
                    }
                }
            },
            
            # Tarix
            {
                'category': 'Tarix',
                'order': 1,
                'translations': {
                    'uz': {
                        'question': 'Universitet qachon tashkil etilgan?',
                        'answer': 'O\'zbekiston Davlat Jahon Tillari Universiteti 1992-yil 23-iyunda tashkil etilgan. 30 yildan ortiq vaqt davomida universitet minglab malakali mutaxassislarni tayyorlab kelmoqda.',
                        'variants': ['universitet tarixi', 'qachon ochilgan', 'tashkil topgan yili']
                    },
                    'ru': {
                        'question': 'Когда был основан университет?',
                        'answer': 'Узбекский государственный университет мировых языков был основан 23 июня 1992 года. Более 30 лет университет готовит тысячи квалифицированных специалистов.',
                        'variants': ['история университета', 'когда открылся', 'год основания']
                    },
                    'en': {
                        'question': 'When was the university founded?',
                        'answer': 'Uzbekistan State World Languages University was founded on June 23, 1992. For over 30 years, the university has been training thousands of qualified specialists.',
                        'variants': ['university history', 'when opened', 'founding year']
                    }
                }
            },
            
            # Stipendiyalar
            {
                'category': 'Stipendiyalar',
                'order': 1,
                'translations': {
                    'uz': {
                        'question': 'Stipendiya olish mumkinmi?',
                        'answer': 'Ha, a\'lo o\'quvchilar uchun stipendiya mavjud. Davlat granti asosida o\'qiyotgan talabalar oylik stipendiya olishadi. Shuningdek, maxsus stipendiyalar va grantlar ham mavjud.',
                        'variants': ['stipendiya haqida', 'stipendiya olish', 'grant']
                    },
                    'ru': {
                        'question': 'Можно ли получить стипендию?',
                        'answer': 'Да, для отличников доступна стипендия. Студенты, обучающиеся на основе государственного гранта, получают ежемесячную стипендию. Также доступны специальные стипендии и гранты.',
                        'variants': ['о стипендии', 'получить стипендию', 'грант']
                    },
                    'en': {
                        'question': 'Can I get a scholarship?',
                        'answer': 'Yes, scholarships are available for excellent students. Students studying on a state grant basis receive monthly scholarships. Special scholarships and grants are also available.',
                        'variants': ['about scholarship', 'get scholarship', 'grant']
                    }
                }
            },
            
            # Rektor
            {
                'category': 'Rektor',
                'order': 1,
                'translations': {
                    'uz': {
                        'question': 'Rektor kim?',
                        'answer': 'Universitet rektori - professor Irisqulov Azamat Turgunovich. U 2018-yildan buyon universitetga rahbarlik qilmoqda. Ilmiy darajasi: filologiya fanlari doktori.',
                        'variants': ['rektor haqida', 'rektor ismi', 'kim rektor']
                    },
                    'ru': {
                        'question': 'Кто ректор?',
                        'answer': 'Ректор университета - профессор Ирискулов Азамат Тургунович. Он руководит университетом с 2018 года. Ученая степень: доктор филологических наук.',
                        'variants': ['о ректоре', 'имя ректора', 'кто ректор']
                    },
                    'en': {
                        'question': 'Who is the rector?',
                        'answer': 'The rector of the university is Professor Irisqulov Azamat Turgunovich. He has been leading the university since 2018. Academic degree: Doctor of Philology.',
                        'variants': ['about rector', 'rector name', 'who is rector']
                    }
                }
            },
        ]
        
        for faq_data in faqs_data:
            faq = FAQ.objects.create(
                category=categories[faq_data['category']],
                order=faq_data['order'],
                status='published'
            )
            
            for lang, trans_data in faq_data['translations'].items():
                FAQTranslation.objects.create(
                    faq=faq,
                    lang=lang,
                    question=trans_data['question'],
                    answer=trans_data['answer'],
                    question_variants=trans_data.get('variants', [])
                )
            
            self.stdout.write(f"  ✓ FAQ: {faq_data['translations']['uz']['question'][:50]}...")

    def load_dynamic_info(self):
        """Load dynamic information"""
        self.stdout.write('🔄 Loading dynamic info...')
        
        dynamic_data = [
            {'key': 'admission_start_date', 'value': '2024-07-15', 'description': 'Qabul boshlanish sanasi'},
            {'key': 'admission_end_date', 'value': '2024-08-30', 'description': 'Qabul tugash sanasi'},
            {'key': 'contract_price_min', 'value': '8000000', 'description': 'Minimal kontrakt to\'lovi'},
            {'key': 'contract_price_max', 'value': '15000000', 'description': 'Maksimal kontrakt to\'lovi'},
            {'key': 'phone_main', 'value': '+998 71 230 12 87', 'description': 'Asosiy telefon'},
            {'key': 'phone_admission', 'value': '+998 71 230 12 88', 'description': 'Qabul telefoni'},
            {'key': 'email_main', 'value': 'info@uzswlu.uz', 'description': 'Asosiy email'},
            {'key': 'email_admission', 'value': 'admission@uzswlu.uz', 'description': 'Qabul email'},
            {'key': 'address', 'value': 'Toshkent sh., G\'afur G\'ulom ko\'chasi, 21', 'description': 'Manzil'},
            {'key': 'working_hours', 'value': 'Dushanba-Juma 9:00-18:00', 'description': 'Ish vaqti'},
            {'key': 'rector_name', 'value': 'Irisqulov Azamat Turgunovich', 'description': 'Rektor ismi'},
            {'key': 'founded_year', 'value': '1992', 'description': 'Tashkil topgan yil'},
            {'key': 'student_count', 'value': '5000', 'description': 'Talabalar soni'},
            {'key': 'faculty_count', 'value': '6', 'description': 'Fakultetlar soni'},
            {'key': 'minimum_score', 'value': '56.7', 'description': 'Minimal qabul bali'},
        ]
        
        for data in dynamic_data:
            DynamicInfo.objects.get_or_create(
                key=data['key'],
                defaults={
                    'value': data['value'],
                    'description': data['description']
                }
            )
            self.stdout.write(f"  ✓ {data['key']}: {data['value']}")

    def load_documents(self):
        """Load sample documents"""
        self.stdout.write('📄 Loading documents...')
        
        docs_data = [
            {
                'title': 'Qabul qoidalari 2024',
                'source_type': 'pdf',
                'status': 'ready',
                'chunks': [
                    'Qabul qoidalari 2024-yil uchun. Qabul iyul oyining 15-kunidan boshlanadi.',
                    'Hujjatlar: pasport, diplom, fotosurat, tibbiy ma\'lumotnoma.',
                    'Minimal ball 56.7 dan boshlanadi. Yo\'nalishga qarab farq qiladi.'
                ]
            },
            {
                'title': 'Fakultetlar ro\'yxati',
                'source_type': 'html',
                'status': 'ready',
                'chunks': [
                    'Ingliz tili fakulteti - eng katta fakultet, 1500 talaba.',
                    'Nemis tili fakulteti - 800 talaba, yuqori malakali o\'qituvchilar.',
                    'Fransuz tili fakulteti - 600 talaba, zamonaviy laboratoriyalar.'
                ]
            },
            {
                'title': 'Universitet tarixi',
                'source_type': 'text',
                'status': 'ready',
                'chunks': [
                    'UzSWLU 1992-yil 23-iyunda tashkil etilgan.',
                    '30 yildan ortiq tajriba, minglab bitiruvchilar.',
                    'Xalqaro hamkorlik: 50+ universitet bilan shartnomalar.'
                ]
            },
        ]
        
        for doc_data in docs_data:
            doc = Document.objects.create(
                title=doc_data['title'],
                source_type=doc_data['source_type'],
                status=doc_data['status']
            )
            
            for idx, chunk_text in enumerate(doc_data['chunks']):
                DocumentChunk.objects.create(
                    document=doc,
                    chunk_text=chunk_text,
                    chunk_index=idx,
                    lang='uz',
                    embedding_id=f"doc_{doc.id}_chunk_{idx}"
                )
            
            self.stdout.write(f"  ✓ {doc_data['title']} ({len(doc_data['chunks'])} chunks)")

    def load_conversations(self):
        """Load sample conversations"""
        self.stdout.write('💬 Loading conversations...')
        
        conversations_data = [
            {
                'user_id': 'test_user_1',
                'messages': [
                    {'sender': 'user', 'text': 'Salom', 'lang': 'uz'},
                    {'sender': 'bot', 'text': 'Assalomu alaykum! Sizga qanday yordam bera olaman?', 'lang': 'uz'},
                    {'sender': 'user', 'text': 'Qabul qachon boshlanadi?', 'lang': 'uz'},
                    {'sender': 'bot', 'text': 'Qabul har yili iyul oyining 15-kunidan boshlanadi.', 'lang': 'uz'},
                ]
            },
            {
                'user_id': 'test_user_2',
                'messages': [
                    {'sender': 'user', 'text': 'Hello', 'lang': 'en'},
                    {'sender': 'bot', 'text': 'Hello! How can I help you?', 'lang': 'en'},
                    {'sender': 'user', 'text': 'What faculties do you have?', 'lang': 'en'},
                    {'sender': 'bot', 'text': 'We have 6 faculties: English, German, French, Chinese, Russian, and Translation Studies.', 'lang': 'en'},
                ]
            },
            {
                'user_id': 'test_user_3',
                'messages': [
                    {'sender': 'user', 'text': 'Здравствуйте', 'lang': 'ru'},
                    {'sender': 'bot', 'text': 'Здравствуйте! Чем могу помочь?', 'lang': 'ru'},
                    {'sender': 'user', 'text': 'Сколько стоит контракт?', 'lang': 'ru'},
                    {'sender': 'bot', 'text': 'Стоимость контракта от 8,000,000 до 15,000,000 сумов.', 'lang': 'ru'},
                ]
            },
        ]
        
        for conv_data in conversations_data:
            conv = Conversation.objects.create(
                user_id=conv_data['user_id'],
                platform='web'
            )
            
            for msg_data in conv_data['messages']:
                Message.objects.create(
                    conversation=conv,
                    sender_type=msg_data['sender'],
                    text=msg_data['text'],
                    lang=msg_data['lang']
                )
            
            self.stdout.write(f"  ✓ Conversation: {conv_data['user_id']} ({len(conv_data['messages'])} messages)")

    def update_search_vectors(self):
        """Update PostgreSQL search vectors"""
        self.stdout.write('🔍 Updating search vectors...')
        
        from chatbot_app.models import FAQTranslation
        
        translations = FAQTranslation.objects.all()
        for trans in translations:
            trans.question_tsv = SearchVector('question', config='simple')
            trans.answer_tsv = SearchVector('answer', config='simple')
            trans.save(update_fields=['question_tsv', 'answer_tsv'])
        
        self.stdout.write(f"  ✓ Updated {translations.count()} search vectors")

    def print_statistics(self):
        """Print database statistics"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📊 DATABASE STATISTICS'))
        self.stdout.write('='*60)
        
        stats = [
            ('Categories', Category.objects.count()),
            ('FAQs', FAQ.objects.count()),
            ('FAQ Translations', FAQTranslation.objects.count()),
            ('Dynamic Info', DynamicInfo.objects.count()),
            ('Documents', Document.objects.count()),
            ('Document Chunks', DocumentChunk.objects.count()),
            ('Conversations', Conversation.objects.count()),
            ('Messages', Message.objects.count()),
        ]
        
        for name, count in stats:
            self.stdout.write(f"  {name:.<30} {count:>5}")
        
        self.stdout.write('='*60 + '\n')
