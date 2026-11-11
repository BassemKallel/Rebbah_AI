from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from apps.crm.models.analytics import ItemVector
from apps.crm.serializers.analytics import ItemVectorSerializer

class ItemVectorViewSet(viewsets.ModelViewSet):
    """
    CRUD endpoint for Visual RAG Items.
    Embedding vector is excluded from the serializer to avoid huge payloads.
    """
    serializer_class = ItemVectorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = ItemVector.objects.all().order_by('-created_at')
        
        # Filter by company if applicable
        if hasattr(self.request.user, 'company') and self.request.user.company:
            queryset = queryset.filter(shop_id=self.request.user.company.shop_id)
        else:
            # Allow query param filtering if admin
            shop_id = self.request.query_params.get('shop_id')
            if shop_id:
                queryset = queryset.filter(shop_id=shop_id)
                
        return queryset
