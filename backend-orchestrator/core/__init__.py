# This exposes the Celery app at package-level so that @shared_task
# decorators throughout the project can always find the app.
from .celery import app as celery_app

__all__ = ('celery_app',)
