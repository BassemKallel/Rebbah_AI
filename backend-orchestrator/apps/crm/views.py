from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Conversation, Message, Lead, BotConfiguration, ResponseTemplate
from .serializers import (
    ConversationSerializer, MessageSerializer, LeadSerializer,
    BotConfigurationSerializer, ResponseTemplateSerializer,
)
from .authentication import TikTakTokenAuthentication, JWTCompanyAuthentication
from apps.gateway.services.template_service import get_template



class LeadViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows leads to be viewed or edited.
    """
    queryset = Lead.objects.all().order_by('-created_at')
    serializer_class = LeadSerializer
    authentication_classes = [JWTCompanyAuthentication, TikTakTokenAuthentication]
    permission_classes     = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        shop_id = self.request.query_params.get('shop_id')
        if shop_id:
            queryset = queryset.filter(shop_id=shop_id)
        return queryset


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows conversations to be viewed.
    """
    queryset = Conversation.objects.all().order_by('-updated_at')
    serializer_class = ConversationSerializer
    authentication_classes = [JWTCompanyAuthentication, TikTakTokenAuthentication]
    permission_classes     = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        shop_id = self.request.query_params.get('shop_id')
        if shop_id:
            queryset = queryset.filter(shop_id=shop_id)
        return queryset

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """
        Returns all messages for a specific conversation.
        """
        conversation = self.get_object()
        messages = conversation.messages.all().order_by('created_at')
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = MessageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)


class BotConfigurationViewSet(viewsets.GenericViewSet):
    """
    API endpoint that allows bot configurations to be viewed or edited.
    Allows clients to customize greetings, messages, and intents.
    """
    queryset = BotConfiguration.objects.all().order_by('-updated_at')
    serializer_class = BotConfigurationSerializer
    lookup_field = 'shop_id'
    authentication_classes = [JWTCompanyAuthentication, TikTakTokenAuthentication]
    permission_classes     = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        """
        Return a default configuration if it does not exist.
        """
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        shop_id = self.kwargs.get(lookup_url_kwarg)

        obj, created = BotConfiguration.objects.get_or_create(shop_id=shop_id)
        self.check_object_permissions(self.request, obj)
        return Response(self.get_serializer(obj).data)

    def upsert(self, request, *args, **kwargs):
        """
        Handle POST, PUT, PATCH where the shop_id is provided in the payload, not the URL.
        """
        shop_id = request.data.get('shop_id')
        if not shop_id:
            return Response(
                {"error": "Le champ 'shop_id' est requis dans le JSON (payload)."},
                status=400
            )

        obj, created = BotConfiguration.objects.get_or_create(shop_id=shop_id)
        self.check_object_permissions(self.request, obj)

        partial = request.method == 'PATCH'

        serializer = self.get_serializer(obj, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=201 if created else 200)


# ── ResponseTemplate endpoints ────────────────────────────────────────────────

class ResponseTemplateViewSet(viewsets.ModelViewSet):
    """
    CRUD endpoints for per-shop response template customization.

    Base URL: /api/v1/crm/templates/

    Filtering (GET /api/v1/crm/templates/):
      ?shop_id=xxx          — filter by shop (required for shop overrides)
      ?language=FR          — filter by language (FR | AR | EN)
      ?template_type=response — filter by family
      ?intent=GREETING      — filter by intent

    Special action:
      GET /api/v1/crm/templates/preview/
        ?shop_id=xxx&language=FR&template_type=response&intent=GREETING
        Returns the resolved text (through the full lookup chain: Redis → DB shop → DB default → Python)

    Rules:
      - POST/PUT/PATCH/DELETE only on shop-specific rows (shop_id required).
      - System defaults (shop_id=None) can be read via GET but never written via API.
      - Use the Django Admin panel to edit system defaults.
    """
    serializer_class = ResponseTemplateSerializer
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']
    authentication_classes = [JWTCompanyAuthentication, TikTakTokenAuthentication]
    permission_classes     = [IsAuthenticated]

    def get_queryset(self):
        qs = ResponseTemplate.objects.all().order_by('template_type', 'language', 'intent')

        shop_id       = self.request.query_params.get('shop_id')
        language      = self.request.query_params.get('language')
        template_type = self.request.query_params.get('template_type')
        intent        = self.request.query_params.get('intent')

        if shop_id:
            qs = qs.filter(shop_id=shop_id)
        if language:
            qs = qs.filter(language=language)
        if template_type:
            qs = qs.filter(template_type=template_type)
        if intent:
            qs = qs.filter(intent=intent)

        return qs

    def destroy(self, request, *args, **kwargs):
        """Prevent deletion of system defaults."""
        instance = self.get_object()
        if instance.is_default or instance.shop_id is None:
            return Response(
                {"error": "Les templates système par défaut ne peuvent pas être supprimés via l'API."},
                status=status.HTTP_403_FORBIDDEN,
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        """Prevent modification of system defaults."""
        instance = self.get_object()
        if instance.is_default or instance.shop_id is None:
            return Response(
                {"error": "Les templates système par défaut ne peuvent pas être modifiés via l'API."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='preview')
    def preview(self, request):
        """
        GET /api/v1/crm/templates/preview/?shop_id=xxx&language=FR&template_type=response&intent=GREETING

        Returns the resolved template text via the full lookup chain
        (Redis cache → DB shop override → DB system default → Python fallback).
        """
        shop_id       = request.query_params.get('shop_id')
        language      = request.query_params.get('language', 'FR')
        template_type = request.query_params.get('template_type')
        intent        = request.query_params.get('intent')

        if not template_type or not intent:
            return Response(
                {"error": "Les paramètres 'template_type' et 'intent' sont requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        text = get_template(template_type, intent, language, shop_id=shop_id)

        if text is None:
            return Response(
                {"error": f"Aucun template trouvé pour type='{template_type}', intent='{intent}', lang='{language}'."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({
            "shop_id":       shop_id,
            "language":      language,
            "template_type": template_type,
            "intent":        intent,
            "text":          text,
        })
