from django.db import models
from django.utils import timezone


class ResponseTemplate(models.Model):
    """Per-shop, multilingual response template stored in DB."""
    LANGUAGE_CHOICES = [('FR', 'Français'), ('AR', 'Arabe'), ('EN', 'Anglais')]
    TEMPLATE_TYPE_CHOICES = [
        ('response', 'Réponse intent'), ('missing_entity', 'Entité manquante'),
        ('out_of_stock', 'Rupture de stock'), ('order_confirmed', 'Commande confirmée'),
        ('disambiguation', 'Disambiguation'), ('misc', 'Divers'),
    ]

    shop_id             = models.CharField(max_length=255, blank=True, null=True)
    language            = models.CharField(max_length=5, choices=LANGUAGE_CHOICES)
    template_type       = models.CharField(max_length=30, choices=TEMPLATE_TYPE_CHOICES)
    intent              = models.CharField(max_length=100)
    text                = models.TextField()
    available_variables = models.JSONField(default=list, blank=True)
    is_default          = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('shop_id', 'language', 'template_type', 'intent')]
        ordering = ['template_type', 'language', 'intent']
        verbose_name = "Response Template"
        verbose_name_plural = "Response Templates"

    def __str__(self):
        return f"[{self.language}] {self.template_type}/{self.intent} ({self.shop_id or 'DEFAULT'})"
