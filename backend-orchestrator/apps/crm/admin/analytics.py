import requests as _requests
from django.conf import settings as _settings
from django.contrib import admin, messages as _messages
from django.utils.html import format_html
import json
from ..models import NLUFallbackLog, ProductVector


def _vision_base():
    return _settings.VISION_SERVICE_URL.rstrip('/')


@admin.register(NLUFallbackLog)
class NLUFallbackLogAdmin(admin.ModelAdmin):
    list_display  = ('original_text_preview', 'trigger_reason', 'tunbert_intent', 'tunbert_confidence_badge', 'gemini_intent', 'gemini_confidence_badge', 'intent_changed', 'reviewed', 'created_at')
    list_filter   = ('trigger_reason', 'intent_changed', 'reviewed', 'created_at')
    search_fields = ('original_text', 'tunbert_intent', 'gemini_intent')
    readonly_fields = ('message', 'original_text', 'tunbert_intent', 'tunbert_confidence', 'pretty_tunbert_entities', 'gemini_intent', 'gemini_confidence', 'pretty_gemini_entities', 'trigger_reason', 'intent_changed', 'created_at')
    list_editable = ('reviewed',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    fieldsets = (
        ('Message Original', {'fields': ('message', 'original_text', 'trigger_reason')}),
        ('TunBERT (avant correction)', {'fields': ('tunbert_intent', 'tunbert_confidence', 'pretty_tunbert_entities')}),
        ('Gemini (correction)', {'fields': ('gemini_intent', 'gemini_confidence', 'pretty_gemini_entities')}),
        ('Active Learning', {'fields': ('intent_changed', 'reviewed', 'review_label')}),
    )

    def original_text_preview(self, obj):
        return obj.original_text[:60] + '...' if len(obj.original_text) > 60 else obj.original_text
    original_text_preview.short_description = 'Texte'

    def _confidence_badge(self, score):
        if score is None:
            return '-'
        color = '#27ae60' if score >= 0.8 else ('#e67e22' if score >= 0.5 else '#e74c3c')
        return format_html('<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-weight:bold">{}</span>', color, f'{score:.0%}')

    def tunbert_confidence_badge(self, obj):
        return self._confidence_badge(obj.tunbert_confidence)
    tunbert_confidence_badge.short_description = 'TunBERT Conf.'

    def gemini_confidence_badge(self, obj):
        return self._confidence_badge(obj.gemini_confidence)
    gemini_confidence_badge.short_description = 'Gemini Conf.'

    def pretty_tunbert_entities(self, obj):
        if not obj.tunbert_entities:
            return '-'
        return format_html('<pre>{}</pre>', json.dumps(obj.tunbert_entities, indent=2, ensure_ascii=False))
    pretty_tunbert_entities.short_description = 'Entites TunBERT'

    def pretty_gemini_entities(self, obj):
        if not obj.gemini_entities:
            return '-'
        return format_html('<pre>{}</pre>', json.dumps(obj.gemini_entities, indent=2, ensure_ascii=False))
    pretty_gemini_entities.short_description = 'Entites Gemini'


@admin.register(ProductVector)
class ProductVectorAdmin(admin.ModelAdmin):
    list_display    = ('id', 'shop_id', 'product_id', 'variation_id', 'image_preview', 'created_at')
    list_filter     = ('shop_id',)
    search_fields   = ('product_id', 'variation_id', 'shop_id')
    list_per_page   = 50
    ordering        = ('shop_id', 'product_id')
    readonly_fields = ('id', 'product_id', 'variation_id', 'shop_id', 'created_at', 'image_preview_large')
    actions         = ['clear_vectors_by_shop', 'clear_all_vectors']

    def has_module_permission(self, request): return request.user.is_active and request.user.is_superuser
    def has_view_permission(self, request, obj=None): return request.user.is_active and request.user.is_superuser
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

    @admin.action(description="Vider les vecteurs des boutiques selectionnees")
    def clear_vectors_by_shop(self, request, queryset):
        for shop_id in queryset.values_list('shop_id', flat=True).distinct():
            try:
                resp = _requests.delete(f"{_vision_base()}/vectors/", params={"shop_id": shop_id}, timeout=10)
                resp.raise_for_status()
                self.message_user(request, f"Boutique {shop_id} : {resp.json().get('deleted', '?')} vecteurs supprimes.", level=_messages.SUCCESS)
            except Exception as e:
                self.message_user(request, f"Erreur pour {shop_id} : {e}", level=_messages.ERROR)

    @admin.action(description="VIDER TOUTE LA BASE VECTORIELLE (toutes boutiques)")
    def clear_all_vectors(self, request, queryset):
        try:
            resp = _requests.delete(f"{_vision_base()}/vectors/", timeout=10)
            resp.raise_for_status()
            self.message_user(request, f"Base vectorielle videe : {resp.json().get('deleted', '?')} vecteurs supprimes.", level=_messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Erreur : {e}", level=_messages.ERROR)

    def image_preview(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="height:48px;width:48px;object-fit:cover;border-radius:4px;border:1px solid #ddd;" onerror="this.style.display=\'none\'"/>', obj.image_url)
        return '—'
    image_preview.short_description = 'Image'

    def image_preview_large(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="max-height:200px;max-width:200px;border-radius:8px;border:1px solid #ddd;"/><br><small style="color:#888">{}</small>', obj.image_url, obj.image_url)
        return '—'
    image_preview_large.short_description = 'Image'

    fieldsets = (
        ('Identification', {'fields': ('id', 'shop_id', 'product_id', 'variation_id', 'created_at')}),
        ('Image', {'fields': ('image_preview_large',)}),
    )
