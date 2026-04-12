from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..models import Conversation
from ..serializers import ConversationSerializer, MessageSerializer


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only endpoint for conversations + messages sub-resource."""
    queryset = Conversation.objects.all().order_by('-updated_at')
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        shop_id = self.request.query_params.get('shop_id')
        if shop_id:
            qs = qs.filter(shop_id=shop_id)
        return qs

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Returns all messages for a specific conversation."""
        conversation = self.get_object()
        msgs = conversation.messages.all().order_by('created_at')
        page = self.paginate_queryset(msgs)
        if page is not None:
            return self.get_paginated_response(MessageSerializer(page, many=True).data)
        return Response(MessageSerializer(msgs, many=True).data)
