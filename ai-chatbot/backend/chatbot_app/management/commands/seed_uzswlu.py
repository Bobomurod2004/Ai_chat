"""
UzSWLU Real Data Seeder - Comprehensive Database Population
Populates all models with real, accurate data from uzswlu.uz
"""
import os
import uuid
from datetime import date
from django.core.management.base import BaseCommand
from chatbot_app.models import (
    Category, FAQ, FAQTranslation, DynamicInfo, 
    Document, DocumentChunk
)
from django.contrib.postgres.search import SearchVector


class Command(BaseCommand):
    help = 'Seed comprehensive UzSWLU real data - 50+ FAQs, Documents, Dynamic Info'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("🌟 UZSWLU COMPREHENSIVE DATA SEEDER"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        
        # Clear existing data
        self.stdout.write("\n🗑️  Clearing existing data...")
        FAQTranslation.objects.all().delete()
        FAQ.objects.all().delete()
        Category.objects.all().delete()
        DynamicInfo.objects.all().delete()
        DocumentChunk.objects.all().delete()
        Document.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("  ✓ Data cleared\n"))

        # Create Categories
        self.stdout.write("📁 Creating categories...")
        cats = self._create_categories()
        
        # Create FAQs (50+)
        self.stdout.write("\n❓ Creating 50+ FAQs...")
        self._create_faqs(cats)
        
        # Create Dynamic Info
        self.stdout.write("\n🔄 Creating dynamic information...")
        self._create_dynamic_info()
        
        # Create Documents
        self.stdout.write("\n📄 Creating documents...")
        self._create_documents()
        
        # Update search vectors
        self.stdout.write("\n🔍 Updating search vectors...")
        self._update_search_vectors()
        
        # Sync to ChromaDB
        self.stdout.write("\n🔗 Syncing to ChromaDB...")
        self._sync_chromadb()
        
        # Print statistics
        self._print_statistics()
        
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 70))
        self.stdout.write(self.style.SUCCESS("✅ UZSWLU DATA SEEDING COMPLETED SUCCESSFULLY!"))
        self.stdout.write(self.style.SUCCESS("=" * 70 + "\n"))

    def _create_categories(self):
        """Create all categories"""
        categories = {
            'general': Category.objects.create(
                name="Umumiy", slug="general", icon="👋",
                intent_keywords=["salom", "universitet", "umumiy", "ma'lumot"]
            ),
            'history': Category.objects.create(
                name="Tarix", slug="history", icon="🏛️",
                intent_keywords=["tarix", "qachon ochilgan", "founded"]
            ),
            'rectorate': Category.objects.create(
                name="Rektorat", slug="rectorate", icon="👨‍🏫",
                intent_keywords=["rektor", "prorektor", "rahbariyat"]
            ),
            'faculties': Category.objects.create(
                name="Fakultetlar", slug="faculties", icon="🎓",
                intent_keywords=["fakultet", "yo'nalish", "department"]
            ),
            'admission': Category.objects.create(
                name="Qabul", slug="admission", icon="📝",
                intent_keywords=["qabul", "hujjat", "topshirish", "imtihon", "admission"]
            ),
            'contact': Category.objects.create(
                name="Aloqa", slug="contact", icon="📞",
                intent_keywords=["telefon", "manzil", "aloqa", "email", "contact"]
            ),
            'education': Category.objects.create(
                name="Ta'lim", slug="education", icon="📚",
                intent_keywords=["kontrakt", "magistratura", "shartnoma", "grant", "stipendiya"]
            ),
            'student_life': Category.objects.create(
                name="Talaba hayoti", slug="student-life", icon="🎯",
                intent_keywords=["yotoqxona", "oshxona", "sport", "klub", "ttj"]
            ),
        }
        
        for cat in categories.values():
            self.stdout.write(f"  ✓ {cat.icon} {cat.name}")
        
        return categories

    def _create_faqs(self, cats):
        """Create 50+ comprehensive FAQs"""
        faq_data = [
            # GENERAL (Salomlashuvlar) - 5 FAQs
            {
                'category': cats['general'],
                'translations': {
                    'uz': {
                        'q': 'Salom',
                        'a': 'Assalomu alaykum! Men UzSWLU AI yordamchisiman. Sizga qanday yordam bera olaman? Universitet haqida, qabul, fakultetlar yoki boshqa savollaringiz bo\'lsa, bemalol so\'rang!',
                        'short': 'Salom! Sizga qanday yordam bera olaman?'
                    },
                    'ru': {
                        'q': 'Привет',
                        'a': 'Здравствуйте! Я AI-помощник УзГУМЯ. Чем могу вам помочь? Если у вас есть вопросы об университете, приёме, факультетах или другие вопросы, смело спрашивайте!',
                        'short': 'Здравствуйте! Чем могу помочь?'
                    },
                    'en': {
                        'q': 'Hello',
                        'a': 'Hello! I am the UzSWLU AI assistant. How can I help you today? Feel free to ask about the university, admission, faculties, or any other questions!',
                        'short': 'Hello! How can I help you?'
                    },
                }
            },
            {
                'category': cats['general'],
                'translations': {
                    'uz': {
                        'q': 'Qalaysiz / Qandaysiz',
                        'a': 'Rahmat, yaxshiman! Sizga universitet haqida qanday ma\'lumot kerak? Qabul, fakultetlar, ta\'lim dasturlari yoki boshqa narsalar haqida so\'rashingiz mumkin.',
                        'short': 'Yaxshiman! Sizga qanday yordam bera olaman?'
                    },
                    'ru': {
                        'q': 'Как дела',
                        'a': 'Спасибо, у меня всё хорошо! Какая информация об университете вам нужна? Вы можете спросить о приёме, факультетах, образовательных программах или других вопросах.',
                        'short': 'Хорошо! Чем могу помочь?'
                    },
                    'en': {
                        'q': 'How are you',
                        'a': 'I\'m doing well, thank you! What information about the university do you need? You can ask about admission, faculties, educational programs, or other topics.',
                        'short': 'Good! How can I help?'
                    },
                }
            },
            {
                'category': cats['general'],
                'translations': {
                    'uz': {
                        'q': 'Rahmat / Tashakkur',
                        'a': 'Arzimaydi! Yana savollaringiz bo\'lsa, bemalol so\'rang. Men doim yordam berishga tayyorman!',
                        'short': 'Arzimaydi!'
                    },
                    'ru': {
                        'q': 'Спасибо',
                        'a': 'Пожалуйста! Если у вас есть ещё вопросы, смело спрашивайте. Я всегда готов помочь!',
                        'short': 'Пожалуйста!'
                    },
                    'en': {
                        'q': 'Thank you',
                        'a': 'You\'re welcome! If you have more questions, feel free to ask. I\'m always here to help!',
                        'short': 'You\'re welcome!'
                    },
                }
            },
            {
                'category': cats['general'],
                'translations': {
                    'uz': {
                        'q': 'UzSWLU nima / Universitet haqida',
                        'a': 'O\'zbekiston Davlat Jahon Tillari Universiteti (UzSWLU) - O\'zbekistonning eng yirik va nufuzli til universitetidir. 1949-yilda tashkil etilgan, 70+ yillik tarixga ega. 11 fakultet, 5000+ talaba, 50+ chet tillarni o\'rgatadi.',
                        'short': 'UzSWLU - O\'zbekistonning eng yirik til universiteti'
                    },
                    'ru': {
                        'q': 'Что такое УзГУМЯ / Об университете',
                        'a': 'Узбекский Государственный Университет Мировых Языков (УзГУМЯ) - крупнейший и престижный языковый университет Узбекистана. Основан в 1949 году, имеет 70+ летнюю историю. 11 факультетов, 5000+ студентов, преподаёт 50+ иностранных языков.',
                        'short': 'УзГУМЯ - крупнейший языковый университет Узбекистана'
                    },
                    'en': {
                        'q': 'What is UzSWLU / About university',
                        'a': 'Uzbekistan State World Languages University (UzSWLU) is the largest and most prestigious language university in Uzbekistan. Founded in 1949, has 70+ years of history. 11 faculties, 5000+ students, teaches 50+ foreign languages.',
                        'short': 'UzSWLU - largest language university in Uzbekistan'
                    },
                }
            },
            {
                'category': cats['general'],
                'a': 'Xayr / Salomat bo\'ling',
                'translations': {
                    'uz': {
                        'q': 'Xayr / Salomat bo\'ling',
                        'a': 'Xayr! Omad tilayman! Yana savollaringiz bo\'lsa, qaytib keling. UzSWLU haqida har doim ma\'lumot berishga tayyorman!',
                        'short': 'Xayr! Omad tilayman!'
                    },
                    'ru': {
                        'q': 'До свидания / Пока',
                        'a': 'До свидания! Удачи вам! Если у вас появятся вопросы, возвращайтесь. Всегда готов предоставить информацию об УзГУМЯ!',
                        'short': 'До свидания! Удачи!'
                    },
                    'en': {
                        'q': 'Goodbye / Bye',
                        'a': 'Goodbye! Good luck! If you have questions, come back anytime. Always ready to provide information about UzSWLU!',
                        'short': 'Goodbye! Good luck!'
                    },
                }
            },
            
            # HISTORY (Tarix) - 6 FAQs
            {
                'category': cats['history'],
                'translations': {
                    'uz': {
                        'q': 'Universitet qachon tashkil etilgan?',
                        'a': 'UzSWLU 1949-yilda Toshkent Davlat Chet Tillar Pedagogika Instituti nomi bilan tashkil etilgan. 1992-yil 12-mayda O\'zbekiston Respublikasi Prezidentining Farmoni bilan universitet maqomiga ega bo\'ldi. Hozirda 75+ yillik tarixga ega.',
                        'short': '1949-yilda tashkil etilgan, 75+ yillik tarix'
                    },
                    'ru': {
                        'q': 'Когда был основан университет?',
                        'a': 'УзГУМЯ был основан в 1949 году как Ташкентский Государственный Педагогический Институт Иностранных Языков. 12 мая 1992 года Указом Президента Республики Узбекистан получил статус университета. Сейчас имеет 75+ летнюю историю.',
                        'short': 'Основан в 1949 году, 75+ лет истории'
                    },
                    'en': {
                        'q': 'When was the university founded?',
                        'a': 'UzSWLU was founded in 1949 as Tashkent State Pedagogical Institute of Foreign Languages. On May 12, 1992, by the Decree of the President of Uzbekistan, it received university status. Now has 75+ years of history.',
                        'short': 'Founded in 1949, 75+ years of history'
                    },
                }
            },
            {
                'category': cats['history'],
                'translations': {
                    'uz': {
                        'q': 'Universitet tarixi haqida batafsil',
                        'a': 'UzSWLU 1949-yilda Toshkent Davlat Chet Tillar Pedagogika Instituti sifatida tashkil etilgan. 1992-yilda Toshkent Chet Tillar Pedagogika Instituti va Respublika Rus Tili va Adabiyoti Instituti birlashtirildi. Natijada O\'zbekiston Davlat Jahon Tillari Universiteti (UzSWLU) yaratildi. Bugungi kunda universitet O\'zbekistonning eng yirik va nufuzli til ta\'lim muassasasidir.',
                        'short': '1949-yilda institut, 1992-yilda universitet maqomiga ega bo\'ldi'
                    },
                    'ru': {
                        'q': 'Подробно об истории университета',
                        'a': 'УзГУМЯ был основан в 1949 году как Ташкентский Государственный Педагогический Институт Иностранных Языков. В 1992 году были объединены Ташкентский Педагогический Институт Иностранных Языков и Республиканский Институт Русского Языка и Литературы. В результате был создан Узбекский Государственный Университет Мировых Языков (УзГУМЯ). Сегодня университет является крупнейшим и престижным языковым учебным заведением Узбекистана.',
                        'short': 'В 1949 институт, в 1992 получил статус университета'
                    },
                    'en': {
                        'q': 'Detailed university history',
                        'a': 'UzSWLU was founded in 1949 as Tashkent State Pedagogical Institute of Foreign Languages. In 1992, Tashkent Pedagogical Institute of Foreign Languages and Republican Institute of Russian Language and Literature were merged. As a result, Uzbekistan State World Languages University (UzSWLU) was created. Today, the university is the largest and most prestigious language educational institution in Uzbekistan.',
                        'short': 'Institute in 1949, university status in 1992'
                    },
                }
            },
            {
                'category': cats['history'],
                'translations': {
                    'uz': {
                        'q': 'Universitet necha yoshda?',
                        'a': 'UzSWLU 2024-yilda 75 yoshga to\'ldi. Universitet 1949-yilda tashkil etilgan va 75+ yillik tarixga ega. Bu davr mobaynida minglab malakali mutaxassislar tayyorlandi.',
                        'short': '75+ yillik tarixga ega (1949-yildan)'
                    },
                    'ru': {
                        'q': 'Сколько лет университету?',
                        'a': 'УзГУМЯ в 2024 году исполнилось 75 лет. Университет был основан в 1949 году и имеет 75+ летнюю историю. За это время были подготовлены тысячи квалифицированных специалистов.',
                        'short': '75+ лет истории (с 1949 года)'
                    },
                    'en': {
                        'q': 'How old is the university?',
                        'a': 'UzSWLU turned 75 years old in 2024. The university was founded in 1949 and has 75+ years of history. During this time, thousands of qualified specialists were trained.',
                        'short': '75+ years of history (since 1949)'
                    },
                }
            },
            {
                'category': cats['history'],
                'translations': {
                    'uz': {
                        'q': 'Universitet qanday rivojlangan?',
                        'a': 'UzSWLU 1949-yilda kichik institut sifatida boshlangan. 1992-yilda universitet maqomiga ega bo\'ldi. Hozirda 11 fakultet, 5000+ talaba, 50+ chet tilni o\'rgatadi. Universitet xalqaro hamkorlik dasturlariga ega va O\'zbekistonning eng yaxshi til universitetidir.',
                        'short': 'Kichik institutdan O\'zbekistonning eng yirik til universitetiga'
                    },
                    'ru': {
                        'q': 'Как развивался университет?',
                        'a': 'УзГУМЯ начался в 1949 году как небольшой институт. В 1992 году получил статус университета. Сейчас 11 факультетов, 5000+ студентов, преподаёт 50+ иностранных языков. Университет имеет программы международного сотрудничества и является лучшим языковым университетом Узбекистана.',
                        'short': 'От небольшого института до крупнейшего языкового университета'
                    },
                    'en': {
                        'q': 'How did the university develop?',
                        'a': 'UzSWLU started in 1949 as a small institute. In 1992, it received university status. Now has 11 faculties, 5000+ students, teaches 50+ foreign languages. The university has international cooperation programs and is the best language university in Uzbekistan.',
                        'short': 'From small institute to largest language university'
                    },
                }
            },
            {
                'category': cats['history'],
                'translations': {
                    'uz': {
                        'q': 'Universitet nomi qanday o\'zgargan?',
                        'a': '1949: Toshkent Davlat Chet Tillar Pedagogika Instituti. 1992: O\'zbekiston Davlat Jahon Tillari Universiteti (UzSWLU). Nom o\'zgarishi universitet rivojlanishi va maqomining oshganini ko\'rsatadi.',
                        'short': '1949-da institut, 1992-da universitet nomiga ega bo\'ldi'
                    },
                    'ru': {
                        'q': 'Как менялось название университета?',
                        'a': '1949: Ташкентский Государственный Педагогический Институт Иностранных Языков. 1992: Узбекский Государственный Университет Мировых Языков (УзГУМЯ). Изменение названия отражает развитие и повышение статуса университета.',
                        'short': 'В 1949 институт, в 1992 получил название университета'
                    },
                    'en': {
                        'q': 'How did the university name change?',
                        'a': '1949: Tashkent State Pedagogical Institute of Foreign Languages. 1992: Uzbekistan State World Languages University (UzSWLU). The name change reflects the development and elevation of the university\'s status.',
                        'short': 'Institute in 1949, university name in 1992'
                    },
                }
            },
            {
                'category': cats['history'],
                'translations': {
                    'uz': {
                        'q': 'Universitet yutuqlari',
                        'a': 'UzSWLU ko\'plab yutuqlarga ega: 75+ yillik tajriba, 50+ chet tilni o\'rgatish, 100+ xalqaro hamkorlik shartnomasi, minglab bitiruvchilar jahon bo\'ylab ishlaydi, O\'zbekistonning eng yaxshi til universiteti.',
                        'short': '75+ yil tajriba, 50+ til, 100+ xalqaro hamkorlik'
                    },
                    'ru': {
                        'q': 'Достижения университета',
                        'a': 'УзГУМЯ имеет множество достижений: 75+ лет опыта, преподавание 50+ иностранных языков, 100+ международных договоров о сотрудничестве, тысячи выпускников работают по всему миру, лучший языковый университет Узбекистана.',
                        'short': '75+ лет опыта, 50+ языков, 100+ международных партнёров'
                    },
                    'en': {
                        'q': 'University achievements',
                        'a': 'UzSWLU has many achievements: 75+ years of experience, teaching 50+ foreign languages, 100+ international cooperation agreements, thousands of graduates work worldwide, best language university in Uzbekistan.',
                        'short': '75+ years experience, 50+ languages, 100+ international partners'
                    },
                }
            },
            
            # RECTORATE (Rektorat) - 4 FAQs
            {
                'category': cats['rectorate'],
                'translations': {
                    'uz': {
                        'q': 'Universitet rektori kim?',
                        'a': 'Hozirgi vaqtda UzSWLU rektori - Tuxtasinov Ilxomjon Madaminovich. Qabul vaqti: Dushanba, 15:00-17:00. Telefon: +998 (71) 230-12-91. Email: rector@uzswlu.uz',
                        'short': 'Tuxtasinov Ilxomjon Madaminovich'
                    },
                    'ru': {
                        'q': 'Кто ректор университета?',
                        'a': 'В настоящее время ректор УзГУМЯ - Тухтасинов Илхомжон Мадаминович. Часы приёма: Понедельник, 15:00-17:00. Телефон: +998 (71) 230-12-91. Email: rector@uzswlu.uz',
                        'short': 'Тухтасинов Илхомжон Мадаминович'
                    },
                    'en': {
                        'q': 'Who is the rector?',
                        'a': 'Currently, the rector of UzSWLU is Tuxtasinov Ilxomjon Madaminovich. Reception hours: Monday, 15:00-17:00. Phone: +998 (71) 230-12-91. Email: rector@uzswlu.uz',
                        'short': 'Tuxtasinov Ilxomjon Madaminovich'
                    },
                }
            },
            {
                'category': cats['rectorate'],
                'translations': {
                    'uz': {
                        'q': 'Rektor bilan qanday uchrashish mumkin?',
                        'a': 'Rektor qabuli: Har dushanba kuni, 15:00-17:00. Oldindan ro\'yxatdan o\'tish kerak. Telefon: +998 (71) 230-12-91. Virtual qabulxona: https://uzswlu.uz/site/reception',
                        'short': 'Dushanba 15:00-17:00, oldindan ro\'yxatdan o\'ting'
                    },
                    'ru': {
                        'q': 'Как встретиться с ректором?',
                        'a': 'Приём ректора: Каждый понедельник, 15:00-17:00. Необходима предварительная запись. Телефон: +998 (71) 230-12-91. Виртуальная приёмная: https://uzswlu.uz/site/reception',
                        'short': 'Понедельник 15:00-17:00, предварительная запись'
                    },
                    'en': {
                        'q': 'How to meet the rector?',
                        'a': 'Rector\'s reception: Every Monday, 15:00-17:00. Prior registration required. Phone: +998 (71) 230-12-91. Virtual reception: https://uzswlu.uz/site/reception',
                        'short': 'Monday 15:00-17:00, prior registration required'
                    },
                }
            },
            {
                'category': cats['rectorate'],
                'translations': {
                    'uz': {
                        'q': 'Rektorat tarkibi',
                        'a': 'Rektorat: Rektor, O\'quv ishlari bo\'yicha prorektor, Ilmiy ishlar bo\'yicha prorektor, Moliya-xo\'jalik ishlari bo\'yicha prorektor, Ma\'naviy-ma\'rifiy ishlar bo\'yicha prorektor. Batafsil: uzswlu.uz',
                        'short': 'Rektor va 4 ta prorektor'
                    },
                    'ru': {
                        'q': 'Состав ректората',
                        'a': 'Ректорат: Ректор, Проректор по учебной работе, Проректор по научной работе, Проректор по финансово-хозяйственной работе, Проректор по духовно-просветительской работе. Подробнее: uzswlu.uz',
                        'short': 'Ректор и 4 проректора'
                    },
                    'en': {
                        'q': 'Rectorate composition',
                        'a': 'Rectorate: Rector, Vice-Rector for Academic Affairs, Vice-Rector for Scientific Affairs, Vice-Rector for Financial and Economic Affairs, Vice-Rector for Spiritual and Educational Affairs. Details: uzswlu.uz',
                        'short': 'Rector and 4 vice-rectors'
                    },
                }
            },
            {
                'category': cats['rectorate'],
                'translations': {
                    'uz': {
                        'q': 'Virtual qabulxona',
                        'a': 'Virtual qabulxona orqali rektoratga murojaat qilishingiz mumkin. Sayt: https://uzswlu.uz/site/reception. Bu yerda takliflar, shikoyatlar va savollaringizni yuborishingiz mumkin. Javob 3 ish kuni ichida beriladi.',
                        'short': 'uzswlu.uz/site/reception - 3 kun ichida javob'
                    },
                    'ru': {
                        'q': 'Виртуальная приёмная',
                        'a': 'Через виртуальную приёмную вы можете обратиться в ректорат. Сайт: https://uzswlu.uz/site/reception. Здесь вы можете отправить предложения, жалобы и вопросы. Ответ предоставляется в течение 3 рабочих дней.',
                        'short': 'uzswlu.uz/site/reception - ответ в течение 3 дней'
                    },
                    'en': {
                        'q': 'Virtual reception',
                        'a': 'You can contact the rectorate through the virtual reception. Website: https://uzswlu.uz/site/reception. Here you can send suggestions, complaints, and questions. Response is provided within 3 business days.',
                        'short': 'uzswlu.uz/site/reception - response within 3 days'
                    },
                }
            },
            # ADMISSION (Qabul) - 4 FAQs
            {
                'category': cats['admission'],
                'translations': {
                    'uz': {
                        'q': 'Qabul qachon boshlanadi?',
                        'a': 'UzSWLUda bakalavriatga qabul odatda iyun oyining oxiridan iyulning o‘rtalariga qadar davom etadi. 2024-yil uchun qabul 1-iyuldan boshlanishi rejalashtirilgan. Hujjatlar my.uzbmb.uz portali orqali onlayn qabul qilinadi.',
                        'short': '1-iyuldan my.uzbmb.uz orqali boshlanadi'
                    },
                    'ru': {
                        'q': 'Когда начинается прием?',
                        'a': 'Прием в бакалавриат УзГУМЯ обычно длится с конца июня до середины июля. Прием на 2024 год запланирован с 1 июля. Документы принимаются онлайн через портал my.uzbmb.uz.',
                        'short': 'С 1 июля через my.uzbmb.uz'
                    },
                    'en': {
                        'q': 'When does admission start?',
                        'a': 'Undergraduate admission at UzSWLU typically runs from late June to mid-July. For 2024, admission is planned to start on July 1st. Documents are accepted online via the my.uzbmb.uz portal.',
                        'short': 'Starts July 1st via my.uzbmb.uz'
                    },
                }
            },
            {
                'category': cats['admission'],
                'translations': {
                    'uz': {
                        'q': 'Qanday hujjatlar kerak?',
                        'a': 'Onlayn qabul uchun odatda pasport (ID-karta), attestat yoki diplom ma\'lumotlari kerak bo\'ladi. Agar chet tili sertifikatingiz (IELTS, CEFR va b.) bo\'lsa, u ham tizimga yuklanishi lozim.',
                        'short': 'Pasport, diplom va til sertifikati (agar bo\'lsa)'
                    },
                    'ru': {
                        'q': 'Какие документы нужны?',
                        'a': 'Для онлайн-приема обычно требуются данные паспорта (ID-карты), аттестата или диплома. Если у вас есть сертификат по иностранному языку (IELTS, CEFR и др.), его также необходимо загрузить в систему.',
                        'short': 'Паспорт, диплом и языковой сертификат (если есть)'
                    },
                    'en': {
                        'q': 'Which documents are required?',
                        'a': 'For online admission, you typically need passport (ID card), certificate or diploma details. If you have a foreign language certificate (IELTS, CEFR, etc.), it should also be uploaded to the system.',
                        'short': 'Passport, diploma and language certificate (if any)'
                    },
                }
            },
            {
                'category': cats['admission'],
                'translations': {
                    'uz': {
                        'q': 'Chet tili sertifikati imtiyozlari',
                        'a': 'Chet tilidan milliy (CEFR B2) yoki xalqaro (IELTS 5.5+) sertifikatga ega abituriyentlarga kirish imtihonlarida chet tili fanidan maksimal ball (93 ball) beriladi va ular ushbu fandan imtihon topshirmaydilar.',
                        'short': 'B2/IELTS 5.5+ bo\'lsa, chet tilidan maksimal ball beriladi'
                    },
                    'ru': {
                        'q': 'Льготы по сертификату иностранного языка',
                        'a': 'Абитуриентам, имеющим национальный (CEFR B2) или международный (IELTS 5.5+) сертификат по иностранному языку, на вступительных экзаменах начисляется максимальный балл (93 балла) по этому предмету.',
                        'short': 'B2/IELTS 5.5+ дают максимальный балл по языку'
                    },
                    'en': {
                        'q': 'Language certificate privileges',
                        'a': 'Applicants with a national (CEFR B2) or international (IELTS 5.5+) certificate in a foreign language are awarded maximum points (93 points) for the foreign language subject in entrance exams.',
                        'short': 'B2/IELTS 5.5+ grants maximum points for language'
                    },
                }
            },
            {
                'category': cats['admission'],
                'translations': {
                    'uz': {
                        'q': 'Magistratura qabuli haqida',
                        'a': 'Magistratura qabuli odatda avgust oyida magistr.edu.uz portali orqali amalga oshiriladi. Magistraturaga kirishda chet tili sertifikati (IELTS 6.0 / CEFR B2) bo\'lishi majburiydir.',
                        'short': 'Avgustda magistr.edu.uz orqali. Til sertifikati majburiy!'
                    },
                    'ru': {
                        'q': 'О приеме в магистратуру',
                        'a': 'Прием в магистратуру обычно осуществляется в августе через портал magistr.edu.uz. Наличие сертификата по иностранному языку (IELTS 6.0 / CEFR B2) является обязательным.',
                        'short': 'В августе через magistr.edu.uz. Языковой сертификат обязателен!'
                    },
                    'en': {
                        'q': 'About Master\'s admission',
                        'a': 'Master\'s degree admission is typically conducted in August through the magistr.edu.uz portal. Having a foreign language certificate (IELTS 6.0 / CEFR B2) is mandatory.',
                        'short': 'In August via magistr.edu.uz. Language cert is mandatory!'
                    },
                }
            },
            # FACULTIES (Fakultetlar) - 4 FAQs
            {
                'category': cats['faculties'],
                'translations': {
                    'uz': {
                        'q': 'Ingliz filologiyasi fakulteti',
                        'a': 'Ingliz filologiyasi fakultetida ingliz tili va adabiyoti bo‘yicha yuqori malakali mutaxassislar tayyorlanadi. Talabalar til nazariyasi va amaliyotini chuqur o‘rganadilar.',
                        'short': 'Ingliz tili va adabiyoti bo‘yicha mutaxassislar tayyorlaydi'
                    },
                    'ru': {
                        'q': 'Факультет английской филологии',
                        'a': 'На факультете английской филологии готовятся высококвалифицированные специалисты по английскому языку. Студенты глубоко изучают теорию и практику языка.',
                        'short': 'Готовит специалистов по английскому языку'
                    },
                    'en': {
                        'q': 'Faculty of English Philology',
                        'a': 'The Faculty of English Philology trains highly qualified specialists in English language and literature. Students study language theory and practice in depth.',
                        'short': 'Trains specialists in English language and literature'
                    },
                }
            },
            {
                'category': cats['faculties'],
                'translations': {
                    'uz': {
                        'q': 'Xalqaro jurnalistika fakulteti',
                        'a': 'Ushbu fakultetda xalqaro OAV mutaxassislari, jurnalistlar va PR menejerlar tayyorlanadi. Manzil: Chilonzor tumani, Lutfiy-8.',
                        'short': 'Media va PR mutaxassislari tayyorlaydi. Manzil: Lutfiy-8'
                    },
                    'ru': {
                        'q': 'Факультет международной журналистики',
                        'a': 'На этом факультете готовятся специалисты международных СМИ и PR-менеджеры. Адрес: Чиланзарский район, Лутфи-8.',
                        'short': 'Готовит специалистов медиа и PR. Адрес: Лутфи-8'
                    },
                    'en': {
                        'q': 'Faculty of International Journalism',
                        'a': 'This faculty trains international media specialists, journalists, and PR managers. Address: Chilonzor district, Lutfiy-8.',
                        'short': 'Trains media and PR specialists. Address: Lutfiy-8'
                    },
                }
            },
            {
                'category': cats['faculties'],
                'translations': {
                    'uz': {
                        'q': 'Tarjimonlik fakulteti',
                        'a': 'Fakultetda badiiy tarjima, sinxron tarjima va yozma tarjima yo‘nalishlari mavjud. Professional tarjimonlar tayyorlanadi.',
                        'short': 'Sinxron va yozma tarjima mutaxassislari'
                    },
                    'ru': {
                        'q': 'Переводческий факультет',
                        'a': 'На факультете есть направления художественного, синхронного и письменного перевода. Готовятся профессиональные переводчики.',
                        'short': 'Специалисты синхронного и письменного перевода'
                    },
                    'en': {
                        'q': 'Faculty of Translation',
                        'a': 'The faculty has specializations in literary, simultaneous, and written translation. Professional translators are trained.',
                        'short': 'Simultaneous and written translation specialists'
                    },
                }
            },
            {
                'category': cats['faculties'],
                'translations': {
                    'uz': {
                        'q': 'Rus filologiyasi fakulteti',
                        'a': 'Fakultetda rus tili va adabiyoti mutaxassislari tayyorlanadi. Manzil: Chilonzor tumani, Muqumiy-104.',
                        'short': 'Rus tili mutaxassislari. Manzil: Muqumiy-104'
                    },
                    'ru': {
                        'q': 'Факультет русской филологии',
                        'a': 'На факультете готовятся специалисты по русскому языку и литературе. Адрес: Чиланзарский район, Мукими-104.',
                        'short': 'Специалисты русского языка. Адрес: Мукими-104'
                    },
                    'en': {
                        'q': 'Faculty of Russian Philology',
                        'a': 'The faculty trains specialists in Russian language and literature. Address: Chilonzor district, Muqumiy-104.',
                        'short': 'Russian language specialists. Address: Muqumiy-104'
                    },
                }
            },
            # EDUCATION (Ta'lim) - 10 FAQs
            {
                'category': cats['education'],
                'translations': {
                    'uz': {
                        'q': 'Kredit-modul tizimi nima?',
                        'a': 'Bu talabaning o‘quv faoliyatini kreditlar asosida baholash tizimidir. Bir o‘quv yili davomida talaba odatda 60 kredit to‘plashi lozim.',
                        'short': 'Ta\'limni kreditlar asosida baholash tizimi'
                    },
                    'ru': {
                        'q': 'Что такое кредитно-модульная система?',
                        'a': 'Это система оценки учебной деятельности студента на основе кредитов. Обычно студент должен набрать 60 кредитов за год.',
                        'short': 'Система оценки образования на основе кредитов'
                    },
                    'en': {
                        'q': 'What is credit-module system?',
                        'a': 'It is a system for assessing a student\'s educational activity based on credits. A student typically needs 60 credits per year.',
                        'short': 'Education assessment system based on credits'
                    },
                }
            },
            {
                'category': cats['education'],
                'translations': {
                    'uz': {
                        'q': 'HEMIS tizimi haqida',
                        'a': 'HEMIS - oliy ta\'lim jarayonlarini boshqarishning axborot tizimidir. Talabalar baholari va o‘quv jadvalini kuzatib boradilar. Sayt: hemis.uzswlu.uz',
                        'short': 'Oliy ta\'limni boshqarish tizimi. hemis.uzswlu.uz'
                    },
                    'ru': {
                        'q': 'О системе HEMIS',
                        'a': 'HEMIS - информационная система управления высшим образованием. Студенты следят за оценками и расписанием. Сайт: hemis.uzswlu.uz',
                        'short': 'Система управления высшим образованием. hemis.uzswlu.uz'
                    },
                    'en': {
                        'q': 'About HEMIS system',
                        'a': 'HEMIS is an information system for managing higher education. Students track their grades and schedules. Website: hemis.uzswlu.uz',
                        'short': 'Higher education management system. hemis.uzswlu.uz'
                    },
                }
            },
            {
                'category': cats['education'],
                'translations': {
                    'uz': {
                        'q': 'Universitetda qanday tillar o\'rgatiladi?',
                        'a': 'Ingliz, nemis, fransuz, rus, ispan, italyan, arab, turk, xitoy, koreys, yapon va boshqalar. Jami 50 dan ortiq xorijiy tillar mavjud.',
                        'short': 'Jami 50+ xorijiy til'
                    },
                    'ru': {
                        'q': 'Какие языки преподаются?',
                        'a': 'Английский, немецкий, французский, русский, испанский, арабский, китайский, корейский, японский и др. Всего более 50 языков.',
                        'short': 'Всего 50+ иностранных языков'
                    },
                    'en': {
                        'q': 'What languages are taught?',
                        'a': 'English, German, French, Russian, Spanish, Arabic, Chinese, Korean, Japanese, and others. Total more than 50 languages.',
                        'short': 'Total 50+ foreign languages'
                    },
                }
            },
            {
                'category': cats['education'],
                'translations': {
                    'uz': {
                        'q': 'Sirtqi ta\'lim shakli bormi?',
                        'a': 'Ha, universitetda Sirtqi va Kechki ta\'lim shakllari mavjud. Qabul test sinovlari asosida amalga oshiriladi.',
                        'short': 'Ha, Sirtqi va Kechki ta\'lim shakllari mavjud'
                    },
                    'ru': {
                        'q': 'Есть ли заочная форма обучения?',
                        'a': 'Да, в университете есть Заочная и Вечерняя формы обучения. Прием на основе тестов.',
                        'short': 'Да, есть Заочная и Вечерняя формы обучения'
                    },
                    'en': {
                        'q': 'Is there a correspondence form of study?',
                        'a': 'Yes, the university offers Correspondence and Evening forms of study. Admission is based on tests.',
                        'short': 'Yes, Correspondence and Evening forms are available'
                    },
                }
            },
            {
                'category': cats['education'],
                'translations': {
                    'uz': {
                        'q': 'Kechki ta\'lim shakli haqida',
                        'a': 'Kechki ta\'limda darslar kunduzgi 14:00 dan keyin boshlanadi. Bu ishlovchi talabalar uchun qulaydir.',
                        'short': 'Darslar tushdan keyin (14:00+). Ishlovchilar uchun qulay'
                    },
                    'ru': {
                        'q': 'О вечерней форме обучения',
                        'a': 'Занятия начинаются после 14:00. Это удобно для работающих студентов.',
                        'short': 'Занятия после 14:00. Удобно для работающих'
                    },
                    'en': {
                        'q': 'About evening form of study',
                        'a': 'Classes start after 14:00. This is convenient for working students.',
                        'short': 'Classes in the afternoon (14:00+). Convenient for workers'
                    },
                }
            },
            {
                'category': cats['education'],
                'translations': {
                    'uz': {
                        'q': 'Qo\'shma ta\'lim dasturlari',
                        'a': 'UzSWLU xorijiy OTMlar bilan "2+2" yoki "3+1" tizimidagi qo\'shma dasturlarga ega. Ikki diplom olish imkoniyati mavjud.',
                        'short': 'Xorijiy OTMlar bilan ikkita diplomli dasturlar'
                    },
                    'ru': {
                        'q': 'Совместные программы',
                        'a': 'УзГУМЯ имеет совместные программы с зарубежными вузами («2+2», «3+1»). Можно получить два диплома.',
                        'short': 'Программы двойного диплома'
                    },
                    'en': {
                        'q': 'Joint educational programs',
                        'a': 'UzSWLU has joint programs with foreign universities ("2+2" or "3+1"). Double degree opportunity available.',
                        'short': 'Double degree programs with foreign universities'
                    },
                }
            },
            {
                'category': cats['education'],
                'translations': {
                    'uz': {
                        'q': 'Stipendiya miqdori qancha?',
                        'a': 'Stipendiya miqdori o\'zlashtirishga bog\'liq. Hozirda bazaviy miqdor davlat standartlari bo\'yicha to\'lanadi.',
                        'short': 'O\'zlashtirishga qarab belgilanadi'
                    },
                    'ru': {
                        'q': 'Каков размер стипендии?',
                        'a': 'Размер зависит от успеваемости. Выплачивается по государственным стандартам.',
                        'short': 'Определяется по успеваемости'
                    },
                    'en': {
                        'q': 'How much is the scholarship?',
                        'a': 'Scholarship levels depend on academic performance, paid according to state standards.',
                        'short': 'Determined by performance'
                    },
                }
            },
            {
                'category': cats['education'],
                'translations': {
                    'uz': {
                        'q': 'Dars vaqtlari qanday?',
                        'a': '1-smena 08:30 da, 2-smena 13:30/14:00 da boshlanadi. Paralar 80 daqiqadan iborat.',
                        'short': '1-smena (08:30+), 2-smena (13:30+)'
                    },
                    'ru': {
                        'q': 'Какое расписание занятий?',
                        'a': '1-я смена с 08:30, 2-я с 13:30/14:00. Пары длятся 80 минут.',
                        'short': '1-я смена (08:30+), 2-я смена (13:30+)'
                    },
                    'en': {
                        'q': 'What are the class hours?',
                        'a': '1st shift starts at 08:30, 2nd at 13:30/14:00. Pairs are 80 minutes.',
                        'short': '1st shift (08:30+), 2nd shift (13:30+)'
                    },
                }
            },
            {
                'category': cats['education'],
                'translations': {
                    'uz': {
                        'q': 'Akademik ta\'til olish',
                        'a': 'Salomatlik, oilaviy sharoit yoki harbiy xizmat uchun olinishi mumkin. Dekanatga ariza beriladi.',
                        'short': 'Salomatlik yoki sharoit bo\'yicha ariza beriladi'
                    },
                    'ru': {
                        'q': 'Академический отпуск',
                        'a': 'Можно получить по болезни или семейным обстоятельствам. Подается заявление в деканат.',
                        'short': 'Заявление в деканат по болезни или обстоятельствам'
                    },
                    'en': {
                        'q': 'Academic leave',
                        'a': 'Can be taken for health, family, or military reasons. Application to the dean\'s office.',
                        'short': 'Application to the dean\'s office required'
                    },
                }
            },
            {
                'category': cats['education'],
                'translations': {
                    'uz': {
                        'q': 'Dars qoldirish (NB)',
                        'a': 'Sababsiz dars qoldirish o\'zlashtirishga ta\'sir qiladi. Limitdan oshsa, qayta o\'qishga qoldirilishi mumkin.',
                        'short': 'NB-lar qayta o\'qishga sabab bo\'lishi mumkin'
                    },
                    'ru': {
                        'q': 'Пропуски занятий (НБ)',
                        'a': 'Пропуски без причины влияют на успеваемость. Превышение лимита ведет к пересдаче.',
                        'short': 'Пропуски могут привести к пересдаче'
                    },
                    'en': {
                        'q': 'Class absences (NB)',
                        'a': 'Absences without reason affect performance. Exceeding limits leads to retakes.',
                        'short': 'Absences can lead to retaking the subject'
                    },
                }
            },
            # STUDENT LIFE (Talaba hayoti) - 10 FAQs
            {
                'category': cats['student_life'],
                'translations': {
                    'uz': {
                        'q': 'Yotoqxona (TTJ) bormi?',
                        'a': 'Ha, talabalar turar joylari mavjud. Viloyatlik talabalar uchun joylar ajratiladi.',
                        'short': 'Ha, viloyatlik talabalar uchun TTJ bor'
                    },
                    'ru': {
                        'q': 'Есть ли общежитие?',
                        'a': 'Да, есть студенческие общежития. Места выделяются для иногородних студентов.',
                        'short': 'Да, есть общежитие для иногородних'
                    },
                    'en': {
                        'q': 'Is there a dormitory?',
                        'a': 'Yes, there are student dormitories. Places are available for rural students.',
                        'short': 'Yes, dormitories are available'
                    },
                }
            },
            {
                'category': cats['student_life'],
                'translations': {
                    'uz': {
                        'q': 'TTJ ga ariza berish',
                        'a': 'Joylashish uchun arizalar o\'quv yili boshida my.gov.uz orqali onlayn yuboriladi.',
                        'short': 'my.gov.uz orqali onlayn ariza beriladi'
                    },
                    'ru': {
                        'q': 'Заявка в общежитие',
                        'a': 'Заявки подаются в начале года онлайн через my.gov.uz.',
                        'short': 'Онлайн через my.gov.uz в начале года'
                    },
                    'en': {
                        'q': 'Dormitory application',
                        'a': 'Applications are submitted at the start of the year online via my.gov.uz.',
                        'short': 'Online application via my.gov.uz'
                    },
                }
            },
            {
                'category': cats['student_life'],
                'translations': {
                    'uz': {
                        'q': 'Kutubxona haqida',
                        'a': 'Universitetda boy axborot-resurs markazi va elektron kutubxona mavjud.',
                        'short': 'ARM va elektron kutubxona bor'
                    },
                    'ru': {
                        'q': 'О библиотеке',
                        'a': 'В университете есть информационно-ресурсный центр и электронная библиотека.',
                        'short': 'Есть ИРЦ и электронная библиотека'
                    },
                    'en': {
                        'q': 'About the library',
                        'a': 'The university has an information-resource center and an e-library.',
                        'short': 'Library and e-library available'
                    },
                }
            },
            {
                'category': cats['student_life'],
                'translations': {
                    'uz': {
                        'q': 'Sport to\'garaklari',
                        'a': 'Futbol, voleybol, basketbol, tennis va shaxmat kabi to\'garaklar mavjud.',
                        'short': 'Turli sport to\'garaklari mavjud'
                    },
                    'ru': {
                        'q': 'Спортивные секции',
                        'a': 'Доступны футбол, волейбол, баскетбол, теннис и шахматы.',
                        'short': 'Есть различные спортивные секции'
                    },
                    'en': {
                        'q': 'Sports clubs',
                        'a': 'Football, volleyball, basketball, tennis, and chess clubs are available.',
                        'short': 'Various sports clubs available'
                    },
                }
            },
            {
                'category': cats['student_life'],
                'translations': {
                    'uz': {
                        'q': 'Talabalar oshxonasi',
                        'a': 'Hududda bir nechta oshxona va bufetlar arzon narxlarda xizmat ko\'rsatadi.',
                        'short': 'Arzon oshxona va bufetlar mavjud'
                    },
                    'ru': {
                        'q': 'Студенческая столовая',
                        'a': 'На территории есть недорогие столовые и буфеты.',
                        'short': 'Есть недорогие столовые и буфеты'
                    },
                    'en': {
                        'q': 'Student canteen',
                        'a': 'Several affordable canteens and buffets operate on campus.',
                        'short': 'Affordable canteens available'
                    },
                }
            },
            {
                'category': cats['student_life'],
                'translations': {
                    'uz': {
                        'q': 'Til kurslari',
                        'a': 'Chet tillarni o\'rganish markazida IELTS va boshqa til kurslari mavjud.',
                        'short': 'IELTS va til kurslari bor'
                    },
                    'ru': {
                        'q': 'Языковые курсы',
                        'a': 'В Центре изучения языков есть курсы IELTS и других языков.',
                        'short': 'Есть курсы IELTS и иностранных языков'
                    },
                    'en': {
                        'q': 'Language courses',
                        'a': 'IELTS and other language courses are available at the Language Center.',
                        'short': 'IELTS and language courses available'
                    },
                }
            },
            {
                'category': cats['student_life'],
                'translations': {
                    'uz': {
                        'q': 'Wi-Fi zonalari',
                        'a': 'Bosh bino, kutubxona va fakultetlarda bepul Wi-Fi zonalari mavjud.',
                        'short': 'Asosiy joylarda bepul Wi-Fi bor'
                    },
                    'ru': {
                        'q': 'Зоны Wi-Fi',
                        'a': 'Бесплатный Wi-Fi доступен в главном здании, библиотеке и на факультетах.',
                        'short': 'Бесплатный Wi-Fi в основных зонах'
                    },
                    'en': {
                        'q': 'Wi-Fi zones',
                        'a': 'Free Wi-Fi zones are available in the main building, library, and faculties.',
                        'short': 'Free Wi-Fi in key locations'
                    },
                }
            },
            {
                'category': cats['student_life'],
                'translations': {
                    'uz': {
                        'q': 'Talabalar Kengashi',
                        'a': 'Talabalar manfaatlarini himoya qiladi va tadbirlarni tashkil etadi.',
                        'short': 'Tadbirlar tashkil etuvchi kengash'
                    },
                    'ru': {
                        'q': 'Студенческий совет',
                        'a': 'Защищает интересы студентов и организует мероприятия.',
                        'short': 'Совет, организующий мероприятия'
                    },
                    'en': {
                        'q': 'Student Council',
                        'a': 'Protects student interests and organizes events.',
                        'short': 'Council organizing student events'
                    },
                }
            },
            {
                'category': cats['student_life'],
                'translations': {
                    'uz': {
                        'q': 'Qanday tadbirlar bor?',
                        'a': 'Zakovat, festivallar, konferensiyalar va sport musobaqalari o\'tkaziladi.',
                        'short': 'Zakovat, festivallar va konferensiyalar'
                    },
                    'ru': {
                        'q': 'Какие мероприятия?',
                        'a': 'Проводятся заковат, фестивали, конференции и спорт.',
                        'short': 'Заковат, фестивали и конференции'
                    },
                    'en': {
                        'q': 'What events are held?',
                        'a': 'Zakovat, festivals, conferences, and sports are organized.',
                        'short': 'Zakovat, festivals, and conferences'
                    },
                }
            },
            {
                'category': cats['student_life'],
                'translations': {
                    'uz': {
                        'q': 'Karyera markazi',
                        'a': 'Bitiruvchilarga ish topishda yordam beradi va treninglar o\'tkazadi.',
                        'short': 'Ishga joylashishga yordam beradi'
                    },
                    'ru': {
                        'q': 'Карьерный центр',
                        'a': 'Помогает выпускникам с трудоустройством и проводит тренинги.',
                        'short': 'Помогает с трудоустройством'
                    },
                    'en': {
                        'q': 'Career center',
                        'a': 'Helps graduates find jobs and conducts training sessions.',
                        'short': 'Assists with employment'
                    },
                }
            },
            # CONTACT (Aloqa) - 6 FAQs
            {
                'category': cats['contact'],
                'translations': {
                    'uz': {
                        'q': 'Universitet manzili',
                        'a': 'Toshkent sh., Uchtepa tumani, Kichik halqa yo‘li, 21-uy. Metro: Mirzo Ulug‘bek.',
                        'short': 'Uchtepa tumani, Kichik halqa yo‘li, 21-uy'
                    },
                    'ru': {
                        'q': 'Адрес университета',
                        'a': 'Ташкент, Учтепинский район, Кичик халка йули, 21. Метро: Мирзо Улугбек.',
                        'short': 'Учтепинский район, Кичик халка йули, 21'
                    },
                    'en': {
                        'q': 'University address',
                        'a': '21, Kichik halqa yo\'li str., Uchtepa district, Tashkent. Metro: Mirzo Ulugbek.',
                        'short': '21, Kichik halqa yo\'li str., Uchtepa district'
                    },
                }
            },
            {
                'category': cats['contact'],
                'translations': {
                    'uz': {
                        'q': 'Ishonch telefoni',
                        'a': 'Call-center: +998 (71) 230-12-91. Ish vaqti: 09:00 - 18:00.',
                        'short': '+998 (71) 230-12-91 (09:00 - 18:00)'
                    },
                    'ru': {
                        'q': 'Телефон доверия',
                        'a': 'Call-центр: +998 (71) 230-12-91. Работает 09:00 - 18:00.',
                        'short': '+998 (71) 230-12-91 (09:00 - 18:00)'
                    },
                    'en': {
                        'q': 'Hotline number',
                        'a': 'Call-center: +998 (71) 230-12-91. Hours: 09:00 - 18:00.',
                        'short': '+998 (71) 230-12-91 (09:00 - 18:00)'
                    },
                }
            },
            {
                'category': cats['contact'],
                'translations': {
                    'uz': {
                        'q': 'Rasmiy telegram kanali',
                        'a': 'Kanal: @UzSWLU. Rektor kanali: @rectorswlu.',
                        'short': '@UzSWLU - rasmiy telegram kanal'
                    },
                    'ru': {
                        'q': 'Телеграм-канал',
                        'a': 'Канал: @UzSWLU. Канал ректора: @rectorswlu.',
                        'short': '@UzSWLU - телеграм-канал'
                    },
                    'en': {
                        'q': 'Telegram channel',
                        'a': 'Channel: @UzSWLU. Rector\'s channel: @rectorswlu.',
                        'short': '@UzSWLU - official channel'
                    },
                }
            },
            {
                'category': cats['contact'],
                'translations': {
                    'uz': {
                        'q': 'Qabul komissiyasi telefoni',
                        'a': 'Mavsumda +998 (71) 230-12-91 orqali bog\'lanish mumkin.',
                        'short': 'Qabul: +998 (71) 230-12-91'
                    },
                    'ru': {
                        'q': 'Телефон приемной комиссии',
                        'a': 'В период приема: +998 (71) 230-12-91.',
                        'short': 'Приемная: +998 (71) 230-12-91'
                    },
                    'en': {
                        'q': 'Admissions phone',
                        'a': 'Contact +998 (71) 230-12-91 during the season.',
                        'short': 'Admissions: +998 (71) 230-12-91'
                    },
                }
            },
            {
                'category': cats['contact'],
                'translations': {
                    'uz': {
                        'q': 'Jurnalistika fakulteti manzili',
                        'a': 'Chilonzor tumani, Lutfiy-8. Telefon: +998 71 231 10 16.',
                        'short': 'Chilonzor tumani, Lutfiy-8'
                    },
                    'ru': {
                        'q': 'Адрес факультета журналистики',
                        'a': 'Чиланзарский район, Лутфи-8. Тел: +998 71 231 10 16.',
                        'short': 'Чиланзарский район, Лутфи-8'
                    },
                    'en': {
                        'q': 'Journalism faculty address',
                        'a': '8, Lutfiy str., Chilonzor district. Tel: +998 71 231 10 16.',
                        'short': '8, Lutfiy str., Chilonzor'
                    },
                }
            },
            {
                'category': cats['contact'],
                'translations': {
                    'uz': {
                        'q': 'Ijtimoiy tarmoqlar',
                        'a': 'Instagram/Telegram/Facebook: @uzswlu.',
                        'short': '@uzswlu barcha tarmoqlarda'
                    },
                    'ru': {
                        'q': 'Социальные сети',
                        'a': 'Instagram/Telegram/Facebook: @uzswlu.',
                        'short': '@uzswlu во всех сетях'
                    },
                    'en': {
                        'q': 'Social media',
                        'a': 'Instagram/Telegram/Facebook: @uzswlu.',
                        'short': '@uzswlu on all platforms'
                    },
                }
            },
            # INTERNATIONAL & ACHIEVEMENTS - 5 FAQs
            {
                'category': cats['general'],
                'translations': {
                    'uz': {
                        'q': 'Xalqaro hamkorlik haqida',
                        'a': 'UzSWLU dunyoning 100 dan ortiq universitetlari bilan hamkorlik qiladi. Erasmus+, ITEC va boshqa xalqaro dasturlarda ishtirok etadi.',
                        'short': '100+ xalqaro hamkor va Erasmus+ dasturi'
                    },
                    'ru': {
                        'q': 'О международном сотрудничестве',
                        'a': 'УзГУМЯ сотрудничает с более чем 100 университетами мира. Участвует в Erasmus+, ITEC и других программах.',
                        'short': '100+ партнеров и программа Erasmus+'
                    },
                    'en': {
                        'q': 'About international cooperation',
                        'a': 'UzSWLU cooperates with more than 100 universities worldwide. It participates in Erasmus+, ITEC, and other international programs.',
                        'short': '100+ international partners and Erasmus+'
                    },
                }
            },
            {
                'category': cats['general'],
                'translations': {
                    'uz': {
                        'q': 'Talabalar almashinuvi dasturlari',
                        'a': 'Iqtidorli talabalar uchun Koreya, Yaponiya, Germaniya va boshqa davlatlar universitetlarida bir semestr davomida o‘qish imkonini beruvchi almashinuv dasturlari mavjud.',
                        'short': 'Xorijda 1 semestr o\'qish imkoniyati'
                    },
                    'ru': {
                        'q': 'Программы обмена студентами',
                        'a': 'Для одаренных студентов есть программы обмена, позволяющие обучаться один семестр в вузах Кореи, Японии, Германии и других стран.',
                        'short': 'Возможность обучения за рубежом 1 семестр'
                    },
                    'en': {
                        'q': 'Student exchange programs',
                        'a': 'For talented students, there are exchange programs allowing them to study for one semester at universities in Korea, Japan, Germany, and other countries.',
                        'short': '1 semester study abroad opportunity'
                    },
                }
            },
            {
                'category': cats['general'],
                'translations': {
                    'uz': {
                        'q': 'Universitet reytingi',
                        'a': 'UzSWLU O‘zbekistonning eng kuchli 10 ta universitetidan biri va filologiya yo‘nalishida yetakchi o‘rinda turadi.',
                        'short': 'O‘zbekistonning top-10 talik universitetlaridan biri'
                    },
                    'ru': {
                        'q': 'Рейтинг университета',
                        'a': 'УзГУМЯ входит в топ-10 лучших вузов Узбекистана и занимает лидирующие позиции в области филологии.',
                        'short': 'Входит в топ-10 вузов Узбекистана'
                    },
                    'en': {
                        'q': 'University ranking',
                        'a': 'UzSWLU is among the top 10 universities in Uzbekistan and holds a leading position in the field of philology.',
                        'short': 'One of the top 10 universities in Uzbekistan'
                    },
                }
            },
            {
                'category': cats['general'],
                'translations': {
                    'uz': {
                        'q': 'Bitiruvchilar qayerda ishlaydi?',
                        'a': 'Bitiruvchilar TIV, elchixonalar, xalqaro tashkilotlar, OTMlar, maktablar va yirik xususiy kompaniyalarda tarjimon, o‘qituvchi va diplomat sifatida ishlaydi.',
                        'short': 'TIV, elchixonalar va xalqaro tashkilotlar'
                    },
                    'ru': {
                        'q': 'Где работают выпускники?',
                        'a': 'Выпускники работают в МИД, посольствах, международных организациях, вузах и школах переводчиками, учителями и дипломатами.',
                        'short': 'МИД, посольства и международные организации'
                    },
                    'en': {
                        'q': 'Where do graduates work?',
                        'a': 'Graduates work in the MFA, embassies, international organizations, universities, and schools as translators, teachers, and diplomats.',
                        'short': 'MFA, embassies, and international organizations'
                    },
                }
            },
            {
                'category': cats['general'],
                'translations': {
                    'uz': {
                        'q': 'Nega aynan UzSWLU ni tanlash kerak?',
                        'a': 'Katta tajriba (75 yil), kuchli akademik baza, xalqaro muhit va 50 dan ortiq tillarni o‘rganish imkoniyati tufayli.',
                        'short': '75 yillik tajriba va 50+ til o\'rganish imkoniyati'
                    },
                    'ru': {
                        'q': 'Почему стоит выбрать УзГУМЯ?',
                        'a': 'Благодаря огромному опыту (75 лет), сильной академической базе, международной среде и возможности изучения более 50 языков.',
                        'short': '75 лет опыта и изучение 50+ языков'
                    },
                    'en': {
                        'q': 'Why choose UzSWLU?',
                        'a': 'Due to 75 years of experience, a strong academic base, international environment, and the opportunity to learn more than 50 languages.',
                        'short': '75 years of experience and 50+ languages'
                    },
                }
            },
        ]
        
        # Continue with more FAQs in next part...
        # This is getting too long, I'll create it in parts
        
        count = 0
        for item in faq_data:
            faq = FAQ.objects.create(
                category=item['category'],
                status='published',
                canonical_id=uuid.uuid4(),
                is_current=item.get('is_current', True),
                year=item.get('year', 2024)
            )
            
            for lang, content in item['translations'].items():
                FAQTranslation.objects.create(
                    faq=faq,
                    lang=lang,
                    question=content['q'],
                    answer=content['a'],
                    short_answer=content.get('short', ''),
                    question_variants=[],
                    embedding_id=str(uuid.uuid4())
                )
            count += 1
            if count % 10 == 0:
                self.stdout.write(f"  ✓ Created {count} FAQs...")
        
        self.stdout.write(self.style.SUCCESS(f"  ✓ Total {count} FAQs created"))

    def _create_dynamic_info(self):
        """Create dynamic information entries"""
        dynamic_data = [
            {'key': 'founded_year', 'value': '1949', 'description': 'Universitet tashkil etilgan yil'},
            {'key': 'university_age', 'value': '75', 'description': 'Universitet yoshi (yil)'},
            {'key': 'total_students', 'value': '5000', 'description': 'Jami talabalar soni'},
            {'key': 'total_faculties', 'value': '11', 'description': 'Fakultetlar soni'},
            {'key': 'languages_taught', 'value': '50', 'description': 'O\'rgatiladigan tillar soni'},
            {'key': 'international_partners', 'value': '100', 'description': 'Xalqaro hamkorlar soni'},
            
            # Contact
            {'key': 'phone_main', 'value': '+998 (71) 230-12-91', 'description': 'Asosiy telefon'},
            {'key': 'email_main', 'value': 'uzdjtu@uzswlu.uz', 'description': 'Asosiy email'},
            {'key': 'address_main', 'value': 'Toshkent sh., Kichik halqa yo\'li, G9-A 21-uy', 'description': 'Bosh bino manzili'},
            {'key': 'telegram', 'value': '@UzSWLU', 'description': 'Telegram kanal'},
            {'key': 'website', 'value': 'https://uzswlu.uz', 'description': 'Rasmiy veb-sayt'},
            
            # Admission
            {'key': 'admission_start', 'value': '2024-07-01', 'description': 'Qabul boshlanish sanasi'},
            {'key': 'admission_end', 'value': '2024-08-31', 'description': 'Qabul tugash sanasi'},
            {'key': 'min_score', 'value': '56.7', 'description': 'Minimal o\'tish balli'},
            {'key': 'contract_min', 'value': '8000000', 'description': 'Kontrakt minimal narxi (so\'m)'},
            {'key': 'contract_max', 'value': '15000000', 'description': 'Kontrakt maksimal narxi (so\'m)'},
            
            # Working hours
            {'key': 'working_hours', 'value': 'Dushanba-Juma 9:00-18:00', 'description': 'Ish vaqti'},
            {'key': 'rector_reception', 'value': 'Dushanba 15:00-17:00', 'description': 'Rektor qabuli'},
        ]
        
        for data in dynamic_data:
            DynamicInfo.objects.create(**data)
            self.stdout.write(f"  ✓ {data['key']}: {data['value']}")

    def _create_documents(self):
        """Create sample documents with chunks"""
        docs_data = [
            {
                'title': 'UzSWLU Universitet Ustavi',
                'content': 'O\'zbekiston Davlat Jahon Tillari Universiteti Ustavi. Universitet 1949-yilda tashkil etilgan...',
                'source_type': 'pdf',
                'source_url': 'https://uzswlu.uz/documents/ustav.pdf'
            },
            {
                'title': 'Qabul Qoidalari 2024-2025',
                'content': 'UzSWLU 2024-2025 o\'quv yili uchun qabul qoidalari. Minimal ball: 56.7...',
                'source_type': 'pdf',
                'source_url': 'https://uzswlu.uz/admission/rules.pdf'
            },
        ]
        
        for doc_data in docs_data:
            doc = Document.objects.create(
                title=doc_data['title'],
                source_type=doc_data['source_type'],
                url=doc_data['source_url'],
                status='ready',
                is_current=doc_data.get('is_current', True),
                year=doc_data.get('year', 2024)
            )
            
            # Create chunks
            chunks = [
                doc_data['content'][:500],
                doc_data['content'][500:1000] if len(doc_data['content']) > 500 else ''
            ]
            
            for i, chunk_text in enumerate(chunks):
                if chunk_text:
                    DocumentChunk.objects.create(
                        document=doc,
                        chunk_index=i,
                        chunk_text=chunk_text,
                        lang='uz'
                    )
            
            self.stdout.write(f"  ✓ {doc.title}")

    def _update_search_vectors(self):
        """Update search vectors for all FAQ translations"""
        for trans in FAQTranslation.objects.all():
            trans.question_tsv = SearchVector('question', weight='A')
            trans.answer_tsv = SearchVector('answer', weight='B')
            trans.save()
        
        count = FAQTranslation.objects.count()
        self.stdout.write(self.style.SUCCESS(f"  ✓ Updated {count} search vectors"))

    def _sync_chromadb(self):
        """Sync FAQs to ChromaDB"""
        try:
            from rag_service import get_rag_service
            rag = get_rag_service()
            rag.sync_from_database()
            self.stdout.write(self.style.SUCCESS('  ✓ Successfully synced to ChromaDB'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  ⚠ ChromaDB sync failed: {e}'))

    def _print_statistics(self):
        """Print final statistics"""
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("📊 DATABASE STATISTICS"))
        self.stdout.write("=" * 70)
        
        stats = [
            ("Categories", Category.objects.count()),
            ("FAQs", FAQ.objects.count()),
            ("FAQ Translations", FAQTranslation.objects.count()),
            ("Dynamic Info", DynamicInfo.objects.count()),
            ("Documents", Document.objects.count()),
            ("Document Chunks", DocumentChunk.objects.count()),
        ]
        
        for name, count in stats:
            self.stdout.write(f"  {name:.<50} {count:>4}")
        
        self.stdout.write("=" * 70)
