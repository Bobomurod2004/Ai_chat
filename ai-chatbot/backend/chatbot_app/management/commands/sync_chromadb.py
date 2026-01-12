"""
Sync FAQs from database to ChromaDB
Usage: python manage.py sync_chromadb
"""
from django.core.management.base import BaseCommand
from rag_service import sync_faqs_to_chromadb


class Command(BaseCommand):
    help = 'Sync FAQ data from PostgreSQL to ChromaDB'
    
    def handle(self, *args, **options):
        self.stdout.write("Syncing FAQs to ChromaDB...")
        count = sync_faqs_to_chromadb()
        self.stdout.write(self.style.SUCCESS(f"Synced {count} FAQs"))
