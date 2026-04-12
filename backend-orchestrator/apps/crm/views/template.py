from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..models import ResponseTemplate
from ..serializers import ResponseTemplateSerializer
from apps.gateway.services.template_service import get_template


class ResponseTemplateViewSet(viewsets.ModelViewSet):
    """
    CRUD for per-shop response template customization.
    System defaults (shop_id=None) are read-only via API — use Django Admin.
    """
    serializer_class = ResponseTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ResponseTemplate.objects.all().order_by('template_type', 'language', 'intent')
        params = self.request.query_params
        for field in ('shop_id', 'language', 'template_type', 'intent'):
            val = params.get(field)
            if val:
                qs = qs.filter(**{field: val})
        return qs

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_default or instance.shop_id is None:
            return Response(
                {"error": "Les templates système par défaut ne peuvent pas être supprimés via l'API."},
                status=status.HTTP_403_FORBIDDEN,
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
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
        GET /api/v1/crm/templates/preview/?shop_id=...&language=FR&template_type=response&intent=GREETING
        Returns the resolved template text via the full lookup chain.
        """
        shop_id       = request.query_params.get('shop_id')
        language      = request.query_params.get('language', 'FR')
        template_type = request.query_params.get('template_type')
        intent        = request.query_params.get('intent')

        if not template_type or not intent:
            return Response({"error": "Les paramètres 'template_type' et 'intent' sont requis."}, status=400)

        text = get_template(template_type, intent, language, shop_id=shop_id)
        if text is None:
            return Response({"error": f"Aucun template trouvé pour type='{template_type}', intent='{intent}', lang='{language}'."}, status=404)

        return Response({"shop_id": shop_id, "language": language, "template_type": template_type, "intent": intent, "text": text})
