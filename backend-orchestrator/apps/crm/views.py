from rest_framework import viewsets , mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Conversation, Message, Lead, BotConfiguration
from .serializers import ConversationSerializer, MessageSerializer, LeadSerializer, BotConfigurationSerializer

class LeadViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows leads to be viewed or edited.
    """
    queryset = Lead.objects.all().order_by('-created_at')
    serializer_class = LeadSerializer

    def get_queryset(self):
        """
        Optionally restricts the returned leads to a given shop
        by filtering against a `shop_id` query parameter in the URL.
        """
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

    def get_queryset(self):
        """
        Optionally restricts the returned conversations to a given shop
        by filtering against a `shop_id` query parameter in the URL.
        """
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
        
        # Determine if partial update (PATCH)
        partial = request.method == 'PATCH'
        
        serializer = self.get_serializer(obj, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Return 201 if just created, else 200
        return Response(serializer.data, status=201 if created else 200)
