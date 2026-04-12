from rest_framework import serializers
from ..models import Company


class CompanySettingsSerializer(serializers.ModelSerializer):
    """
    Serializer for Company LLM settings (response_mode, gemini_api_key, llm_context).
    The gemini_api_key is write-only — never exposed in GET responses.
    """
    has_gemini_key  = serializers.SerializerMethodField()
    has_llm_context = serializers.SerializerMethodField()

    class Meta:
        model  = Company
        fields = [
            'shop_id', 'name', 'response_mode',
            'gemini_api_key', 'llm_context',
            'has_gemini_key', 'has_llm_context', 'is_active',
        ]
        read_only_fields = ['shop_id', 'name', 'is_active']
        extra_kwargs = {
            'gemini_api_key': {'write_only': True, 'required': False},
        }

    def get_has_gemini_key(self, obj):
        return bool(obj.gemini_api_key)

    def get_has_llm_context(self, obj):
        return bool(obj.llm_context and obj.llm_context.strip())

    def validate_llm_context(self, value):
        if value and len(value) > 10000:
            raise serializers.ValidationError(
                f"Le contexte LLM ne peut pas dépasser 10 000 caractères ({len(value)} fournis)."
            )
        return value

    def validate(self, attrs):
        """Guard: can't switch to LLM mode without gemini_api_key and llm_context."""
        new_mode = attrs.get('response_mode')
        if new_mode == 'llm':
            gemini_key = attrs.get('gemini_api_key')
            if not gemini_key and self.instance:
                gemini_key = self.instance.gemini_api_key
            if not gemini_key or not str(gemini_key).strip():
                raise serializers.ValidationError(
                    "Une clé API Gemini est obligatoire pour activer le mode LLM."
                )

            llm_ctx = attrs.get('llm_context')
            if llm_ctx is None and self.instance:
                llm_ctx = self.instance.llm_context
            if not llm_ctx or not str(llm_ctx).strip():
                raise serializers.ValidationError(
                    "Le contexte LLM est obligatoire pour activer le mode LLM."
                )
        return attrs
