from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ConversationViewSet, LeadViewSet,
    BotConfigurationViewSet, ResponseTemplateViewSet,
    takeover_conversation, release_conversation,
    agent_reply, handoff_status, toggle_bot,
    CompanySettingsView,
    dashboard_kpis, dashboard_hourly, dashboard_pending_orders,
    dashboard_recent_activity, dashboard_top_intents, dashboard_channels,
    dashboard_lead_funnel,
)

from .views.mlops import (
    mlops_stats,
    mlops_fallbacks_list,
    mlops_review_fallback,
    mlops_export,
    mlops_retrain_trigger,
    mlops_retrain_status,
    mlops_deployment_log,
    mlops_retrain_report,
)

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'leads', LeadViewSet, basename='lead')
router.register(r'templates', ResponseTemplateViewSet, basename='template')

urlpatterns = [
    path('auth/', include('apps.crm.auth_urls')),

    # BotConfiguration (get_or_create by shop_id)
    path('bot-configurations/', BotConfigurationViewSet.as_view({'put': 'upsert', 'patch': 'upsert'}), name='bot-configuration-upsert'),
    path('bot-configurations/<str:shop_id>/', BotConfigurationViewSet.as_view({'get': 'retrieve'}), name='bot-configuration-detail'),

    # Human Handoff
    path('conversations/<int:conversation_id>/takeover/',      takeover_conversation, name='conversation-takeover'),
    path('conversations/<int:conversation_id>/release/',       release_conversation,  name='conversation-release'),
    path('conversations/<int:conversation_id>/agent-reply/',   agent_reply,           name='conversation-agent-reply'),
    path('conversations/<int:conversation_id>/handoff-status/', handoff_status,       name='conversation-handoff-status'),
    path('bot-configurations/<str:shop_id>/toggle-bot/',       toggle_bot,            name='bot-toggle'),

    # Dashboard KPIs
    path('dashboard/kpis/',             dashboard_kpis,             name='dashboard-kpis'),
    path('dashboard/hourly/',           dashboard_hourly,           name='dashboard-hourly'),
    path('dashboard/pending-orders/',   dashboard_pending_orders,   name='dashboard-pending-orders'),
    path('dashboard/recent-activity/',  dashboard_recent_activity,  name='dashboard-recent-activity'),
    path('dashboard/top-intents/',      dashboard_top_intents,      name='dashboard-top-intents'),
    path('dashboard/channels/',         dashboard_channels,         name='dashboard-channels'),
    path('dashboard/lead-funnel/',      dashboard_lead_funnel,      name='dashboard-lead-funnel'),

    # Admin MLOps (Protected by IsAdminUser)
    path('admin/mlops/stats/',              mlops_stats,            name='mlops-stats'),
    path('admin/mlops/fallbacks/',          mlops_fallbacks_list,   name='mlops-fallbacks-list'),
    path('admin/mlops/fallbacks/<int:pk>/', mlops_review_fallback,  name='mlops-review-fallback'),
    path('admin/mlops/export/',             mlops_export,           name='mlops-export'),
    path('admin/mlops/retrain/trigger/',    mlops_retrain_trigger,  name='mlops-retrain-trigger'),
    path('admin/mlops/retrain/status/',     mlops_retrain_status,   name='mlops-retrain-status'),
    path('admin/mlops/deployment-log/',     mlops_deployment_log,   name='mlops-deployment-log'),
    path('admin/mlops/retrain/<int:pk>/report/', mlops_retrain_report, name='mlops-retrain-report'),

    path('', include(router.urls)),
]
