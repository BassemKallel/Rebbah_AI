"""
serializers/mlops.py — Sérialiseurs pour les endpoints Admin MLOps
"""
from rest_framework import serializers
from ..models import NLUFallbackLog, RetrainingLog, ManualDataset

class NLUFallbackLogListSerializer(serializers.ModelSerializer):
    """
    Liste paginée — affichage table frontend.
    """
    message_id = serializers.IntegerField(source='message.id', read_only=True, allow_null=True)

    class Meta:
        model = NLUFallbackLog
        fields = [
            'id',
            'message_id',
            'original_text',
            'tunbert_intent',
            'tunbert_confidence',
            'gemini_intent',
            'gemini_confidence',
            'trigger_reason',
            'intent_changed',
            'reviewed',
            'review_label',
            'created_at',
        ]

class NLUFallbackLogReviewSerializer(serializers.ModelSerializer):
    """
    PATCH — révision d'un label par l'admin.
    """
    class Meta:
        model = NLUFallbackLog
        fields = ['review_label']

    def validate_review_label(self, value):
        from apps.crm.models.config import BotConfiguration
        # Optionnel: on peut verifier dynamiquement si l'intent existe,
        # ou utiliser une liste fixe. Pour le moment, liste fixe :
        VALID_INTENTS = [
            'ASK_ADVICE', 'ASK_AVAILABILITY', 'ASK_DELIVERY', 'ASK_DETAILS',
            'ASK_DISCOUNT', 'ASK_LOCATION', 'ASK_PRICE', 'CANCEL_ORDER',
            'CHECK_PACKAGE', 'COMPLAINT', 'CONFIRM_DENY', 'ECHANGE',
            'GREETING', 'INFORM_INFO', 'NOISE', 'ORDER_PRODUCT', 'TRACK_ORDER',
        ]
        if value not in VALID_INTENTS:
            raise serializers.ValidationError(f"Intent invalide: {value}")
        return value

    def update(self, instance, validated_data):
        instance.review_label = validated_data['review_label']
        instance.reviewed = True
        instance.save(update_fields=['review_label', 'reviewed'])
        return instance

class RetrainingLogSerializer(serializers.ModelSerializer):
    duration_seconds = serializers.SerializerMethodField()
    f1_improvement   = serializers.SerializerMethodField()

    class Meta:
        model = RetrainingLog
        fields = '__all__'

    def get_duration_seconds(self, obj):
        if obj.started_at and obj.finished_at:
            return int((obj.finished_at - obj.started_at).total_seconds())
        return None

    def get_f1_improvement(self, obj):
        if obj.old_f1 and obj.new_f1:
            return round(obj.new_f1 - obj.old_f1, 4)
        return None

class ManualDatasetSerializer(serializers.ModelSerializer):
    """
    Sérialiseur pour la table ManualDataset.
    """
    class Meta:
        model = ManualDataset
        fields = ['id', 'original_text', 'label', 'source', 'created_at']
