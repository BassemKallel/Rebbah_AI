"""apps/crm/views/__init__.py — re-export all ViewSets for backward compat."""
from .lead import LeadViewSet
from .conversation import ConversationViewSet
from .config import BotConfigurationViewSet
from .template import ResponseTemplateViewSet
from .handoff import takeover_conversation, release_conversation, agent_reply, handoff_status, toggle_bot

__all__ = [
    'LeadViewSet', 'ConversationViewSet', 'BotConfigurationViewSet',
    'ResponseTemplateViewSet', 'takeover_conversation', 'release_conversation',
    'agent_reply', 'handoff_status', 'toggle_bot',
]
