from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet, LeadViewSet

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'leads', LeadViewSet, basename='lead')

urlpatterns = [
    path('', include(router.urls)),
]
