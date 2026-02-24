from django.urls import path
from .views import MessengerWebhookPOC

urlpatterns = [
    path('messenger/poc', MessengerWebhookPOC.as_view(), name='messenger_poc'),
]
