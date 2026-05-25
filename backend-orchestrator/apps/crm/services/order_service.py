"""
apps/crm/services/order_service.py

Business logic for lead pre-order management.
Replaces the Lead.create_pending_order() method on the model.
"""
import time
import logging
from typing import Any, Dict, List, Optional

from django.utils import timezone

from apps.crm.models.lead import Lead, OrderItem

logger = logging.getLogger(__name__)


def create_pending_order(
    lead: Lead,
    shop_id: str,
    extracted_data: Optional[Dict[str, Any]] = None,
    items: Optional[List[Dict[str, Any]]] = None
) -> Lead:
    """
    Attach a pre-order/lead status to a lead and advance it to QUALIFIED status.
    Universal for all domains. If 'items' is provided, creates OrderItems (E-commerce).
    Returns the updated lead instance.
    """
    lead.shop_id        = shop_id
    lead.extracted_data = extracted_data or {}

    lead.has_pending_order          = True
    lead.agent_confirmation_pending = True
    lead.lead_status                = Lead.LEAD_STATUS_QUALIFIED

    if not lead.pending_order_reference:
        lead.pending_order_reference = f"PRE-{int(time.time() * 1000)}"

    lead.pending_order_created_at = timezone.now()
    lead.save()
    
    # Create Order Items if any
    if items:
        for item in items:
            OrderItem.objects.create(
                lead=lead,
                product_id=item.get("product_id"),
                product_name=item.get("product_name", item.get("name", item.get("product", "Unknown"))),
                quantity=item.get("quantity", item.get("qty", 1)),
                price=item.get("price"),
                attributes=item.get("attributes") or {}
            )

    logger.info(f"[ORDER] Pre-order/Lead created — lead={lead.id} ref={lead.pending_order_reference}")
    return lead
