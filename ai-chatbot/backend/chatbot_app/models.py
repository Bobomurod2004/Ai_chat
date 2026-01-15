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
    short_answer = models.CharField(max_length=255, blank=True)
    embedding_id = models.CharField(max_length=100, blank=True)
    
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
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    version = models.PositiveIntegerField(default=1)
    
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
    """
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    lang = models.CharField(max_length=2, choices=FAQTranslation.LANGUAGE_CHOICES, default='uz')
    chunk_text = models.TextField(default='')
    chunk_index = models.PositiveIntegerField()
    
    # Metadata
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
    """
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
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


class SearchLog(models.Model):
    """
    Audit log for searches to track performance and missing content.
    """
    FOUND_TYPE_CHOICES = [
        ('faq', 'FAQ'),
        ('doc', 'Document'),
        ('none', 'Not Found'),
    ]
    
    query = models.TextField()
    lang = models.CharField(max_length=2, choices=FAQTranslation.LANGUAGE_CHOICES, default='uz')
    found_type = models.CharField(max_length=10, choices=FOUND_TYPE_CHOICES, default='none')
    latency_ms = models.PositiveIntegerField(help_text="Search latency in milliseconds", default=0)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.lang} | {self.found_type} | {self.query[:50]}"


class Feedback(models.Model):
    """User feedback for quality improvement."""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='feedbacks', null=True, blank=True)
    is_positive = models.BooleanField(default=False)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
