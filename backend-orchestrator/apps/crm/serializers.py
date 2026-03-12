from rest_framework import serializers
from .models import Lead, Conversation, Message, BotConfiguration
from apps.gateway.response_templates import TEMPLATES

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

class BotConfigurationSerializer(serializers.ModelSerializer):
    default_intents = serializers.SerializerMethodField()

    class Meta:
        model = BotConfiguration
        fields = [
            'id', 'shop_id', 'shop_name', 'language', 'ai_agent_name', 'custom_intents', 
            'default_intents', 'created_at', 'updated_at'
        ]

    def get_default_intents(self, obj):
        # Determine the effective language for defaults (AUTO falls back to FR)
        lang = obj.language if obj.language in TEMPLATES else 'FR'
        return TEMPLATES.get(lang, TEMPLATES['FR'])

    def update(self, instance, validated_data):
        # Enable partial updates inside the 'custom_intents' JSON object
        custom_intents = validated_data.pop('custom_intents', None)
        
        # Standard DRF update for everything else (language, greeting, etc.)
        instance = super().update(instance, validated_data)
        
        if custom_intents is not None:
            if self.partial:
                # If PATCH request, deep merge with existing intents
                existing_intents = instance.custom_intents or {}
                for key, value in custom_intents.items():
                    if value and str(value).strip():
                        existing_intents[key] = value
                    else:
                        # If a value is empty/null in PATCH, we remove the override
                        existing_intents.pop(key, None)
                instance.custom_intents = existing_intents
            else:
                # If PUT request, replace with cleaned dictionary (no empty strings)
                cleaned_intents = {
                    key: val for key, val in custom_intents.items() 
                    if val and str(val).strip()
                }
                instance.custom_intents = cleaned_intents
            instance.save()
            
        return instance
