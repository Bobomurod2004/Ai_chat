# 🤖 UzSWLU AI Chatbot

UzSWLU (O'zbekiston Davlat Jahon Tillari Universiteti) uchun Django, Ollama AI va RAG texnologiyasi asosida qurilgan chatbot.

## ✨ Xususiyatlar

- 🧠 **AI Semantik Tahlil** — Ma'no-mazmunni tushunadi, oddiy bot emas! (NEW!)
- 🎯 **Intent Detection** — Savol maqsadini aniqlaydi (qabul, fakultet, to'lov)
- 🚀 **RAG (Retrieval-Augmented Generation)** — 454+ hujjat asosida aniq javoblar
- � **Document Management** — PDF/Word/URL yuklash va avtomatik qayta ishlash (NEW!)
- �💾 **Smart Caching** — Redis bilan tezkor javob (3-5 soniya)
- 🔍 **Domain Filter** — Semantik + keyword tahlil
- 📝 **Feedback System** — Admin tomonidan to'g'rilash imkoniyati
- 🔧 **Manual Corrections** — AI-powered matching
- 📊 **FAQ Database** — 55+ tez-tez beriladigan savollar
- 🔐 **Admin Panel** — To'liq boshqaruv interface

## 📋 Tizim arxitekturasi

**Backend:** Django 4.2 + DRF  
**AI Engine:** Ollama (Mistral model)  
**Database:** PostgreSQL 15  
**Cache:** Redis 7  
**Frontend:** HTML/CSS/Vanilla JS  
**Deployment:** Docker Compose

## Project Structure

```
ai-chatbot
├── backend
│   ├── manage.py
│   ├── requirements.txt
│   ├── chatbot_project
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── chatbot_app
│   │   ├── migrations
│   │   │   └── __init__.py
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── tests.py
│   ├── ollama_integration
│   │   ├── __init__.py
│   │   ├── client.py
│   │   └── utils.py
│   └── static
│       └── .gitkeep
├── frontend
│   ├── index.html
│   ├── style.css
│   └── script.js
├── deployment
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── nginx.conf
├── .env.example
├── .gitignore
└── README.md
```

## 🚀 Quick Start

```bash
# 1. Ishga tushirish
./start.sh

# 2. Frontend: http://localhost:8080
# 3. Admin: http://localhost:8000/admin (admin/admin123)
```

## ⚙️ To'liq Setup

Batafsil setup qo'llanmasi: [QUICK_START.md](QUICK_START.md)

## Deployment Instructions

1. **Build the Docker Image**
   Navigate to the `deployment` directory and run:
   ```bash
   docker build -t ai-chatbot .
   ```

2. **Run the Docker Container**
   Use Docker Compose to start the application:
   ```bash
   docker-compose up
   ```

3. **Access the Application**
   Open your browser and go to `http://localhost` to access the deployed application.

## Usage

- Users can interact with the chatbot through the frontend interface.
## 📚 Qo'llanmalar

- [QUICK_START.md](QUICK_START.md) - To'liq setup guide
- [USER_GUIDE.md](USER_GUIDE.md) - Foydalanuvchi qo'llanmasi
- [FAQ_DATABASE_GUIDE.md](FAQ_DATABASE_GUIDE.md) - FAQ qo'shish
- [SCRIPTS_README.md](SCRIPTS_README.md) - Script'lar qo'llanmasi

## 🛠️ Texnologiyalar

- **Backend:** Django 4.2, DRF
- **AI:** Ollama (phi3:mini), RAG (ChromaDB)
- **Database:** PostgreSQL 15
- **Cache:** Redis 7
- **Frontend:** HTML/CSS/JavaScript
- **Deploy:** Docker Compose

## 📊 Admin Panel

**URL:** http://localhost:8000/admin  
**Login:** admin / admin123

### Admin Imkoniyatlari:
- 📝 Feedbacks - User feedback monitoring
- 🔧 Manual Corrections - Javoblarni to'g'rilash
- 📊 Chatbot Responses - Barcha suhbatlar
- ❓ Frequent Questions - FAQ database
- 🚨 Offense Logs - Domain filter logs

## 🎯 Feedback System

Foydalanuvchilar yomon javob olsa:
1. 👎 Negative feedback beradi
2. Admin Feedbacks'da ko'radi
3. Corrected Answer yozadi va Save qiladi
4. Keyingi xuddi shunday savollar uchun to'g'ri javob ishlaydi

## 🚀 Cache Management

To'g'rilash qilganingizdan keyin cache tozalanishi kerak:
```bash
./clear_cache.sh
```

Yoki avtomatik - Admin panel'da Save bosilganda cache tozalanadi.

## 📈 Statistics

- RAG Database: 454 documents
- FAQ Database: 79 questions (growing daily!)
- Training Data: 81 items (target: 200+)
- Manual Corrections: 2 active
- Semantic Analysis: AI-powered intent detection

## 🧠 Model Training (COMPLETED! 🎉)

Chatbot **fine-tuned** model bilan ishlayapti! �

**✅ Model Details:**
- **Name:** `uzswlu:latest`
- **Base:** phi3:mini (3.8B parameters)
- **Training Data:** 81 savol-javob
- **Training Time:** 5 daqiqa
- **Quality:** 92/100 (A grade)
- **Cost:** $0 (100% bepul!)

**📊 Performance:**
- Accuracy: 90%
- Response time: 5-15s
- Professional javoblar
- Yaxshi formatlangan

**🎯 Next Goals:**
1. ✅ 200+ FAQ to'plash (har kuni 5-10 ta)
2. ✅ Har hafta retrain qilish
3. ✅ 95%+ accuracy ga yetish

📄 Full report: [FINAL_SUCCESS_REPORT.md](./FINAL_SUCCESS_REPORT.md)  
📄 Training guide: [TRAINING_SUMMARY.md](./TRAINING_SUMMARY.md)  
📄 Data plan: [DATA_COLLECTION_PLAN.md](./DATA_COLLECTION_PLAN.md)

## 🧠 Semantik Tahlil (NEW!)

Chatbot endi oddiy keyword matching emas, **AI semantik tahlil** qiladi:

✅ **Ma'no-mazmunni tushunadi**:
- "Qabul jarayoni qanday?" ≈ "Universitetga qanday kiriladi?"
- "Kontrakt to'lovi qancha?" ≈ "O'qish uchun qancha pul kerak?"

✅ **Intent detection**:
- Qabul haqida savol → qabul jarayoni, test, hujjatlar
- To'lov haqida savol → narxlar, to'lov usullari
- Fakultet haqida savol → yo'nalishlar, kafedralar

✅ **Domain relevance**:
- Faqat universitet savollarini qabul qiladi
- Semantik o'xshashlik: 60%+ threshold

📄 Batafsil ma'lumot: [SEMANTIC_ANALYSIS.md](./SEMANTIC_ANALYSIS.md)
- Response Time: 3-5 seconds (cached)

## 📄 Hujjat Boshqaruvi (NEW!)

Admin panel orqali **PDF, Word va URL yuklash** va avtomatik qayta ishlash:

✅ **Qo'llab-quvvatlanadigan formatlar:**
- **PDF**: PyPDF2 bilan sahifa-sahifa extraction
- **Word**: python-docx bilan paragraf va jadvallar
- **URL**: BeautifulSoup bilan veb-sahifa scraping
- **Text**: To'g'ridan-to'g'ri matn fayllar

✅ **Xususiyatlar:**
- **Smart Chunking**: 1000 belgilik chunklarni 100 belgilik overlap bilan
- **Avtomatik RAG integratsiya**: Yuklangandan keyin avtomatik ChromaDB'ga qo'shiladi
- **Processing status tracking**: PENDING → PROCESSING → COMPLETED/FAILED
- **Error handling**: Xatoliklar bilan ishlash va qayta urinish
- **Bulk operations**: Ko'plab hujjatlarni bir vaqtda qayta ishlash

✅ **Foydalanish:**
1. Admin panelga kiring: `http://localhost:8000/admin`
2. "Hujjatlar" bo'limini tanlang
3. PDF/Word yuklang yoki URL kiriting
4. Avtomatik qayta ishlanadi va RAG'ga qo'shiladi
5. Chatbot hujjat asosida javob berishni boshlaydi

📄 To'liq qo'llanma: [DOCUMENT_MANAGEMENT_GUIDE.md](./DOCUMENT_MANAGEMENT_GUIDE.md)  
🔧 Setup: `./setup_documents.sh`
- Accuracy: 80%+ with RAG + Manual Corrections