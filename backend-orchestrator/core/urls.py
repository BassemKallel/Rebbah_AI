from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='/admin/', permanent=False)),
    path('admin/', admin.site.urls),
    path('api/v1/gateway/', include('apps.gateway.urls')),
    path('api/v1/crm/', include('apps.crm.urls')),
    # Auth endpoints also exposed at /api/v1/auth/ (matches frontend authApi.ts)
    path('api/v1/auth/', include('apps.crm.auth_urls')),
]
