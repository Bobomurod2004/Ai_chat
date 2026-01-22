from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
import uuid


# =============================================================================
# KNOWLEDGE BASE MODELS - Professional Multilingual Architecture
# =============================================================================

class Category(models.Model):
    """
    Asosiy kategoriyalar: Admission, Faculties, Tuition, etc.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Emoji yoki icon nomi")
    order = models.PositiveIntegerField(default=0, help_text="Tartib raqami")
    is_active = models.BooleanField(default=True)
    intent_keywords = models.JSONField(default=list, blank=True, help_text="Keywords to trigger this category intent")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"
        ordering = ['order', 'name']
    
    def __str__(self):
        return f"{self.icon} {self.name}" if self.icon else self.name


class FAQ(models.Model):
    """
    Professional FAQ Container. 
    Actual content is in FAQTranslation to separate languages properly.
    """
    STATUS_CHOICES = [
        ('draft', 'Qoralama'),
        ('published', 'Chop etilgan'),
        ('archived', 'Arxivlangan'),
    ]
    
    canonical_id = models.UUIDField(default=uuid.uuid4, unique=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='faqs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='published')
    order = models.PositiveIntegerField(default=0)
    is_current = models.BooleanField(default=True, help_text="Is this information up to date?")
    year = models.PositiveIntegerField(default=2024, help_text="The year this information applies to")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQlar"
        ordering = ['category', 'order', '-created_at']

    def __str__(self):
        first_trans = self.translations.first()
        return first_trans.question[:60] if first_trans else f"FAQ ID: {self.id}"


class FAQTranslation(models.Model):
    """
    Multilingual FAQ Content with PostgreSQL Full-Text Search support.
    v6.0: Added dynamic_variables for automatic DynamicInfo integration.
    """
    LANGUAGE_CHOICES = [
        ('uz', 'O\'zbek'),
        ('ru', 'Русский'),
        ('en', 'English'),
    ]
    
    faq = models.ForeignKey(FAQ, on_delete=models.CASCADE, related_name='translations')
    lang = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='uz')
    question = models.TextField()
    answer = models.TextField()
    question_variants = models.JSONField(default=list)
    embedding_id = models.CharField(max_length=100, blank=True)
    
    # v6.0: Dynamic Variables Support
    dynamic_variables = models.JSONField(default=list, blank=True, help_text="DynamicInfo keys used in answer (e.g., ['tuition_fee_journalism'])")
    
    # PostgreSQL Full-Text Search fields
    question_tsv = SearchVectorField(null=True, blank=True)
    answer_tsv = SearchVectorField(null=True, blank=True)
    
    class Meta:
        verbose_name = "FAQ Tarjimasi"
        verbose_name_plural = "FAQ Tarjimalari"
        unique_together = ['faq', 'lang']
        indexes = [
            models.Index(fields=['lang']),
            GinIndex(fields=['question_tsv']),
            GinIndex(fields=['answer_tsv']),
        ]
    
    def __str__(self):
        return f"[{self.lang.upper()}] {self.question[:50]}"


class Document(models.Model):
    """
    Professional Document Model for RAG.
    """
    SOURCE_TYPES = [
        ('pdf', 'PDF'),
        ('doc', 'Word'),
        ('html', 'Web/HTML'),
        ('text', 'Text'),
    ]
    
    STATUS_CHOICES = [
        ('uploaded', 'Yuklangan'),
        ('processing', 'Qayta ishlanmoqda'),
        ('ready', 'Tayyor'),
        ('failed', 'Xatolik'),
    ]
    
    title = models.CharField(max_length=255)
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPES, default='pdf')
    file_path = models.FileField(upload_to='documents/%Y/%m/', blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    lang = models.CharField(max_length=2, choices=FAQTranslation.LANGUAGE_CHOICES, default='uz', db_index=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    version = models.PositiveIntegerField(default=1)
    is_current = models.BooleanField(default=True)
    year = models.PositiveIntegerField(default=2024)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Hujjat"
        verbose_name_plural = "Hujjatlar"
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class DocumentChunk(models.Model):
    """
    Document parts stored in DB for Hybrid Search (Postgres + Vector).
    Enhanced with v6.0 metadata for better context preservation.
    """
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    lang = models.CharField(max_length=2, choices=FAQTranslation.LANGUAGE_CHOICES, default='uz')
    chunk_text = models.TextField(default='')
    chunk_index = models.PositiveIntegerField()
    
    # v6.0: Enhanced Metadata for Table/Section Context
    section_title = models.CharField(max_length=500, blank=True, help_text="Section or heading this chunk belongs to")
    table_headers = models.JSONField(default=list, blank=True, help_text="Column headers if from table")
    parent_context = models.TextField(blank=True, help_text="Parent document/section context")
    row_data = models.JSONField(default=dict, blank=True, help_text="Structured row data if from table")
    
    # Vector DB Metadata
    embedding_id = models.CharField(max_length=100, unique=True, db_index=True, null=True, blank=True, help_text="ID in Vector DB (Qdrant/Chroma)")
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['document', 'chunk_index']
        unique_together = ['document', 'chunk_index']

    def __str__(self):
        return f"{self.document.title} [Chunk {self.chunk_index}]"


class DynamicInfo(models.Model):
    """
    Dinamik ma'lumotlar (sanalar, narxlar) - FAQ ichida ishlatish uchun.
    v6.0: Added multilingual support (value_uz, value_ru, value_en).
    """
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField(help_text="Deprecated: use value_uz instead")
    
    # v6.0: Multilingual Values
    value_uz = models.TextField(blank=True, help_text="Value in Uzbek")
    value_ru = models.TextField(blank=True, help_text="Value in Russian")
    value_en = models.TextField(blank=True, help_text="Value in English")
    
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    intent_keywords = models.JSONField(default=list, blank=True, help_text="Keywords to trigger this dynamic info")
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Dinamik ma'lumot"
        verbose_name_plural = "Dinamik ma'lumotlar"

    def __str__(self):
        return self.key


# =============================================================================
# CHAT & AUDIT MODELS - Professional Monitoring
# =============================================================================

class Conversation(models.Model):
    """
    Optimized for high volume. Supports anonymous web users via user_id.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.CharField(max_length=100, db_index=True)
    platform = models.CharField(max_length=20, default='web')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Conv {str(self.id)[:8]} ({self.user_id})"


class Message(models.Model):
    """
    Individual chat messages.
    """
    SENDER_CHOICES = [
        ('user', 'User'),
        ('bot', 'Bot'),
        ('system', 'System'),
    ]
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender_type = models.CharField(max_length=10, choices=SENDER_CHOICES, default='user')
    lang = models.CharField(max_length=2, choices=FAQTranslation.LANGUAGE_CHOICES, default='uz')
    text = models.TextField(default='')
    metadata = models.JSONField(default=dict, blank=True, help_text="Sources, feedback, etc.")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender_type}: {self.text[:50]}"




class Feedback(models.Model):
    """User feedback for quality improvement."""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='feedbacks', null=True, blank=True)
    is_positive = models.BooleanField(default=False)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']


class ChatAnalytics(models.Model):
    """
    Professional Analytics for RAG performance tracking.
    """
    message = models.OneToOneField(Message, on_delete=models.CASCADE, related_name='analytics')
    response_time = models.FloatField(help_text="Response time in seconds")
    confidence_score = models.FloatField(default=0.0)
    source_type = models.CharField(max_length=50, blank=True)  # faq, chroma, hybrid, none
    is_cache_hit = models.BooleanField(default=False)
    language = models.CharField(max_length=10)
    tokens_used = models.PositiveIntegerField(default=0)
    error_log = models.TextField(blank=True, null=True, help_text="Raw error logs if failure occurred")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Chat Analitikasi"
        verbose_name_plural = "Chat Analitikalari"
        ordering = ['-created_at']

    def __str__(self):
        return f"Analytics for Msg {self.message_id}"
