from rest_framework import serializers
from .models import Lead, Conversation, Message, BotConfiguration, ResponseTemplate, Company
from apps.gateway.response_templates import TEMPLATES


class CompanySettingsSerializer(serializers.ModelSerializer):
    """
    Serializer for Company LLM settings (response_mode, gemini_api_key, llm_context).
    The gemini_api_key is write-only — never exposed in GET responses.
    """
    has_gemini_key = serializers.SerializerMethodField()
    has_llm_context = serializers.SerializerMethodField()

    class Meta:
        model = Company
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
            # Check gemini_api_key (from payload or existing)
            gemini_key = attrs.get('gemini_api_key')
            if not gemini_key and self.instance:
                gemini_key = self.instance.gemini_api_key
            if not gemini_key or not str(gemini_key).strip():
                raise serializers.ValidationError(
                    "Une clé API Gemini est obligatoire pour activer le mode LLM."
                )

            # Check llm_context (from payload or existing)
            llm_ctx = attrs.get('llm_context')
            if llm_ctx is None and self.instance:
                llm_ctx = self.instance.llm_context
            if not llm_ctx or not str(llm_ctx).strip():
                raise serializers.ValidationError(
                    "Le contexte LLM est obligatoire pour activer le mode LLM."
                )
        return attrs


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'text', 'extracted_intent', 'extracted_entities', 'is_error', 'created_at']


class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = ['id', 'platform_id', 'name', 'shop_id', 'product_id', 'variation_id', 'color', 'size', 'quantity', 'address', 'phone_number', 'has_pending_order', 'pending_order_reference', 'pending_order_created_at', 'agent_confirmation_pending', 'created_at', 'updated_at']


class ConversationSerializer(serializers.ModelSerializer):
    lead_details = LeadSerializer(source='lead', read_only=True)

    class Meta:
        model = Conversation
        fields = ['id', 'lead', 'lead_details', 'shop_id', 'state', 'context_data', 'missing_entities', 'created_at', 'updated_at']


class BotConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotConfiguration
        fields = [
            'id', 'shop_id', 'shop_name', 'language', 'ai_agent_name',
            'created_at', 'updated_at'
        ]




# ── ResponseTemplate ─────────────────────────────────────────────────────────

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
        fields = ['id', 'shop_id', 'language', 'template_type', 'intent',
                  'text', 'available_variables', 'is_default', 'created_at', 'updated_at']
        read_only_fields = ['id', 'is_default', 'created_at', 'updated_at']

    def validate_shop_id(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError(
                "shop_id est requis. Utilisez l'Admin pour modifier les templates système."
            )
        return str(value).strip()

    def validate(self, attrs):
        shop_id       = attrs.get('shop_id',       getattr(self.instance, 'shop_id', None))
        language      = attrs.get('language',      getattr(self.instance, 'language', None))
        template_type = attrs.get('template_type', getattr(self.instance, 'template_type', None))
        intent        = attrs.get('intent',        getattr(self.instance, 'intent', None))

        qs = ResponseTemplate.objects.filter(
            shop_id=shop_id, language=language,
            template_type=template_type, intent=intent,
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                f"Un template existe déjà pour shop='{shop_id}', lang='{language}', "
                f"type='{template_type}', intent='{intent}'. Utilisez PATCH pour le modifier."
            )
        return attrs

    def create(self, validated_data):
        validated_data['is_default'] = False
        return super().create(validated_data)
