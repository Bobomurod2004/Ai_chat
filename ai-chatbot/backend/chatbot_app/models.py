from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


# =============================================================================
# KNOWLEDGE BASE MODELS - Universal ma'lumotlar bazasi
# =============================================================================

class Category(models.Model):
    """
    Asosiy kategoriyalar: Admission, Faculties, Tuition, Student Life, etc.
    """
    name = models.CharField(max_length=100, unique=True)
    name_uz = models.CharField(max_length=100, blank=True, help_text="O'zbek tilidagi nomi")
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Emoji yoki icon nomi")
    order = models.PositiveIntegerField(default=0, help_text="Tartib raqami")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"
        ordering = ['order', 'name']
    
    def __str__(self):
        return f"{self.icon} {self.name}" if self.icon else self.name
    
    @property
    def faq_count(self):
        return self.faqs.filter(is_active=True).count()


class Topic(models.Model):
    """
    Kategoriya ichidagi mavzular: Requirements, Documents, Process, etc.
    """
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='topics')
    name = models.CharField(max_length=100)
    name_uz = models.CharField(max_length=100, blank=True)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Mavzu"
        verbose_name_plural = "Mavzular"
        ordering = ['category', 'order', 'name']
        unique_together = ['category', 'slug']
    
    def __str__(self):
        return f"{self.category.name} > {self.name}"


class FAQ(models.Model):
    """
    Savollar va javoblar bazasi - AI chatbot uchun asosiy ma'lumot manbai.
    """
    PRIORITY_CHOICES = [
        (1, 'Past'),
        (2, 'O\'rta'),
        (3, 'Yuqori'),
        (4, 'Juda muhim'),
    ]
    
    # Kategoriya va mavzu
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='faqs')
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True, related_name='faqs')
    
    # Savol va javob
    question = models.TextField(help_text="Asosiy savol")
    question_variants = models.JSONField(
        default=list, 
        blank=True,
        help_text="Savolning boshqa variantlari (list). Masalan: ['When is admission?', 'Admission dates?']"
    )
    answer = models.TextField(help_text="Javob matni")
    short_answer = models.CharField(max_length=255, blank=True, help_text="Qisqa javob (optional)")
    
    # Metadata
    tags = models.JSONField(
        default=list, 
        blank=True,
        help_text="Qidiruv uchun teglar. Masalan: ['admission', 'dates', 'june']"
    )
    keywords = models.TextField(
        blank=True, 
        help_text="Qidiruv uchun kalit so'zlar (vergul bilan ajratilgan)"
    )
    
    # Manbalar
    source_url = models.URLField(blank=True, help_text="Ma'lumot manbasi URL")
    source_name = models.CharField(max_length=100, blank=True, help_text="Manba nomi")
    
    # Prioritet va status
    priority = models.PositiveSmallIntegerField(choices=PRIORITY_CHOICES, default=2)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False, help_text="Admin tomonidan tekshirilgan")
    
    # Statistika
    view_count = models.PositiveIntegerField(default=0)
    helpful_count = models.PositiveIntegerField(default=0)
    not_helpful_count = models.PositiveIntegerField(default=0)
    
    # Vaqt
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    # Embedding (ChromaDB bilan sinxronizatsiya uchun)
    embedding_updated = models.BooleanField(default=False, help_text="ChromaDB ga qo'shilganmi")
    
    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQlar"
        ordering = ['-priority', '-view_count', '-created_at']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['priority', '-view_count']),
            models.Index(fields=['embedding_updated']),
        ]
    
    def __str__(self):
        return f"[{self.category.name}] {self.question[:60]}..."
    
    def record_view(self):
        """FAQ ko'rilganini qayd qilish"""
        self.view_count += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['view_count', 'last_used_at'])
    
    def get_all_questions(self):
        """Barcha savol variantlarini olish"""
        variants = self.question_variants if self.question_variants else []
        return [self.question] + variants
    
    def get_searchable_text(self):
        """Qidiruv uchun to'liq matn"""
        parts = [
            self.question,
            self.answer,
            self.short_answer,
            self.keywords,
            ' '.join(self.tags) if self.tags else '',
            ' '.join(self.question_variants) if self.question_variants else '',
        ]
        return ' '.join(filter(None, parts))


class DynamicInfo(models.Model):
    """
    O'zgaruvchan ma'lumotlar: sanalar, narxlar, raqamlar.
    Yillik yangilanadi va FAQ javoblarida ishlatiladi.
    """
    INFO_TYPES = [
        ('date', 'Sana'),
        ('price', 'Narx'),
        ('number', 'Raqam'),
        ('text', 'Matn'),
        ('contact', 'Aloqa'),
    ]
    
    key = models.CharField(max_length=100, unique=True, help_text="Kalit nomi. Masalan: admission_start_date")
    value = models.TextField(help_text="Qiymat")
    info_type = models.CharField(max_length=20, choices=INFO_TYPES, default='text')
    description = models.CharField(max_length=255, blank=True, help_text="Tavsif")
    
    # Yaroqlilik muddati
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = "Dinamik ma'lumot"
        verbose_name_plural = "Dinamik ma'lumotlar"
        ordering = ['key']
    
    def __str__(self):
        return f"{self.key}: {self.value[:50]}"
    
    @classmethod
    def get_value(cls, key, default=None):
        """Kalit bo'yicha qiymat olish"""
        try:
            info = cls.objects.get(key=key, is_active=True)
            return info.value
        except cls.DoesNotExist:
            return default


# =============================================================================
# CHAT MODELS - Suhbat modellari
# =============================================================================

class ChatSession(models.Model):
    """Chat session for multi-turn conversations."""
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Session metadata
    total_turns = models.PositiveIntegerField(default=0)
    last_intent = models.CharField(max_length=50, blank=True, help_text="Oxirgi savol intent'i")
    language = models.CharField(max_length=2, default='uz', choices=[('uz', 'O\'zbek'), ('ru', 'Русский'), ('en', 'English')], help_text="Suhbat tili")
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['created_at', 'is_active']),
            models.Index(fields=['language']),
            models.Index(fields=['session_id', 'is_active']),
            models.Index(fields=['-updated_at']),
        ]
    
    def __str__(self):
        return f"Session {self.session_id} - {self.user or 'Anonymous'}"
    
    def get_conversation_history(self, limit=5):
        """Oxirgi N ta turn'ni qaytarish - Optimized query"""
        # select_related() ishlatmaslik kerak chunki ConversationTurn session'ga FK
        # only() bilan faqat kerakli fieldlarni olish
        return list(
            self.turns.only('turn_number', 'user_message', 'bot_response', 'intent')
            .order_by('-turn_number')[:limit]
            .values('turn_number', 'user_message', 'bot_response', 'intent')
        )[::-1]  # Reverse to chronological


class ChatLog(models.Model):
    """
    Suhbatning to'liq auditi (Log) - faqat ko'rish va analiz uchun.
    Tizimning ishlashiga ta'sir qilmaydi, faqat audit uchun saqlanadi.
    """
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    turn_number = models.PositiveIntegerField()
    
    # Message logs
    user_message = models.TextField()
    bot_response = models.TextField()
    
    # Audit info (JSON formatida saqlash - DB yukini kamaytiradi)
    metadata = models.JSONField(
        default=dict, 
        help_text="Confidence, sources, response_time va boshqa meta-ma'lumotlar"
    )
    
    intent = models.CharField(max_length=50, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['turn_number']
        indexes = [
            models.Index(fields=['session', 'turn_number']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f"Log {self.turn_number}: {self.user_message[:50]}..."


class SessionMemory(models.Model):
    """
    AI uchun qisqa va tezkor xotira (Context).
    Har bir sessiya uchun bitta record - AI faqat buni ko'radi.
    """
    session = models.OneToOneField(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='memory'
    )
    summary = models.TextField(blank=True, help_text="Suhbatning qisqa mazmuni (AI tomonidan yangilanadi)")
    last_intent = models.CharField(max_length=50, blank=True)
    interaction_count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Session Memory"

    def __str__(self):
        return f"Memory for {self.session.session_id}"




class FrequentQuestion(models.Model):
    """Persisted frequent question for fast answers and curation."""
    question = models.TextField(unique=True)
    answer = models.TextField()
    hits = models.PositiveIntegerField(default=0)
    last_used = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-hits', '-last_used']

    def __str__(self):
        return self.question[:80]


class Feedback(models.Model):
    """User/admin feedback for QA pairs."""
    RATING_CHOICES = [
        ('positive', 'Yaxshi 👍'),
        ('negative', 'Yomon 👎'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('corrected', 'To\'g\'rilandi'),
        ('ignored', 'E\'tiborga olinmadi'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    chat_log = models.ForeignKey(ChatLog, on_delete=models.CASCADE, related_name='feedbacks', null=True, blank=True)
    rating = models.CharField(max_length=20, choices=RATING_CHOICES, blank=True)
    admin_notes = models.TextField(blank=True, help_text="Admin izohlar")
    
    # YANGI SODDA TO'G'RILASH FIELDS
    corrected_answer = models.TextField(blank=True, help_text="To'g'rilangan javob (admin tomonidan)")
    correction_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', help_text="To'g'rilash holati")
    corrected_at = models.DateTimeField(null=True, blank=True, help_text="To'g'rilangan vaqt")
    corrected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='corrections', help_text="Kim to'g'rilagan")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.chat_log:
            question = self.chat_log.user_message[:50]
            return f"Feedback: {self.rating} - {question}"
        return "Feedback"

    @property
    def is_negative(self):
        """Negative feedback ekanligini tekshirish"""
        return self.rating == 'negative'
    
    @property
    def needs_correction(self):
        """To'g'rilash kerakligini tekshirish"""
        return self.is_negative and self.correction_status == 'pending'


class ManualCorrection(models.Model):
    """Admin tomonidan qo'lda to'g'rilangan javoblar - keyinchalik foydalanish uchun."""
    question_pattern = models.TextField(help_text="Savol namunasi (regex yoki oddiy matn)")
    correct_answer = models.TextField(help_text="To'g'ri javob")
    priority = models.IntegerField(default=1, help_text="Yuqori raqam = yuqori ustuvorlik")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    usage_count = models.PositiveIntegerField(default=0, help_text="Necha marta ishlatilgan")

    class Meta:
        ordering = ['-priority', '-created_at']

    def __str__(self):
        return f"Manual: {self.question_pattern[:50]} -> {self.correct_answer[:50]}"


class OffenseLog(models.Model):
    """Log offensive/out-of-domain user inputs and offenders."""
    user_ident = models.CharField(max_length=200, null=True, blank=True)
    question = models.TextField()
    reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Offense by {self.user_ident or 'unknown'} at {self.created_at}"


class Document(models.Model):
    """Hujjatlar (PDF, Word, URL) - RAG knowledge base uchun."""
    
    DOC_TYPE_CHOICES = [
        ('pdf', 'PDF'),
        ('word', 'Word Document'),
        ('url', 'Web URL'),
        ('text', 'Text File'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('processing', 'Qayta ishlanmoqda'),
        ('completed', 'Tayyor'),
        ('failed', 'Xatolik'),
    ]
    
    # File upload va URL
    file = models.FileField(
        upload_to='documents/%Y/%m/',
        blank=True,
        null=True,
        help_text="PDF, Word yoki Text fayl yuklang"
    )
    url = models.URLField(
        blank=True,
        null=True,
        help_text="Veb-sahifa URL manzili"
    )
    
    # Metadata
    title = models.CharField(
        max_length=255,
        help_text="Hujjat nomi"
    )
    description = models.TextField(
        blank=True,
        help_text="Qisqacha tavsif"
    )
    doc_type = models.CharField(
        max_length=10,
        choices=DOC_TYPE_CHOICES,
        help_text="Hujjat turi"
    )
    
    # Processing status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Qayta ishlash holati"
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Qayta ishlangan vaqt"
    )
    chunks_created = models.PositiveIntegerField(
        default=0,
        help_text="Yaratilgan chunk'lar soni"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Xatolik xabari (agar bo'lsa)"
    )
    
    # Metadata
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_documents'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Hujjat"
        verbose_name_plural = "Hujjatlar"
    
    def __str__(self):
        return f"{self.title} ({self.get_doc_type_display()})"
    
    @property
    def is_ready(self):
        """Hujjat tayyor bo'lganligini tekshirish"""
        return self.status == 'completed'
    
    @property
    def has_error(self):
        """Xatolik borligini tekshirish"""
        return self.status == 'failed'
    
    def get_source(self):
        """Fayl yoki URL manbani qaytarish"""
        if self.file:
            return self.file.path
        return self.url


class DocumentChunk(models.Model):
    """
    Hujjat bo'laklari (Metadata) - Faqat qidiruv va manba ko'rsatish uchun.
    ASOSIY MATN ChromaDB da saqlanadi. PostgreSQL da faqat meta-ma'lumot.
    """
    document = models.ForeignKey(
        Document, 
        on_delete=models.CASCADE, 
        related_name='chunks'
    )
    chunk_index = models.PositiveIntegerField()
    
    # Metadata
    title = models.CharField(max_length=255, blank=True, help_text="Chunk sarlavhasi")
    char_count = models.PositiveIntegerField(default=0)
    
    # ChromaDB identifier
    chroma_id = models.CharField(max_length=100, unique=True, db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['document', 'chunk_index']
        unique_together = ['document', 'chunk_index']

    def __str__(self):
        return f"{self.document.title} [Chunk {self.chunk_index}]"


class ChatAnalytics(models.Model):
    """
    Har bir interaction uchun analytics.
    Monitoring va sifat nazorati uchun.
    """
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='analytics'
    )
    
    # Request info
    query = models.TextField()
    query_length = models.IntegerField(default=0)
    intent = models.CharField(max_length=50, db_index=True, blank=True)
    detected_language = models.CharField(max_length=10, default='uz')
    
    # Response info
    response = models.TextField(blank=True)
    response_length = models.IntegerField(default=0)
    response_time = models.FloatField(default=0.0)  # seconds
    was_cached = models.BooleanField(default=False)
    
    # Quality metrics
    confidence_score = models.FloatField(default=0.0)
    validation_score = models.FloatField(default=0.0)
    hallucination_risk = models.FloatField(default=0.0)
    grounding_score = models.FloatField(default=0.0)
    
    # Sources
    sources_count = models.IntegerField(default=0)
    top_source_confidence = models.FloatField(default=0.0)
    sources_used = models.JSONField(default=list)
    search_type = models.CharField(
        max_length=20,
        default='hybrid',
        choices=[
            ('semantic', 'Semantic Search'),
            ('keyword', 'Keyword Search'),
            ('hybrid', 'Hybrid Search'),
        ]
    )
    
    # User feedback (later filled)
    user_rating = models.IntegerField(null=True, blank=True)  # 1-5
    user_feedback_text = models.TextField(blank=True)
    
    # Technical
    error_occurred = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'intent']),
            models.Index(fields=['confidence_score']),
            models.Index(fields=['error_occurred']),
        ]
        verbose_name = "Chat Analytics"
        verbose_name_plural = "Chat Analytics"
    
    def __str__(self):
        return f"{self.timestamp}: {self.query[:50]}..."


class DailyStats(models.Model):
    """
    Kunlik agregatsiya - dashboard uchun.
    Celery task yoki cron job bilan yangilanadi.
    """
    date = models.DateField(unique=True, db_index=True)
    
    # Volume
    total_queries = models.IntegerField(default=0)
    unique_sessions = models.IntegerField(default=0)
    
    # Performance
    avg_response_time = models.FloatField(default=0.0)
    cache_hit_rate = models.FloatField(default=0.0)  # percentage
    
    # Quality
    avg_confidence = models.FloatField(default=0.0)
    avg_validation_score = models.FloatField(default=0.0)
    error_rate = models.FloatField(default=0.0)  # percentage
    hallucination_count = models.IntegerField(default=0)
    
    # Intent distribution (JSON)
    top_intents = models.JSONField(default=dict)
    
    # User satisfaction
    avg_user_rating = models.FloatField(null=True, blank=True)
    feedback_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-date']
        verbose_name = "Daily Stats"
        verbose_name_plural = "Daily Stats"
    
    def __str__(self):
        return f"Stats for {self.date}"
