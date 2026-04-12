from django.db import models
from django.utils import timezone


class BotConfiguration(models.Model):
    """Stores the AI Agent configuration per shop."""
    LANGUAGE_CHOICES = [('AUTO', 'Auto-detect'), ('FR', 'French'), ('AR', 'Arabizi'), ('EN', 'English')]

    shop_id        = models.CharField(max_length=255, unique=True)
    shop_name      = models.CharField(max_length=255, blank=True, null=True)
    language       = models.CharField(max_length=4, choices=LANGUAGE_CHOICES, default='FR')
    ai_agent_name  = models.CharField(max_length=255, default="Tiktak AI")
    custom_intents = models.JSONField(default=dict, blank=True)

    bot_enabled     = models.BooleanField(default=True)
    bot_disabled_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Config for {self.shop_id} ({self.language})"
