"""
core/celery.py — Celery Application Entry Point

Initializes the Celery application, links it to Django settings,
and auto-discovers tasks declared in all INSTALLED_APPS.

The broker and result backend both point to the existing Redis container
already used for the debouncer hot memory and sliding window buffer.
"""
import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('rebbah_core')

# Namespace 'CELERY' means all celery-related configuration keys
# in settings.py must start with the CELERY_ prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Automatically discover tasks defined in any tasks.py file
# within each Django application registered in INSTALLED_APPS.
app.autodiscover_tasks()
