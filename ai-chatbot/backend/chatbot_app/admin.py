"""
UzSWLU Professional Chatbot Admin Panel
"""
from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from django.utils import timezone
from .models import (
    Category, FAQ, FAQTranslation, DynamicInfo,
    Conversation, Message, Document, DocumentChunk,
    Feedback, ChatAnalytics
)


class FAQTranslationInline(admin.TabularInline):
    model = FAQTranslation
    extra = 1
    fields = ['lang', 'question', 'answer']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['icon_display', 'name', 'slug', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    
    def icon_display(self, obj):
        return obj.icon if obj.icon else '📁'
    icon_display.short_description = ''


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['id', 'category', 'status', 'order', 'created_at']
    list_filter = ['category', 'status']
    inlines = [FAQTranslationInline]
    ordering = ['category', 'order', '-created_at']


@admin.register(FAQTranslation)
class FAQTranslationAdmin(admin.ModelAdmin):
    list_display = ['faq', 'lang', 'question_short']
    list_filter = ['lang']
    search_fields = ['question', 'answer']
    readonly_fields = ['question_tsv', 'answer_tsv']

    def question_short(self, obj):
        return obj.question[:60] + "..." if len(obj.question) > 60 else obj.question


@admin.register(DynamicInfo)
class DynamicInfoAdmin(admin.ModelAdmin):
    list_display = ['key', 'value_short', 'is_active', 'updated_at']
    list_editable = ['is_active']
    search_fields = ['key', 'value']

    def value_short(self, obj):
        return obj.value[:50] + "..." if len(obj.value) > 50 else obj.value


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ['sender_type', 'lang', 'text', 'created_at']
    can_delete = False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_id', 'platform', 'created_at']
    list_filter = ['platform', 'created_at']
    inlines = [MessageInline]
    readonly_fields = ['id', 'created_at']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['conversation_id_short', 'sender_type', 'lang', 'text_short', 'created_at']
    list_filter = ['sender_type', 'lang', 'created_at']
    search_fields = ['text']
    
    def conversation_id_short(self, obj):
        return str(obj.conversation_id)[:8]
    
    def text_short(self, obj):
        return obj.text[:60] + "..." if len(obj.text) > 60 else obj.text


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'source_type', 'lang', 'status_badge', 'version', 'created_at']
    list_filter = ['source_type', 'lang', 'status']
    search_fields = ['title']
    readonly_fields = ['status', 'created_at', 'updated_at']

    def status_badge(self, obj):
        colors = {
            'uploaded': '#6c757d',
            'processing': '#17a2b8',
            'ready': '#28a745',
            'failed': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 4px;">{}</span>',
            color, obj.get_status_display()
        )
    def save_model(self, request, obj, form, change):
        """Muvaffaqiyatli saqlangandan keyin background processingni boshlash."""
        super().save_model(request, obj, form, change)
        
        # Agar yangi fayl yuklangan bo'lsa yoki o'zgartirilgan bo'lsa
        if 'file_path' in form.changed_data or not change:
            from .tasks import process_document_task
            # Taskni kechiktirib yuborish (Celery or synchronous fallback)
            process_document_task.delay(obj.id)
            messages.info(request, f"'{obj.title}' hujjatni qayta ishlash boshlandi. Kutilmoqda...")


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ['document', 'lang', 'chunk_index', 'embedding_id']
    list_filter = ['lang', 'document']
    search_fields = ['chunk_text']




@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['message_short', 'is_positive', 'created_at']
    list_filter = ['is_positive']
    
    def message_short(self, obj):
        return obj.message.text[:50]


admin.site.site_header = "UzSWLU Professional Chatbot Admin"
admin.site.site_title = "UzSWLU Chatbot"
admin.site.index_title = "Knowledge Base Management"


@admin.register(ChatAnalytics)
class ChatAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'status_icon',
        'message_link',
        'response_time',
        'confidence_score',
        'is_cache_hit',
        'language',
        'created_at'
    ]
    list_filter = ['is_cache_hit', 'language', 'source_type', 'created_at']
    readonly_fields = ['message', 'response_time', 'confidence_score', 'source_type', 'is_cache_hit', 'language', 'tokens_used', 'error_log', 'created_at']

    def status_icon(self, obj):
        if obj.error_log:
            return format_html('<span title="{}" style="color: #ef4444; font-size: 18px;">⚠️</span>', obj.error_log[:100])
        return format_html('<span style="color: #10b981; font-size: 18px;">✅</span>')
    status_icon.short_description = 'Status'

    def message_link(self, obj):
        return obj.message.text[:50]
    message_link.short_description = 'Message'
