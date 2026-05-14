from django.urls import path
from .views import MessengerWebhookPOC, MetaWebhookView, MetaWebhookSilentView, CatalogUploadView, CatalogUpdateMetadataView, CatalogImportCsvView
from .health import ServicesHealthView
urlpatterns = [
    path('messenger/poc',       MessengerWebhookPOC.as_view(),   name='messenger_poc'),
    path('meta/webhook',        MetaWebhookView.as_view(),        name='meta_webhook'),
    path('meta/webhook/silent', MetaWebhookSilentView.as_view(),  name='meta_webhook_silent'),
    path('health/',             ServicesHealthView.as_view(),      name='services_health'),
    
    # Visual RAG Catalog endpoint
    path('catalog/upload',           CatalogUploadView.as_view(),          name='catalog_upload'),
    path('catalog/update-metadata',   CatalogUpdateMetadataView.as_view(),  name='catalog_update_metadata'),
    path('catalog/import-csv',        CatalogImportCsvView.as_view(),       name='catalog_import_csv'),
]

