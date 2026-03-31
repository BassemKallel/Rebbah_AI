from django.urls import path
from .views import MessengerWebhookPOC, MetaWebhookView

urlpatterns = [
    path('messenger/poc', MessengerWebhookPOC.as_view(), name='messenger_poc'),
    path('meta/webhook', MetaWebhookView.as_view(), name='meta_webhook'),
]
