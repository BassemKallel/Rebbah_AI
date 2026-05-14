from rest_framework import serializers
from ..models import BotConfiguration


class BotConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotConfiguration
        fields = [
            'id', 'shop_id', 'shop_name', 'ai_agent_name',
            'business_domain', 'target_audience', 'communication_tone',
            'language_rules', 'delivery_policy', 'required_checkout_info',
            'custom_intents', 'bot_enabled', 'bot_disabled_at',
            'created_at', 'updated_at',
        ]
