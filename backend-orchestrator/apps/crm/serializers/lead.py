from rest_framework import serializers
from ..models import Lead


class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = [
            'id', 'platform_id', 'name', 'shop_id', 'lead_status',
            'product_id', 'variation_id', 'color', 'size', 'quantity',
            'address', 'phone_number', 'has_pending_order',
            'pending_order_reference', 'pending_order_created_at',
            'agent_confirmation_pending', 'created_at', 'updated_at',
        ]
