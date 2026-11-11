from django.db import models
from django.utils import timezone
from datetime import timedelta




class ItemVector(models.Model):
    """Read-only mirror of crm_itemvector table (managed by vision-service)."""
    item_id      = models.CharField(max_length=255)
    shop_id      = models.CharField(max_length=255)
    image_url    = models.TextField(blank=True, null=True)
    metadata     = models.JSONField(blank=True, null=True)
    embedding    = models.TextField(blank=True, null=True)
    created_at   = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'crm_itemvector'
        verbose_name = 'Visual RAG Item'
        verbose_name_plural = 'Visual RAG Items (Vision)'
        ordering = ['shop_id', '-created_at']

    def __str__(self):
        name = self.metadata.get('name', self.item_id) if self.metadata else self.item_id
        return f"[{self.shop_id}] {name}"


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

    # ── Performance & Billing ──────────────────────────────────────────────
    duration_ms       = models.IntegerField(null=True, blank=True)
    prompt_tokens     = models.IntegerField(default=0, help_text="Tokens consommés en entrée (prompt)")
    completion_tokens = models.IntegerField(default=0, help_text="Tokens consommés en sortie (réponse)")

    # ── Full logger trace ──────────────────────────────────────────────────
    # Captures every logger.info/warning/error emitted during this pipeline run.
    log_messages    = models.TextField(blank=True, default='',
                                       help_text='Trace complète des logs (INFO/WARNING/ERROR) émis pendant ce run.')

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


class PendingMessage(models.Model):
    """
    Retry queue for messages that failed due to a temporary Gemini API error
    (e.g. 429 RESOURCE_EXHAUSTED, 503 UNAVAILABLE).

    The cron job RetryPendingMessagesCronJob reads this table every minute
    and re-processes each pending message once Gemini is available again.
    """
    # ── Identifiers ────────────────────────────────────────────────────────
    shop_id       = models.CharField(max_length=100, db_index=True)
    sender_id     = models.CharField(max_length=255)
    conversation  = models.ForeignKey(
        'crm.Conversation', on_delete=models.CASCADE,
        related_name='pending_messages', null=True, blank=True
    )

    # ── Payload ────────────────────────────────────────────────────────────
    user_text     = models.TextField()
    image_url     = models.URLField(max_length=2048, blank=True, default='')

    # ── Retry tracking ─────────────────────────────────────────────────────
    retry_count   = models.PositiveSmallIntegerField(default=0)
    next_retry_at = models.DateTimeField(default=timezone.now, db_index=True)
    MAX_RETRIES   = 3

    created_at    = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['next_retry_at']
        verbose_name = 'Message en Attente (Queue)'
        verbose_name_plural = 'Messages en Attente (Queue)'
        indexes = [
            models.Index(fields=['shop_id', 'next_retry_at']),
        ]

    def schedule_next_retry(self, delay_seconds: int = 60):
        """Reschedule after a failed retry attempt."""
        self.retry_count += 1
        self.next_retry_at = timezone.now() + timedelta(seconds=delay_seconds)
        self.save(update_fields=['retry_count', 'next_retry_at'])

    @property
    def is_expired(self) -> bool:
        return self.retry_count >= self.MAX_RETRIES

    def __str__(self):
        return (
            f"[Queue] shop={self.shop_id} sender={self.sender_id} "
            f"retry={self.retry_count}/{self.MAX_RETRIES} | '{self.user_text[:40]}'"
        )
