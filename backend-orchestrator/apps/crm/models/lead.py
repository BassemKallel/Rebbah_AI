from django.db import models
from django.utils import timezone
import uuid as uuid_lib
import time


class Lead(models.Model):
    """
    Represents a potential customer identified via Messenger.
    Stores both lead info AND pending pre-order data waiting for agent confirmation.
    """
    LEAD_STATUS_PROSPECT  = "PROSPECT"
    LEAD_STATUS_ENGAGED   = "ENGAGED"
    LEAD_STATUS_QUALIFIED = "QUALIFIED"
    LEAD_STATUS_CHOICES   = [
        (LEAD_STATUS_PROSPECT,  "Prospect — conversation démarrée, pas d'intention d'achat"),
        (LEAD_STATUS_ENGAGED,   "Engagé — produit identifié, entités en cours de collecte"),
        (LEAD_STATUS_QUALIFIED, "Qualifié — pré-commande créée, en attente agent"),
    ]

    uuid        = models.UUIDField(default=uuid_lib.uuid4, unique=True, editable=False)
    platform_id = models.CharField(max_length=255, db_index=True)
    name        = models.CharField(max_length=255, blank=True, null=True)
    shop_id     = models.CharField(max_length=255, blank=True, null=True)

    product_id   = models.CharField(max_length=255, blank=True, null=True)
    variation_id = models.CharField(max_length=255, blank=True, null=True)
    color        = models.CharField(max_length=100, blank=True, null=True)
    size         = models.CharField(max_length=50, blank=True, null=True)
    quantity     = models.IntegerField(default=1)
    address      = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    lead_status = models.CharField(max_length=20, choices=LEAD_STATUS_CHOICES, default=LEAD_STATUS_PROSPECT, db_index=True)

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

    def create_pending_order(self, shop_id, product_id, variation_id, color, size, address, phone_number, quantity=1):
        self.shop_id = shop_id; self.product_id = product_id; self.variation_id = variation_id
        self.color = color; self.size = size; self.quantity = quantity
        self.address = address; self.phone_number = phone_number
        self.has_pending_order = True; self.agent_confirmation_pending = True
        self.lead_status = Lead.LEAD_STATUS_QUALIFIED
        if not self.pending_order_reference:
            self.pending_order_reference = f"PRE-{int(time.time() * 1000)}"
        self.pending_order_created_at = timezone.now()
        self.save()
