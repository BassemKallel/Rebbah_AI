from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # POC Messenger webhook
    path('api/v1/gateway/', include('apps.gateway.urls')),
]
