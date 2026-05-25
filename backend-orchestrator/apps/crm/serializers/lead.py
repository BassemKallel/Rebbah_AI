from typing import Any, Dict, List

from rest_framework import serializers
from ..models import Lead


class LeadSerializer(serializers.ModelSerializer):
    phone_number = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            'id', 'platform_id', 'name', 'shop_id', 'lead_status',
            'extracted_data', 'items', 'address', 'phone_number', 'has_pending_order',
            'pending_order_reference', 'pending_order_created_at',
            'agent_confirmation_pending', 'created_at', 'updated_at',
        ]

    def get_phone_number(self, obj: Lead) -> str:
        return (obj.extracted_data or {}).get("phone_number", "")

    def get_address(self, obj: Lead) -> str:
        return (obj.extracted_data or {}).get("address", "")

    def get_items(self, obj: Lead) -> List[Dict[str, Any]]:
        db_items = list(obj.items.all())
        if db_items:
            return [
                {
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                    "price": float(item.price) if item.price is not None else None,
                    "attributes": item.attributes or {},
                }
                for item in db_items
            ]
        return (obj.extracted_data or {}).get("items", [])
