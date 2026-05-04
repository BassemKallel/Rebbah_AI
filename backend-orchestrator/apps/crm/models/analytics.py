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


class PipelineLog(models.Model):
    """
    Logs every AI pipeline execution for monitoring and debugging.
    Captures both NLU and LLM mode runs, their errors, and key metadata.
    """
    MODE_CHOICES = [
        ('nlu', 'NLU (TunBERT)'),
        ('llm', 'LLM (Gemini Direct)'),
    ]
    ERROR_CHOICES = [
        ('none',        'Aucune erreur'),
        ('json_parse',  'JSON Parse Error (Gemini)'),
        ('api_error',   'Gemini API Error'),
        ('no_api_key',  'Clé API manquante'),
        ('import_error','Package manquant'),
        ('vision_error','Vision Service Error'),
        ('order_error', 'Erreur création commande'),
        ('timeout',     'Timeout'),
        ('other',       'Autre'),
    ]

    # ── Identifiers ────────────────────────────────────────────────────────
    shop_id         = models.CharField(max_length=100, db_index=True)
    sender_id       = models.CharField(max_length=255)
    mode            = models.CharField(max_length=10, choices=MODE_CHOICES, default='nlu')

    # ── Message content ────────────────────────────────────────────────────
    user_text       = models.TextField()
    bot_text        = models.TextField(blank=True, default='')
    detected_intent = models.CharField(max_length=50, blank=True, default='')
    has_image       = models.BooleanField(default=False)

    # ── State machine ──────────────────────────────────────────────────────
    state_before    = models.CharField(max_length=50, blank=True, default='')
    state_after     = models.CharField(max_length=50, blank=True, default='')
    order_created   = models.BooleanField(default=False)

    # ── Error tracking ─────────────────────────────────────────────────────
    has_error       = models.BooleanField(default=False, db_index=True)
    error_type      = models.CharField(max_length=20, choices=ERROR_CHOICES, default='none')
    error_detail    = models.TextField(blank=True, default='')

    # ── Performance ────────────────────────────────────────────────────────
    duration_ms     = models.IntegerField(null=True, blank=True)

    created_at      = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Pipeline Log'
        verbose_name_plural = 'Pipeline Logs'
        indexes = [
            models.Index(fields=['shop_id', '-created_at']),
            models.Index(fields=['has_error', '-created_at']),
        ]

    def __str__(self):
        status = '❌' if self.has_error else '✅'
        return f"{status} [{self.mode.upper()}] {self.shop_id} | {self.detected_intent} | '{self.user_text[:40]}'"
