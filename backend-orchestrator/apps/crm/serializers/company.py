from rest_framework import serializers
from ..models import Company


class CompanySettingsSerializer(serializers.ModelSerializer):
    """
    Serializer for Company.
    """
    class Meta:
        model  = Company
        fields = [
            'shop_id', 'name', 'is_active',
        ]
        read_only_fields = ['shop_id', 'name', 'is_active']
