"""apps/crm/views/__init__.py — re-export all views for backward compat."""
from .lead import LeadViewSet
from .conversation import ConversationViewSet
from .config import BotConfigurationViewSet
from .template import ResponseTemplateViewSet
from .handoff import takeover_conversation, release_conversation, agent_reply, handoff_status, toggle_bot
from .company import CompanySettingsView
from .auth import LoginView, MeView, ChangePasswordView
from .dashboard import (
    dashboard_kpis, dashboard_hourly, dashboard_pending_orders,
    dashboard_recent_activity, dashboard_top_intents, dashboard_channels,
    dashboard_lead_funnel,
)

__all__ = [
    'LeadViewSet', 'ConversationViewSet', 'BotConfigurationViewSet',
    'ResponseTemplateViewSet', 'takeover_conversation', 'release_conversation',
    'agent_reply', 'handoff_status', 'toggle_bot',
    'CompanySettingsView',
    'LoginView', 'MeView', 'ChangePasswordView',
    'dashboard_kpis', 'dashboard_hourly', 'dashboard_pending_orders',
    'dashboard_recent_activity', 'dashboard_top_intents', 'dashboard_channels',
    'dashboard_lead_funnel',
]
