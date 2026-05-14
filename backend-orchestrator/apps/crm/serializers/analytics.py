from rest_framework import serializers
from apps.crm.models.analytics import ItemVector

class ItemVectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemVector
        fields = ['id', 'item_id', 'shop_id', 'image_url', 'metadata', 'created_at']
        read_only_fields = ['id', 'created_at']
