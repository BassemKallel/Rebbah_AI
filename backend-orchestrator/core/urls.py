from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # POC Messenger webhook
    path('api/v1/webhook/', include('apps.gateway.urls')),
]
