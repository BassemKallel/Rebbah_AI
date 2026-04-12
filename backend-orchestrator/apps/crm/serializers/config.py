from rest_framework import serializers
from ..models import BotConfiguration


class BotConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotConfiguration
        fields = [
            'id', 'shop_id', 'shop_name', 'language', 'ai_agent_name',
            'bot_enabled', 'bot_disabled_at',
            'created_at', 'updated_at',
        ]
