from django.urls import path
from .views import MessengerWebhookPOC, MetaWebhookView
from .health import ServicesHealthView

urlpatterns = [
    path('messenger/poc', MessengerWebhookPOC.as_view(), name='messenger_poc'),
    path('meta/webhook', MetaWebhookView.as_view(), name='meta_webhook'),
    path('health/', ServicesHealthView.as_view(), name='services_health'),
]
