from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..models import BotConfiguration
from ..serializers import BotConfigurationSerializer


class BotConfigurationViewSet(viewsets.GenericViewSet):
    """
    Bot configuration endpoint.
    GET  /bot-configurations/<shop_id>/   → retrieve (get_or_create)
    PUT/PATCH /bot-configurations/        → upsert (shop_id in payload)
    """
    queryset = BotConfiguration.objects.all().order_by('-updated_at')
    serializer_class = BotConfigurationSerializer
    lookup_field = 'shop_id'
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        shop_id = self.kwargs.get(self.lookup_url_kwarg or self.lookup_field)
        obj, _ = BotConfiguration.objects.get_or_create(shop_id=shop_id)
        self.check_object_permissions(request, obj)
        return Response(self.get_serializer(obj).data)

    def upsert(self, request, *args, **kwargs):
        shop_id = request.data.get('shop_id')
        if not shop_id:
            return Response({"error": "Le champ 'shop_id' est requis dans le JSON (payload)."}, status=400)

        obj, created = BotConfiguration.objects.get_or_create(shop_id=shop_id)
        self.check_object_permissions(request, obj)

        serializer = self.get_serializer(obj, data=request.data, partial=(request.method == 'PATCH'))
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=201 if created else 200)
