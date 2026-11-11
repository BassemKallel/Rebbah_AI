"""apps/crm/views/__init__.py — re-export all views for backward compat."""
from .lead import LeadViewSet
from .conversation import ConversationViewSet
from .config import BotConfigurationViewSet

from .handoff import takeover_conversation, release_conversation, agent_reply, handoff_status, toggle_bot
from .company import CompanySettingsView
from .auth import LoginView, MeView, ChangePasswordView
from .analytics import ItemVectorViewSet

__all__ = [
    'LeadViewSet', 'ConversationViewSet', 'BotConfigurationViewSet',
    'takeover_conversation', 'release_conversation',
    'agent_reply', 'handoff_status', 'toggle_bot',
    'CompanySettingsView',
    'LoginView', 'MeView', 'ChangePasswordView',
    'ItemVectorViewSet',
]
