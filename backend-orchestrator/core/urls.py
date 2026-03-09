from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/gateway/', include('apps.gateway.urls')),
    path('api/v1/crm/', include('apps.crm.urls')),
]
