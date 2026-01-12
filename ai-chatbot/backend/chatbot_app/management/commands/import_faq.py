"""
Import FAQ data from JSON file to database
Usage: python manage.py import_faq
"""
import json
from django.core.management.base import BaseCommand
from chatbot_app.models import Category, FAQ


# Mapping: JSON title -> Category name
CATEGORY_MAPPING = {
    'About UzSWLU': 'General',
    'University History': 'General',
    'University Statistics': 'General',
    'List of Faculties': 'Faculties',
    'Faculty of English #1': 'Faculties',
    'Faculty of English #2': 'Faculties',
    'Faculty of English Philology': 'Faculties',
    'Admission Process': 'Admission',
    'Tuition and Scholarships': 'Tuition',
    'Study Duration': 'Academic',
    'Student Life': 'Student Life',
    'Career Opportunities': 'Career',
    'Address and Contact': 'Contact',
    'Rector Information': 'Contact',
    'International Partnerships': 'International',
    'Joint Programs': 'International',
    'UzSWLU Awards and Rankings': 'General',
}

# Categories to create
CATEGORIES = [
    {'name': 'General', 'name_uz': 'Umumiy', 'slug': 'general', 'icon': '🏛️', 'order': 1},
    {'name': 'Admission', 'name_uz': 'Qabul', 'slug': 'admission', 'icon': '📋', 'order': 2},
    {'name': 'Faculties', 'name_uz': 'Fakultetlar', 'slug': 'faculties', 'icon': '🎓', 'order': 3},
    {'name': 'Tuition', 'name_uz': 'To\'lov', 'slug': 'tuition', 'icon': '💰', 'order': 4},
    {'name': 'Academic', 'name_uz': 'O\'qish', 'slug': 'academic', 'icon': '📚', 'order': 5},
    {'name': 'Student Life', 'name_uz': 'Talaba hayoti', 'slug': 'student-life', 'icon': '🎉', 'order': 6},
    {'name': 'Career', 'name_uz': 'Karyera', 'slug': 'career', 'icon': '💼', 'order': 7},
    {'name': 'International', 'name_uz': 'Xalqaro', 'slug': 'international', 'icon': '🌍', 'order': 8},
    {'name': 'Contact', 'name_uz': 'Aloqa', 'slug': 'contact', 'icon': '📞', 'order': 9},
]


class Command(BaseCommand):
    help = 'Import FAQ data from uzswlu_knowledge_en.json'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default='uzswlu_knowledge_en.json',
            help='JSON file path'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing FAQs before import'
        )
    
    def handle(self, *args, **options):
        self.stdout.write("Starting FAQ import...")
        
        # Create categories
        self.stdout.write("Creating categories...")
        for cat_data in CATEGORIES:
            cat, created = Category.objects.get_or_create(
                slug=cat_data['slug'],
                defaults=cat_data
            )
            status = "Created" if created else "Exists"
            self.stdout.write(f"  {cat_data['icon']} {cat_data['name']}: {status}")
        
        # Clear existing FAQs if requested
        if options['clear']:
            FAQ.objects.all().delete()
            self.stdout.write(self.style.WARNING("Cleared all existing FAQs"))
        
        # Load JSON file
        file_path = options['file']
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return
        
        # Import FAQs
        self.stdout.write(f"\nImporting {len(data)} FAQs...")
        created_count = 0
        updated_count = 0
        
        for item in data:
            title = item.get('title', '')
            text = item.get('text', '')
            
            if not text:
                continue
            
            # Find category
            category_name = CATEGORY_MAPPING.get(title, 'General')
            try:
                category = Category.objects.get(name=category_name)
            except Category.DoesNotExist:
                category = Category.objects.get(name='General')
            
            # Create question from title
            question = f"Tell me about {title}" if title else text[:100]
            
            # Extract keywords from text
            keywords = self._extract_keywords(text)
            
            # Create or update FAQ
            faq, created = FAQ.objects.update_or_create(
                question=question,
                defaults={
                    'category': category,
                    'answer': text,
                    'short_answer': text[:200] if len(text) > 200 else text,
                    'keywords': ', '.join(keywords),
                    'tags': keywords[:5],
                    'source_name': item.get('source', 'manual'),
                    'priority': 2,
                    'is_active': True,
                    'is_verified': True,
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
        
        self.stdout.write(self.style.SUCCESS(
            f"\nImport complete! Created: {created_count}, Updated: {updated_count}"
        ))
        
        # Show summary
        self.stdout.write("\nCategory summary:")
        for cat in Category.objects.all():
            count = cat.faqs.count()
            self.stdout.write(f"  {cat.icon} {cat.name}: {count} FAQs")
    
    def _extract_keywords(self, text):
        """Extract important keywords from text"""
        # Common words to exclude
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'shall',
            'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
            'for', 'on', 'with', 'at', 'by', 'from', 'up', 'about',
            'into', 'over', 'after', 'and', 'or', 'but', 'if', 'because',
            'as', 'until', 'while', 'this', 'that', 'these', 'those',
            'it', 'its', 'they', 'their', 'them', 'he', 'she', 'his', 'her'
        }
        
        # Extract words
        words = text.lower().split()
        keywords = []
        
        for word in words:
            # Clean word
            clean = ''.join(c for c in word if c.isalnum())
            
            # Check if valid keyword
            if clean and len(clean) > 3 and clean not in stop_words:
                if clean not in keywords:
                    keywords.append(clean)
        
        return keywords[:10]
