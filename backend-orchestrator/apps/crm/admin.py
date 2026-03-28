from django.contrib import admin
from django.utils.html import format_html
import json
from .models import Lead, Conversation, Message, BotConfiguration, Company
from apps.gateway.response_templates import TEMPLATES

@admin.register(BotConfiguration)
class BotConfigurationAdmin(admin.ModelAdmin):
    list_display = ('shop_id', 'shop_name', 'language', 'created_at')
    list_filter = ('language', 'created_at')
    search_fields = ('shop_id', 'shop_name')
    readonly_fields = ('default_intents',)
    
    fieldsets = (
        ('General', {
            'fields': ('shop_id', 'shop_name', 'language','ai_agent_name')
        }),
        ('Custom Responses', {
            'fields': ('custom_intents', 'default_intents')
        }),
    )

    def default_intents(self, obj):
        if not obj or not getattr(obj, 'language', None):
            return "-"
        lang = obj.language if obj.language in TEMPLATES else 'FR'
        data = TEMPLATES.get(lang, {})
        return format_html("<pre>{}</pre>", json.dumps(data, indent=2, ensure_ascii=False))
    default_intents.short_description = "Default Intents (Usine)"


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'shop_id', 'meta_page_id', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'shop_id', 'meta_page_id')
    list_editable = ('is_active',)
    
    fieldsets = (
        ('Identité', {
            'fields': ('name', 'shop_id', 'is_active')
        }),
        ('Meta & Tiktak Integration', {
            'fields': ('meta_page_id', 'meta_page_access_token', 'instagram_page_id', 'tiktak_api_token'),
            'description': 'Facebook Page ID, Token Messenger, et Token API Tiktak pour chaque shop.'
        }),
        ('Bot Configuration', {
            'fields': ('bot_config',),
            'description': 'Lier à une configuration de bot pour la personnalisation.'
        }),
    )


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('sender', 'text', 'extracted_intent', 'confidence_badge', 'state_transition', 'pretty_entities', 'is_error', 'created_at')
    can_delete = False
    fields = ('sender', 'text', 'extracted_intent', 'confidence_badge', 'state_transition', 'pretty_entities', 'is_error', 'created_at')

    def confidence_badge(self, obj):
        if obj.intent_confidence_score is None:
            return "-"
        score = obj.intent_confidence_score
        pct   = f"{score:.0%}"
        color = "#27ae60" if score >= 0.8 else ("#e67e22" if score >= 0.5 else "#e74c3c")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-weight:bold">{}</span>',
            color, pct
        )
    confidence_badge.short_description = "Confiance"

    def state_transition(self, obj):
        before = obj.conversation_state_before or "?"
        after  = obj.conversation_state_after  or "?"
        if before == after:
            return format_html('<span style="color:#888">{}</span>', before)
        return format_html(
            '<span style="color:#2980b9;font-weight:bold">{}</span>'
            ' → '
            '<span style="color:#27ae60;font-weight:bold">{}</span>',
            before, after
        )
    state_transition.short_description = "État (avant → après)"

    def pretty_entities(self, obj):
        if not obj.extracted_entities:
            return "-"
        return format_html("<pre>{}</pre>", json.dumps(obj.extracted_entities, indent=2, ensure_ascii=False))
    pretty_entities.short_description = "Entités Extraites"

class ConversationInline(admin.TabularInline):
    model = Conversation
    extra = 0
    readonly_fields = ('sender_id', 'lead_uuid', 'shop_id', 'state', 'created_at', 'updated_at')
    can_delete = False
    fields = ('sender_id', 'lead_uuid', 'shop_id', 'state', 'created_at', 'updated_at')
    show_change_link = True

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display  = ('name', 'platform_id', 'uuid', 'shop_id', 'pending_order_reference', 'product_id', 'color', 'size', 'agent_confirmation_pending', 'created_at')
    list_filter   = ('agent_confirmation_pending', 'has_pending_order', 'shop_id', 'created_at')
    search_fields = ('name', 'platform_id', 'pending_order_reference', 'phone_number', 'product_id')
    readonly_fields = ('uuid', 'pending_order_created_at', 'created_at', 'updated_at', 'pending_order_reference')
    list_editable = ('agent_confirmation_pending',)
    date_hierarchy = 'created_at'
    inlines = [ConversationInline]
    
    fieldsets = (
        ('Info Client', {
            'fields': ('uuid', 'platform_id', 'name'),
            'classes': ('wide',)
        }),
        ('Pré-Commande (En Attente)', {
            'fields': (
                ('has_pending_order', 'agent_confirmation_pending'),
                ('pending_order_reference', 'pending_order_created_at'),
                'shop_id'
            ),
            'classes': ('wide',)
        }),
        ('Détails Produit', {
            'fields': (
                ('product_id', 'variation_id'),
                ('color', 'size', 'quantity')
            ),
            'classes': ('wide',)
        }),
        ('Informations de Livraison', {
            'fields': ('address', 'phone_number'),
            'classes': ('wide',)
        }),
        ('Système', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    ordering = ('-created_at',)

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display  = ('sender_id', 'lead', 'shop_id', 'state', 'created_at')
    list_filter   = ('state', 'shop_id')
    search_fields = ('sender_id', 'lead__platform_id', 'lead__name', 'lead_uuid')
    readonly_fields = ('lead_uuid', 'sender_id', 'created_at', 'updated_at', 'pretty_context', 'pretty_missing')
    inlines = [MessageInline]
    date_hierarchy = 'created_at'
    ordering = ('-updated_at',)

    fieldsets = (
        ('Identification', {
            'fields': ('sender_id', 'lead', 'lead_uuid', 'shop_id', 'state')
        }),
        ('Contexte & État', {
            'fields': ('pretty_context', 'pretty_missing')
        }),
        ('Système', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def pretty_context(self, obj):
        if not obj.context_data:
            return "-"
        return format_html("<pre>{}</pre>", json.dumps(obj.context_data, indent=2, ensure_ascii=False))
    pretty_context.short_description = "Context Data (JSON)"

    def pretty_missing(self, obj):
        if not obj.missing_entities:
            return "-"
        return format_html("<pre>{}</pre>", json.dumps(obj.missing_entities, indent=2, ensure_ascii=False))
    pretty_missing.short_description = "Missing Entities (JSON)"

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'get_lead', 'text_preview', 'extracted_intent', 'confidence_badge', 'is_error', 'created_at')
    list_filter = ('sender', 'is_error', 'extracted_intent', 'created_at')
    search_fields = ('text', 'conversation__lead__platform_id', 'extracted_intent')
    readonly_fields = ('pretty_entities', 'confidence_badge')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    def text_preview(self, obj):
        return obj.text[:80] + "..." if len(obj.text) > 80 else obj.text
    text_preview.short_description = 'Message Content'

    def get_lead(self, obj):
        return obj.conversation.lead
    get_lead.short_description = 'Lead'
    get_lead.admin_order_field = 'conversation__lead'

    def confidence_badge(self, obj):
        if obj.intent_confidence_score is None:
            return "-"
        score = obj.intent_confidence_score
        pct   = f"{score:.0%}"
        color = "#27ae60" if score >= 0.8 else ("#e67e22" if score >= 0.5 else "#e74c3c")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-weight:bold">{}</span>',
            color, pct
        )
    confidence_badge.short_description = "Confiance Intention"
    confidence_badge.allow_tags = True

    def pretty_entities(self, obj):
        if not obj.extracted_entities:
            return "-"
        return format_html("<pre>{}</pre>", json.dumps(obj.extracted_entities, indent=2, ensure_ascii=False))
    pretty_entities.short_description = "Extraction Data"


# ── ResponseTemplate Admin ────────────────────────────────────────────────────
from django import forms
from .models import ResponseTemplate
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.gateway.services.template_service import invalidate_template_cache


# ── Intent choices per template_type (mirrors response_templates.py) ──────────
INTENT_CHOICES_BY_TYPE = {
    "response": [
        ("GREETING",       "GREETING — Salutation"),
        ("ASK_PRICE",      "ASK_PRICE — Demande de prix"),
        ("ASK_AVAILABILITY","ASK_AVAILABILITY — Disponibilité"),
        ("ORDER_PRODUCT",  "ORDER_PRODUCT — Commander"),
        ("ASK_DELIVERY",   "ASK_DELIVERY — Livraison"),
        ("ASK_DETAILS",    "ASK_DETAILS — Détails produit"),
        ("ASK_DISCOUNT",   "ASK_DISCOUNT — Remise"),
        ("ASK_LOCATION",   "ASK_LOCATION — Localisation"),
        ("CANCEL_ORDER",   "CANCEL_ORDER — Annuler"),
        ("CHECK_PACKAGE",  "CHECK_PACKAGE — Suivi colis"),
        ("COMPLAINT",      "COMPLAINT — Réclamation"),
        ("CONFIRM_DENY",   "CONFIRM_DENY — Confirmation/Refus"),
        ("INFORM_INFO",    "INFORM_INFO — Informer"),
        ("TRACK_ORDER",    "TRACK_ORDER — Suivre commande"),
        ("UNKNOWN",        "UNKNOWN — Incompris"),
        ("NOISE",          "NOISE — Message vide/bruit"),
    ],
    "missing_entity": [
        ("product",      "product — Produit"),
        ("color",        "color — Couleur"),
        ("size",         "size — Taille"),
        ("quantity",     "quantity — Quantité"),
        ("address",      "address — Adresse"),
        ("phone_number", "phone_number — Téléphone"),
    ],
    "out_of_stock": [
        ("default",   "default — Message principal rupture"),
        ("available", "available — Disponible en : {avail}"),
        ("sizes",     "sizes — Tailles disponibles : {avail}"),
        ("colors",    "colors — Couleurs disponibles : {avail}"),
    ],
    "order_confirmed": [
        ("with_ref", "with_ref — Confirmé avec référence #{ref}"),
        ("no_ref",   "no_ref — Confirmé sans référence"),
    ],
    "disambiguation": [
        ("default", "default — Plusieurs articles trouvés"),
    ],
    "misc": [
        ("missing_entity_default",   "missing_entity_default — MISSING_ENTITY_DEFAULT"),
        ("inform_info_default",       "inform_info_default — INFORM_INFO_DEFAULT"),
        ("inform_product_default",    "inform_product_default — INFORM_PRODUCT_DEFAULT"),
        ("ask_availability_default",  "ask_availability_default — ASK_AVAILABILITY_DEFAULT"),
        ("ask_price_default",         "ask_price_default — ASK_PRICE_DEFAULT"),
        ("noise_default",             "noise_default — NOISE_DEFAULT"),
        ("stock_check_error",         "stock_check_error — STOCK_CHECK_ERROR"),
    ],
}

ALL_INTENT_CHOICES = [("", "--- Choisir un intent ---")] + [
    choice for choices in INTENT_CHOICES_BY_TYPE.values() for choice in choices
]




class ResponseTemplateForm(forms.ModelForm):
    intent = forms.ChoiceField(choices=ALL_INTENT_CHOICES)

    class Meta:
        model = ResponseTemplate
        fields = '__all__'
        widgets = {
            'text': forms.Textarea(attrs={'rows': 4, 'style': 'width:100%;font-family:monospace'}),
        }


@admin.register(ResponseTemplate)
class ResponseTemplateAdmin(admin.ModelAdmin):
    form                 = ResponseTemplateForm
    list_display         = ('text_preview', 'intent', 'template_type', 'language', 'shop_id', 'is_default', 'updated_at')
    list_display_links   = ('text_preview',)
    list_filter          = ('language', 'template_type', 'is_default')
    search_fields        = ('shop_id', 'intent', 'text')
    list_editable        = ('is_default',)
    ordering             = ('template_type', 'language', 'intent')
    list_per_page        = 50

    fieldsets = (
        ('Identification', {
            'fields': ('shop_id', 'language', 'template_type', 'intent', 'is_default'),
            'description': (
                '<b>shop_id</b> = laisser vide pour le template système par défaut. '
                'Renseigner un shop_id pour surcharger uniquement cette boutique.'
            ),
        }),
        ('Contenu', {
            'fields': ('text',),
            'description': (
                'Placeholders disponibles : '
                '<code>{product}</code> <code>{color}</code> <code>{size}</code> '
                '<code>{price}</code> <code>{sizes}</code> <code>{colors}</code> '
                '<code>{ref}</code> <code>{count}</code> <code>{list}</code> '
                '<code>{avail}</code> <code>{first_missing}</code> '
                '<code>{ai_agent_name}</code> <code>{shop_name}</code>'
            ),
        }),
    )

    def text_preview(self, obj):
        preview = (obj.text or '')[:100].replace('\n', ' ')
        if len(obj.text or '') > 100:
            preview += '…'
        return preview
    text_preview.short_description = 'Texte'


@receiver(post_save, sender=ResponseTemplate)
def invalidate_response_template_cache(sender, instance, **kwargs):
    """Auto-invalidate Redis cache whenever a template is saved in Admin."""
    invalidate_template_cache(
        shop_id=instance.shop_id,
        language=instance.language,
        template_type=instance.template_type,
        intent=instance.intent,
    )
