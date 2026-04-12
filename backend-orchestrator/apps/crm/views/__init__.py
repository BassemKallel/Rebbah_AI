"""apps/crm/views/__init__.py — re-export all views for backward compat."""
from .lead import LeadViewSet
from .conversation import ConversationViewSet
from .config import BotConfigurationViewSet
from .template import ResponseTemplateViewSet
from .handoff import takeover_conversation, release_conversation, agent_reply, handoff_status, toggle_bot
from .company import CompanySettingsView
from .auth import LoginView, MeView, ChangePasswordView

__all__ = [
    'LeadViewSet', 'ConversationViewSet', 'BotConfigurationViewSet',
    'ResponseTemplateViewSet', 'takeover_conversation', 'release_conversation',
    'agent_reply', 'handoff_status', 'toggle_bot',
    'CompanySettingsView',
    'LoginView', 'MeView', 'ChangePasswordView',
]
