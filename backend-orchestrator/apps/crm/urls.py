from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ConversationViewSet, LeadViewSet,
    BotConfigurationViewSet, ResponseTemplateViewSet,
)
from .views.handoff import (
    takeover_conversation, release_conversation,
    agent_reply, handoff_status, toggle_bot,
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

    path('', include(router.urls)),
]
