"""
UzSWLU Chatbot Admin Panel
"""
from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from django.utils import timezone
from .models import (
    Category, Topic, FAQ, DynamicInfo,
    ChatSession, Document, DocumentChunk,
    ChatLog, SessionMemory
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['icon_display', 'name', 'name_uz', 'faq_count_display', 'is_active', 'order']
    list_filter = ['is_active']
    search_fields = ['name', 'name_uz', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']
    list_editable = ['order', 'is_active']
    
    def icon_display(self, obj):
        return obj.icon if obj.icon else '📁'
    icon_display.short_description = ''
    
    def faq_count_display(self, obj):
        count = obj.faqs.filter(is_active=True).count()
        return format_html('<span style="color: green; font-weight: bold;">{}</span>', count)
    faq_count_display.short_description = 'FAQs'


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'faq_count', 'is_active', 'order']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'name_uz', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['category', 'order', 'name']
    list_editable = ['order', 'is_active']
    
    def faq_count(self, obj):
        return obj.faqs.filter(is_active=True).count()
    faq_count.short_description = 'FAQs'


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = [
        'short_question', 'category', 'priority_badge', 
        'view_count', 'is_active', 'is_verified', 'updated_at'
    ]
    list_filter = ['category', 'priority', 'is_active', 'is_verified']
    search_fields = ['question', 'answer', 'keywords']
    ordering = ['-priority', '-view_count']
    list_editable = ['is_active', 'is_verified']
    date_hierarchy = 'created_at'
    readonly_fields = ['view_count', 'helpful_count', 'not_helpful_count', 'last_used_at', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Savol va Javob', {
            'fields': ('question', 'question_variants', 'answer', 'short_answer')
        }),
        ('Kategoriya', {
            'fields': ('category', 'topic')
        }),
        ('Teglar', {
            'fields': ('tags', 'keywords'),
            'classes': ('collapse',)
        }),
        ('Manbalar', {
            'fields': ('source_url', 'source_name'),
            'classes': ('collapse',)
        }),
        ('Sozlamalar', {
            'fields': ('priority', 'is_active', 'is_verified', 'embedding_updated')
        }),
        ('Statistika', {
            'fields': ('view_count', 'helpful_count', 'not_helpful_count', 'last_used_at'),
            'classes': ('collapse',)
        }),
    )
    
    def short_question(self, obj):
        q = obj.question[:60]
        return q + "..." if len(obj.question) > 60 else q
    short_question.short_description = 'Savol'
    
    def priority_badge(self, obj):
        colors = {1: 'gray', 2: 'blue', 3: 'orange', 4: 'red'}
        labels = {1: 'Past', 2: "O'rta", 3: 'Yuqori', 4: 'Muhim'}
        color = colors.get(obj.priority, 'gray')
        label = labels.get(obj.priority, 'N/A')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 4px;">{}</span>',
            color, label
        )
    priority_badge.short_description = 'Prioritet'


@admin.register(DynamicInfo)
class DynamicInfoAdmin(admin.ModelAdmin):
    list_display = ['key', 'short_value', 'info_type', 'is_active', 'updated_at']
    list_filter = ['info_type', 'is_active']
    search_fields = ['key', 'value', 'description']
    ordering = ['key']
    list_editable = ['is_active']
    
    def short_value(self, obj):
        v = str(obj.value)[:50]
        return v + "..." if len(str(obj.value)) > 50 else v
    short_value.short_description = 'Qiymat'


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id_short', 'user', 'total_turns', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['session_id']
    readonly_fields = ['session_id', 'total_turns', 'created_at', 'updated_at']
    ordering = ['-updated_at']
    
    def session_id_short(self, obj):
        return str(obj.session_id)[:8] + "..."
    session_id_short.short_description = 'Session'


@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'session_id_short', 'turn_number', 'intent', 'timestamp']
    list_filter = ['timestamp', 'intent']
    search_fields = ['user_message', 'bot_response']
    readonly_fields = ['timestamp']
    
    def session_id_short(self, obj):
        return str(obj.session.session_id)[:8] + "..."
    session_id_short.short_description = 'Session'


@admin.register(SessionMemory)
class SessionMemoryAdmin(admin.ModelAdmin):
    list_display = ['session_id_short', 'interaction_count', 'updated_at']
    readonly_fields = ['updated_at']
    
    def session_id_short(self, obj):
        return str(obj.session.session_id)[:8] + "..."
    session_id_short.short_description = 'Session'


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ['document', 'chunk_index', 'char_count', 'created_at']
    list_filter = ['document', 'created_at']
    search_fields = ['document__title', 'chroma_id']
    readonly_fields = ['document', 'chunk_index', 'chroma_id', 'char_count', 'created_at']




@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = [
        'id','title', 'doc_type', 'status_badge', 'chunks_created',
        'created_at', 'processed_at'
    ]
    list_filter = ['doc_type', 'status', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = [
        'status', 'processed_at', 'chunks_created',
        'error_message', 'created_at', 'updated_at'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Hujjat ma\'lumotlari', {
            'fields': ('title', 'description', 'doc_type')
        }),
        ('Fayl yuklash', {
            'fields': ('file',),
            'description': 'PDF, Word (.docx) yoki Text (.txt) fayl yuklang'
        }),
        ('Holat', {
            'fields': ('status', 'processed_at', 'chunks_created', 'error_message'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'processing': '#17a2b8',
            'completed': '#28a745',
            'failed': '#dc3545'
        }
        labels = {
            'pending': '⏳ Kutilmoqda',
            'processing': '🔄 Ishlanmoqda',
            'completed': '✅ Tayyor',
            'failed': '❌ Xatolik'
        }
        color = colors.get(obj.status, '#6c757d')
        label = labels.get(obj.status, obj.status)
        return format_html(
            '<span style="background: {}; color: white; '
            'padding: 3px 8px; border-radius: 4px; font-size: 11px;">'
            '{}</span>',
            color, label
        )
    status_badge.short_description = 'Holat'
    
    actions = ['process_documents', 'reprocess_documents']
    
    def process_documents(self, request, queryset):
        """Tanlangan hujjatlarni qayta ishlash."""
        from document_processor import doc_rag
        
        success_count = 0
        error_count = 0
        
        for doc in queryset.filter(status='pending'):
            doc.status = 'processing'
            doc.save()
            
            result = doc_rag.process_and_store(doc)
            
            if result['success']:
                doc.status = 'completed'
                doc.chunks_created = result['chunks_created']
                doc.processed_at = timezone.now()
                doc.error_message = ''
                success_count += 1
            else:
                doc.status = 'failed'
                doc.error_message = result['error']
                error_count += 1
            
            doc.save()
        
        messages.success(
            request,
            f'{success_count} ta hujjat muvaffaqiyatli ishlandi. '
            f'{error_count} ta xatolik.'
        )
    process_documents.short_description = "📄 Tanlangan hujjatlarni qayta ishlash"
    
    def reprocess_documents(self, request, queryset):
        """Hujjatlarni qaytadan qayta ishlash."""
        queryset.update(status='pending', chunks_created=0, error_message='')
        self.process_documents(request, queryset)
    reprocess_documents.short_description = "🔄 Qaytadan qayta ishlash"
    
    def save_model(self, request, obj, form, change):
        """Saqlashda avtomatik doc_type aniqlash va qayta ishlash."""
        # Avtomatik doc_type aniqlash
        if obj.file and not obj.doc_type:
            ext = obj.file.name.split('.')[-1].lower()
            type_map = {'pdf': 'pdf', 'docx': 'word', 'doc': 'word', 'txt': 'text'}
            obj.doc_type = type_map.get(ext, 'text')
        
        # Statusni 'pending' ga o'rnatish (yangi hujjat uchun)
        if not change:
            obj.status = 'pending'
        
        # Saqlash
        super().save_model(request, obj, form, change)
        
        # Yangi hujjat yuklanganda yoki fayl o'zgarganda avtomatik qayta ishlash
        should_process = False
        if not change:  # Yangi hujjat
            should_process = True
        elif change and obj.file:  # Fayl o'zgartirilgan
            # Eski versiyani olish
            try:
                old_obj = Document.objects.get(pk=obj.pk)
                if old_obj.file != obj.file:
                    should_process = True
            except Document.DoesNotExist:
                should_process = True
        
        if should_process and obj.file and obj.status == 'pending':
            # Background'da qayta ishlash - daemon thread
            import threading
            import time
            import logging
            from django.db import connections
            
            # Logger yaratish
            logger = logging.getLogger(__name__)
            
            # Obj'ning ID'sini saqlash (thread'da ishlatish uchun)
            doc_id = obj.pk
            doc_title = obj.title
            
            def process_in_background():
                """Background thread'da hujjatni qayta ishlash. Django setup bilan."""
                try:
                    # Django setup - thread'da ishlash uchun (faqat bir marta)
                    import django
                    from django.conf import settings
                    if not settings.configured:
                        django.setup()
                    
                    # Logger'ni qayta yaratish (thread'da)
                    logger = logging.getLogger(__name__)
                    logger.info(f"🔄 Background thread ishga tushdi: Hujjat ID={doc_id}")
                    
                    # Kichik kechikish - database commit uchun
                    time.sleep(2)
                    
                    # Obj'ni qayta yuklash
                    from .models import Document
                    doc = Document.objects.get(pk=doc_id)
                    doc.status = 'processing'
                    doc.save(update_fields=['status'])
                    logger.info(f"📄 Hujjat '{doc.title}' qayta ishlanmoqda...")
                    logger.info(f"📄 File path: {doc.file.path if doc.file else 'N/A'}")
                    
                    # Document processor'ni import qilish
                    from document_processor import doc_rag
                    result = doc_rag.process_and_store(doc)
                    
                    # Natijani saqlash
                    doc.refresh_from_db()
                    if result['success']:
                        doc.status = 'completed'
                        doc.chunks_created = result['chunks_created']
                        doc.processed_at = timezone.now()
                        doc.error_message = ''
                        doc.save()
                        logger.info(f"✅ Hujjat '{doc.title}' muvaffaqiyatli qayta ishlandi: {result['chunks_created']} chunk yaratildi")
                    else:
                        doc.status = 'failed'
                        doc.error_message = result.get('error', 'Noma\'lum xatolik')[:500]  # Limit error length
                        doc.save()
                        logger.error(f"❌ Hujjat '{doc.title}' qayta ishlashda xatolik: {result.get('error')}")
                    
                    # Database connection'ni yopish
                    connections.close_all()
                    
                except Exception as e:
                    import traceback
                    error_trace = traceback.format_exc()
                    logger.error(f"❌ Hujjat qayta ishlashda xatolik: {e}")
                    logger.error(f"Traceback: {error_trace}")
                    try:
                        import django
                        from django.conf import settings
                        if not settings.configured:
                            django.setup()
                        from .models import Document
                        doc = Document.objects.get(pk=doc_id)
                        doc.status = 'failed'
                        doc.error_message = str(e)[:500]  # Limit error length
                        doc.save()
                        logger.error(f"❌ Xatolik saqlandi: {str(e)[:500]}")
                    except Exception as inner_e:
                        logger.error(f"❌ Xatolikni saqlashda muammo: {inner_e}")
                    finally:
                        connections.close_all()
            
            # Thread'da ishlatish - daemon thread (main process o'lganda to'xtaydi)
            thread = threading.Thread(target=process_in_background, daemon=True)
            thread.start()
            logger.info(f"🔄 Hujjat '{doc_title}' (ID: {doc_id}) qayta ishlash boshlandi (background thread ID: {thread.ident})...")
            print(f"🔄 Hujjat '{doc_title}' qayta ishlash boshlandi (thread ID: {thread.ident})")


admin.site.site_header = "UzSWLU Chatbot Admin"
admin.site.site_title = "UzSWLU Chatbot"
admin.site.index_title = "Ma'lumotlar bazasini boshqarish"
