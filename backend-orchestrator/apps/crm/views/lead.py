from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from ..models import Lead
from ..serializers import LeadSerializer


class LeadViewSet(viewsets.ModelViewSet):
    """CRUD endpoint for leads."""
    queryset = Lead.objects.all().order_by('-created_at')
    serializer_class = LeadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        shop_id = self.request.query_params.get('shop_id')
        if shop_id:
            qs = qs.filter(shop_id=shop_id)
        status = self.request.query_params.get('status')
        if status:
            qs = qs.filter(lead_status=status)
        return qs
