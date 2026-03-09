from rest_framework import serializers
from .models import Lead, Conversation, Message

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'text', 'extracted_intent', 'extracted_entities', 'is_error', 'created_at']

class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = ['id', 'platform_id', 'name', 'shop_id', 'product_id', 'variation_id', 'color', 'size', 'quantity', 'address', 'phone_number', 'has_pending_order', 'pending_order_reference', 'pending_order_created_at', 'agent_confirmation_pending', 'created_at', 'updated_at']

class ConversationSerializer(serializers.ModelSerializer):
    lead_details = LeadSerializer(source='lead', read_only=True)
    
    class Meta:
        model = Conversation
        fields = ['id', 'lead', 'lead_details', 'shop_id', 'state', 'context_data', 'missing_entities', 'created_at', 'updated_at']
