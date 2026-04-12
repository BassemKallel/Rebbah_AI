"""
apps/crm/services/order_service.py

Business logic for lead pre-order management.
Replaces the Lead.create_pending_order() method on the model.
"""
import time
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


def create_pending_order(lead, shop_id: str, product_id: str, variation_id: str,
                         color: str, size: str, address: str, phone_number: str,
                         quantity: int = 1):
    """
    Attach a pre-order to a lead and advance it to QUALIFIED status.
    Returns the updated lead instance.
    """
    from apps.crm.models import Lead

    lead.shop_id      = shop_id
    lead.product_id   = product_id
    lead.variation_id = variation_id
    lead.color        = color
    lead.size         = size
    lead.quantity     = quantity
    lead.address      = address
    lead.phone_number = phone_number

    lead.has_pending_order          = True
    lead.agent_confirmation_pending = True
    lead.lead_status                = Lead.LEAD_STATUS_QUALIFIED

    if not lead.pending_order_reference:
        lead.pending_order_reference = f"PRE-{int(time.time() * 1000)}"

    lead.pending_order_created_at = timezone.now()
    lead.save()

    logger.info(f"[ORDER] Pre-order created — lead={lead.id} ref={lead.pending_order_reference}")
    return lead
