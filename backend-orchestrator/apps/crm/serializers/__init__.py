"""apps/crm/serializers/__init__.py — re-export all serializers."""
from .lead import LeadSerializer
from .conversation import ConversationSerializer, MessageSerializer
from .config import BotConfigurationSerializer
from .template import ResponseTemplateSerializer

__all__ = [
    'LeadSerializer', 'ConversationSerializer', 'MessageSerializer',
    'BotConfigurationSerializer', 'ResponseTemplateSerializer',
]
