from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet, LeadViewSet, BotConfigurationViewSet

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'leads', LeadViewSet, basename='lead')

urlpatterns = [
    path('bot-configurations/', BotConfigurationViewSet.as_view({
        'put': 'upsert',
        'patch': 'upsert'
    }), name='bot-configuration-upsert'),
    path('bot-configurations/<shop_id>/', BotConfigurationViewSet.as_view({
        'get': 'retrieve'
    }), name='bot-configuration-detail'),
    path('', include(router.urls)),
]
