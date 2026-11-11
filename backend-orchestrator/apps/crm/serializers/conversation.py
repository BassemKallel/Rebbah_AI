from rest_framework import serializers
from ..models import Conversation, Message
from .lead import LeadSerializer


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'text',
            'extracted_intent', 'extracted_entities',
            'is_error', 'is_human_agent', 'created_at',
        ]


class ConversationSerializer(serializers.ModelSerializer):
    lead_details     = LeadSerializer(source='lead', read_only=True)
    human_agent_name = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'lead', 'lead_details', 'shop_id', 'state',
            'context_data', 'missing_entities',
            'is_human_controlled', 'human_takeover_at', 'human_agent_name',
            'created_at', 'updated_at',
        ]

    def get_human_agent_name(self, obj):
        if obj.human_agent:
            return obj.human_agent.get_full_name() or obj.human_agent.username
        return None
