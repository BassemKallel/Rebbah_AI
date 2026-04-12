from django.db import models
from django.utils import timezone


class NLUFallbackLog(models.Model):
    """Logs every Gemini fallback for active learning / retraining."""
    TRIGGER_CHOICES = [
        ('LOW_CONFIDENCE', 'TunBERT confiance basse'),
        ('SERVICE_DOWN',   'NLU service indisponible'),
        ('ALWAYS_VERIFY',  'Intent destructif verifie'),
    ]

    message            = models.OneToOneField('crm.Message', on_delete=models.SET_NULL, null=True, blank=True, related_name='fallback_log')
    original_text      = models.TextField()
    tunbert_intent     = models.CharField(max_length=50, blank=True, null=True)
    tunbert_confidence = models.FloatField(blank=True, null=True)
    tunbert_entities   = models.JSONField(default=list, blank=True)
    gemini_intent      = models.CharField(max_length=50)
    gemini_confidence  = models.FloatField(blank=True, null=True)
    gemini_entities    = models.JSONField(default=list, blank=True)
    trigger_reason     = models.CharField(max_length=20, choices=TRIGGER_CHOICES)
    intent_changed     = models.BooleanField(default=False)
    reviewed           = models.BooleanField(default=False)
    review_label       = models.CharField(max_length=50, blank=True, null=True)
    created_at         = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'NLU Fallback Log'
        verbose_name_plural = 'NLU Fallback Logs'

    def __str__(self):
        arrow = "->" if self.intent_changed else "="
        return f"[{self.trigger_reason}] {self.tunbert_intent} {arrow} {self.gemini_intent} | '{self.original_text[:40]}'"


class ProductVector(models.Model):
    """Read-only mirror of products_vector table (managed by vision-service)."""
    product_id   = models.CharField(max_length=255)
    variation_id = models.CharField(max_length=255)
    shop_id      = models.CharField(max_length=255)
    image_url    = models.TextField(blank=True, null=True)
    created_at   = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'products_vector'
        verbose_name = 'Product Embedding'
        verbose_name_plural = 'Product Embeddings (Vision)'
        ordering = ['shop_id', 'product_id']

    def __str__(self):
        return f"[{self.shop_id}] product={self.product_id} var={self.variation_id}"
