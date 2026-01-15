import os
import django
import uuid
from django.core.management.base import BaseCommand
from chatbot_app.models import Category, FAQ, FAQTranslation
from django.contrib.postgres.search import SearchVector

class Command(BaseCommand):
    help = 'Seed UzSWLU official data and greetings'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding UzSWLU data...")

        # 1. Clear existing FAQs and Categories to ensure a fresh, clean start
        FAQTranslation.objects.all().delete()
        FAQ.objects.all().delete()
        Category.objects.all().delete()

        # 2. Categories
        cats = {
            'general': Category.objects.create(name="General", slug="general", icon="👋"),
            'history': Category.objects.create(name="History", slug="history", icon="🏛️"),
            'rectorate': Category.objects.create(name="Rectorate", slug="rectorate", icon="👨‍🏫"),
            'faculties': Category.objects.create(name="Faculties", slug="faculties", icon="🎓"),
            'admission': Category.objects.create(name="Admission", slug="admission", icon="📝"),
            'contact': Category.objects.create(name="Contact", slug="contact", icon="📞"),
        }

        # 3. FAQ Data Structure
        data = [
            # --- GREETINGS / SMALL TALK ---
            {
                'category': cats['general'],
                'translations': {
                    'uz': {'q': 'Salom', 'a': 'Assalomu alaykum! Men UzSWLU AI asistentiman. Sizga qanday yordam bera olaman?'},
                    'ru': {'q': 'Привет', 'a': 'Здравствуйте! Я AI-ассистент УзГУМЯ. Чем я могу вам помочь?'},
                    'en': {'q': 'Hello', 'a': 'Hello! I am the UzSWLU AI assistant. How can I help you today?'},
                }
            },
            {
                'category': cats['general'],
                'translations': {
                    'uz': {'q': 'Qale / Qandaysiz', 'a': 'Rahmat, yaxshiman! Sizga universitet haqida qanday ma\'lumot kerak?'},
                    'ru': {'q': 'Как дела / Как ты', 'a': 'Спасибо, у меня все хорошо! Какая информация об университете вам нужна?'},
                    'en': {'q': 'How are you', 'a': 'I am doing well, thank you! What information about the university do you need?'},
                }
            },
            # --- HISTORY ---
            {
                'category': cats['history'],
                'translations': {
                    'uz': {
                        'q': 'Universitet tarixi haqida gapirib bering',
                        'a': "Universitet 1948-yilda Toshkent davlat chet tillar pedagogika instituti sifatida tashkil etilgan. 1992-yil 12-mayda O'zbekiston Respublikasi Prezidentining Farmoni bilan Toshkent davlat chet tillar pedagogika instituti va Respublika rus tili va adabiyoti instituti negizida O'zbekiston davlat jahon tillari universiteti (UzSWLU) tashkil etildi."
                    },
                    'ru': {
                        'q': 'Расскажите об истории университета',
                        'a': "Университет был основан в 1948 году как Ташкентский государственный педагогический институт иностранных языков. 12 мая 1992 года Указом Президента Республики Узбекистан на базе этого института и Республиканского института русского языка и литературы был создан Узбекский государственный университет мировых языков."
                    },
                    'en': {
                        'q': 'Tell me about the university history',
                        'a': "The university was founded in 1948 as the Tashkent State Pedagogical Institute of Foreign Languages. On May 12, 1992, by the Decree of the President of the Republic of Uzbekistan, the Uzbekistan State World Languages University was established on the basis of the Pedagogical Institute of Foreign Languages and the Republican Institute of Russian Language and Literature."
                    },
                }
            },
            # --- RECTOR ---
            {
                'category': cats['rectorate'],
                'translations': {
                    'uz': {
                        'q': 'Universitet rektori kim?',
                        'a': "Hozirgi vaqtda UzSWLU rektori - Tuxtasinov Ilxomjon Madaminovich. Qabul vaqti: Dushanba kuni, 15:00 - 17:00. Bog'lanish: +998 (71) 230-12-91, rector@uzswlu.uz"
                    },
                    'ru': {
                        'q': 'Кто ректор университета?',
                        'a': "В настоящее время ректором УзГУМЯ является Тухтасинов Илхомжон Мадаминович. Часы приема: Понедельник, 15:00 - 17:00. Контакты: +998 (71) 230-12-91, rector@uzswlu.uz"
                    },
                    'en': {
                        'q': 'Who is the rector of the university?',
                        'a': "The current rector of UzSWLU is Tuxtasinov Ilxomjon Madaminovich. Reception hours: Monday, 15:00 - 17:00. Contact: +998 (71) 230-12-91, rector@uzswlu.uz"
                    },
                }
            },
            # --- FACULTIES ---
            {
                'category': cats['faculties'],
                'translations': {
                    'uz': {
                        'q': 'Universitetda qanday fakultetlar bor?',
                        'a': "UzSWLUda 11 ta fakultet mavjud: Ingliz filologiyasi, 1-Ingliz tili, 2-Ingliz tili, 3-Ingliz tili, Roman-german filologiyasi, Rus filologiyasi, Tarjima fakulteti, Sharq filologiyasi, Xalqaro jurnalistika, Sirtqi va kechki ta'lim, hamda Qo'shma ta'lim dasturlari bo'limi."
                    },
                    'ru': {
                        'q': 'Какие факультеты есть в университете?',
                        'a': "В УзГУМЯ имеется 11 факультетов: Английской филологии, 1-й английский, 2-й английский, 3-й английский, Романо-германской филологии, Русской филологии, Переводческий, Восточной филологии, Международной журналистики, Заочного и вечернего обучения, а также Отдел координации совместных образовательных программ."
                    },
                    'en': {
                        'q': 'What faculties are there in the university?',
                        'a': "UzSWLU has 11 faculties: English Philology, 1st English, 2nd English, 3rd English, Romano-germanic Philology, Russian Philology, Translation, Oriental Philology, International Journalism, Correspondence and Evening Education, and Joint Educational Programs department."
                    },
                }
            },
            # --- ADMISSION ---
            {
                'category': cats['admission'],
                'translations': {
                    'uz': {
                        'q': 'Qabul 2025 haqida ma\'lumot',
                        'a': "2025/2026 o'quv yili uchun qabul bo'yicha batafsil ma'lumotlar, ijodiy imtihonlar dasturi va o'tgan yillardagi o'tish ballari uzswlu.uz saytining 'Qabul 2025' bo'limida keltirilgan."
                    },
                    'ru': {
                        'q': 'Информация о приеме 2025',
                        'a': "Подробная информация о приеме на 2025/2026 учебный год, программы творческих экзаменов и проходные баллы прошлых лет доступны в разделе 'Прием 2025' на сайте uzswlu.uz."
                    },
                    'en': {
                        'q': 'Admission 2025 information',
                        'a': "Detailed information about admission for the 2025/2026 academic year, creative exam programs, and previous years' passing scores are available in the 'Admission 2025' section on uzswlu.uz."
                    },
                }
            },
            # --- CONTACT ---
            {
                'category': cats['contact'],
                'translations': {
                    'uz': {
                        'q': 'Universitet bilan qanday bog\'lansa bo\'ladi?',
                        'a': "Manzil: Toshkent sh., Uchtepa tumani, Kichik halqa yo'li, 21-uy. Ishonch telefoni: +998 (71) 230-12-91. Email: uzdjtu@uzswlu.uz. Telegram: @UzSWLU."
                    },
                    'ru': {
                        'q': 'Как связаться с университетом?',
                        'a': "Адрес: г. Ташкент, Учтепинский район, ул. Кичик халка йули, 21. Горячая линия: +998 (71) 230-12-91. Email: uzdjtu@uzswlu.uz. Telegram: @UzSWLU."
                    },
                    'en': {
                        'q': 'How to contact the university?',
                        'a': "Address: 21, Kichik halqa yo'li str., Uchtepa district, Tashkent. Hotline: +998 (71) 230-12-91. Email: uzdjtu@uzswlu.uz. Telegram: @UzSWLU."
                    },
                }
            },
        ]

        # 4. Create Records
        for item in data:
            faq = FAQ.objects.create(
                category=item['category'], 
                status='published',
                canonical_id=uuid.uuid4()
            )
            for lang, content in item['translations'].items():
                FAQTranslation.objects.create(
                    faq=faq,
                    lang=lang,
                    question=content['q'],
                    answer=content['a'],
                    question_variants=[], # Required field
                    short_answer="",      # Required field
                    embedding_id=str(uuid.uuid4()) # Placeholder for now
                )

        # 5. Populate Search Vector (search_tsv) with weights
        from django.contrib.postgres.search import SearchVector
        for trans in FAQTranslation.objects.all():
            trans.search_tsv = SearchVector('question', weight='A') + SearchVector('answer', weight='B')
            trans.save()

        # 6. Automatic Sync to ChromaDB
        try:
            from rag_service import get_rag_service
            rag = get_rag_service()
            rag.sync_from_database()
            self.stdout.write(self.style.SUCCESS('Successfully synced to ChromaDB!'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Sync to ChromaDB failed: {e}'))

        self.stdout.write(self.style.SUCCESS('Successfully seeded UzSWLU data!'))
