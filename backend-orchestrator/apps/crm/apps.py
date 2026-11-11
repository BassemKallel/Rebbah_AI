from django.apps import AppConfig

class CrmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.crm'

    def ready(self):
        import apps.crm.signals  # noqa: F401 — register post_delete signal
