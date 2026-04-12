from rest_framework import serializers
from ..models import ResponseTemplate


class ResponseTemplateSerializer(serializers.ModelSerializer):
    """
    Per-shop response template customization.
    Rules:
    - shop_id is mandatory — system defaults (shop_id=None) cannot be touched via API.
    - is_default is always False for shop overrides (read-only).
    """
    is_default = serializers.BooleanField(read_only=True)

    class Meta:
        model  = ResponseTemplate
        fields = [
            'id', 'shop_id', 'language', 'template_type', 'intent',
            'text', 'available_variables', 'is_default', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'is_default', 'created_at', 'updated_at']

    def validate_shop_id(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError("shop_id est requis. Utilisez l'Admin pour modifier les templates système.")
        return str(value).strip()

    def validate(self, attrs):
        shop_id       = attrs.get('shop_id',       getattr(self.instance, 'shop_id', None))
        language      = attrs.get('language',      getattr(self.instance, 'language', None))
        template_type = attrs.get('template_type', getattr(self.instance, 'template_type', None))
        intent        = attrs.get('intent',        getattr(self.instance, 'intent', None))

        qs = ResponseTemplate.objects.filter(shop_id=shop_id, language=language, template_type=template_type, intent=intent)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                f"Un template existe déjà pour shop='{shop_id}', lang='{language}', type='{template_type}', intent='{intent}'. Utilisez PATCH."
            )
        return attrs

    def create(self, validated_data):
        validated_data['is_default'] = False
        return super().create(validated_data)
