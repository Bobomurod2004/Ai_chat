"""
Celery Configuration for UzSWLU Chatbot
Asynchronous task processing for Ollama requests and document processing
"""
import os
from celery import Celery

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_project.settings')

# Create Celery app
app = Celery('chatbot_project')

# Load config from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery."""
    print(f'Request: {self.request!r}')
