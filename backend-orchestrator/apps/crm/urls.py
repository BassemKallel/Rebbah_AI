from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet, LeadViewSet, BotConfigurationViewSet, ResponseTemplateViewSet
from .company_views import CompanySettingsView

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'leads', LeadViewSet, basename='lead')
router.register(r'templates', ResponseTemplateViewSet, basename='template')

urlpatterns = [
    path('bot-configurations/', BotConfigurationViewSet.as_view({
        'put': 'upsert',
        'patch': 'upsert'
    }), name='bot-configuration-upsert'),
    path('bot-configurations/<shop_id>/', BotConfigurationViewSet.as_view({
        'get': 'retrieve'
    }), name='bot-configuration-detail'),
    path('company/<str:shop_id>/', CompanySettingsView.as_view(), name='company-settings'),
    path('', include(router.urls)),
]

