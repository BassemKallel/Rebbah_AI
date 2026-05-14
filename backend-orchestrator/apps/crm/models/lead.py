from django.db import models
from django.utils import timezone
import uuid as uuid_lib
import time


class Lead(models.Model):
    """
    Represents a potential customer identified via Messenger.
    Stores both lead info AND pending pre-order data waiting for agent confirmation.
    """
    LEAD_STATUS_ENGAGED   = "ENGAGED"
    LEAD_STATUS_QUALIFIED = "QUALIFIED"
    LEAD_STATUS_CHOICES   = [
        (LEAD_STATUS_ENGAGED,   "Engagé — intention d'achat détectée, entités en cours de collecte"),
        (LEAD_STATUS_QUALIFIED, "Qualifié — pré-commande créée, en attente agent"),
    ]

    uuid        = models.UUIDField(default=uuid_lib.uuid4, unique=True, editable=False)
    platform_id = models.CharField(max_length=255, db_index=True)
    name        = models.CharField(max_length=255, blank=True, null=True)
    shop_id     = models.CharField(max_length=255, blank=True, null=True)

    # ── Données Métier Universelles (Découplage) ─────────────────────────
    # Toutes les entités extraites par le LLM (produits, adresse, tel, etc.)
    # sont stockées dans ce JSON, rendant le Lead 100% agnostique du domaine.
    extracted_data = models.JSONField(default=dict, blank=True, null=True, help_text="Entités collectées par l'IA")

    lead_status = models.CharField(max_length=20, choices=LEAD_STATUS_CHOICES, default=LEAD_STATUS_ENGAGED, db_index=True)

    has_pending_order          = models.BooleanField(default=False)
    pending_order_reference    = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    pending_order_created_at   = models.DateTimeField(blank=True, null=True)
    agent_confirmation_pending = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name or 'Unknown'} ({self.platform_id})"


class OrderItem(models.Model):
    """
    Optional model linked to a Lead, specifically designed for E-commerce catalogs.
    Represents one item in a shopping cart.
    """
    lead         = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='items')
    product_id   = models.CharField(max_length=255, blank=True, null=True)
    product_name = models.CharField(max_length=255)
    quantity     = models.IntegerField(default=1)
    price        = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    attributes   = models.JSONField(default=dict, blank=True, null=True, help_text="Taille, couleur, variantes...")

    created_at   = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.quantity}x {self.product_name}"
