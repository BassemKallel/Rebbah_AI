from django import forms
from django.contrib import admin
from django.utils.html import format_html
from django.db.models.signals import post_save
from django.dispatch import receiver
from ..models import ResponseTemplate
from apps.gateway.services.template_service import invalidate_template_cache


INTENT_CHOICES_BY_TYPE = {
    "response": [
        ("GREETING", "GREETING"), ("ASK_PRICE", "ASK_PRICE"), ("ASK_AVAILABILITY", "ASK_AVAILABILITY"),
        ("ORDER_PRODUCT", "ORDER_PRODUCT"), ("ASK_DELIVERY", "ASK_DELIVERY"), ("ASK_DETAILS", "ASK_DETAILS"),
        ("ASK_DISCOUNT", "ASK_DISCOUNT"), ("ASK_LOCATION", "ASK_LOCATION"), ("CANCEL_ORDER", "CANCEL_ORDER"),
        ("CHECK_PACKAGE", "CHECK_PACKAGE"), ("COMPLAINT", "COMPLAINT"), ("CONFIRM_DENY", "CONFIRM_DENY"),
        ("INFORM_INFO", "INFORM_INFO"), ("TRACK_ORDER", "TRACK_ORDER"), ("UNKNOWN", "UNKNOWN"), ("NOISE", "NOISE"),
    ],
    "missing_entity": [("product", "product"), ("color", "color"), ("size", "size"), ("quantity", "quantity"), ("address", "address"), ("phone_number", "phone_number")],
    "out_of_stock":    [("default", "default"), ("available", "available"), ("sizes", "sizes"), ("colors", "colors")],
    "order_confirmed": [("with_ref", "with_ref"), ("no_ref", "no_ref")],
    "disambiguation":  [("default", "default")],
    "misc": [
        ("missing_entity_default", "missing_entity_default"), ("inform_info_default", "inform_info_default"),
        ("inform_product_default", "inform_product_default"), ("ask_availability_default", "ask_availability_default"),
        ("ask_price_default", "ask_price_default"), ("noise_default", "noise_default"), ("stock_check_error", "stock_check_error"),
    ],
}
ALL_INTENT_CHOICES = [("", "--- Choisir un intent ---")] + [choice for choices in INTENT_CHOICES_BY_TYPE.values() for choice in choices]


class ResponseTemplateForm(forms.ModelForm):
    intent = forms.ChoiceField(choices=ALL_INTENT_CHOICES)
    class Meta:
        model = ResponseTemplate
        fields = '__all__'
        widgets = {'text': forms.Textarea(attrs={'rows': 4, 'style': 'width:100%;font-family:monospace'})}


@admin.register(ResponseTemplate)
class ResponseTemplateAdmin(admin.ModelAdmin):
    form               = ResponseTemplateForm
    list_display       = ('text_preview', 'intent', 'template_type', 'language', 'shop_id', 'is_default', 'updated_at')
    list_display_links = ('text_preview',)
    list_filter        = ('language', 'template_type', 'is_default')
    search_fields      = ('shop_id', 'intent', 'text')
    list_editable      = ('is_default',)
    ordering           = ('template_type', 'language', 'intent')
    list_per_page      = 50

    fieldsets = (
        ('Identification', {'fields': ('shop_id', 'language', 'template_type', 'intent', 'is_default'), 'description': '<b>shop_id</b> = laisser vide pour le template système par défaut.'}),
        ('Contenu', {'fields': ('text', 'available_variables'), 'description': 'Placeholders: <code>{product}</code> <code>{color}</code> <code>{size}</code> <code>{price}</code> <code>{ref}</code> <code>{ai_agent_name}</code> <code>{shop_name}</code>'}),
    )

    def text_preview(self, obj):
        preview = (obj.text or '')[:100].replace('\n', ' ')
        return preview + '…' if len(obj.text or '') > 100 else preview
    text_preview.short_description = 'Texte'


@receiver(post_save, sender=ResponseTemplate)
def invalidate_response_template_cache(sender, instance, **kwargs):
    """Auto-invalidate Redis cache whenever a template is saved in Admin."""
    invalidate_template_cache(shop_id=instance.shop_id, language=instance.language, template_type=instance.template_type, intent=instance.intent)
