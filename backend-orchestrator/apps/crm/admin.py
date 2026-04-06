from django.contrib import admin
from django.utils.html import format_html
import json
from .models import Lead, Conversation, Message, BotConfiguration, Company, NLUFallbackLog, ProductVector, UserProfile
from apps.gateway.response_templates import TEMPLATES

@admin.register(BotConfiguration)
class BotConfigurationAdmin(admin.ModelAdmin):
    list_display = ('shop_id', 'shop_name', 'language', 'created_at')
    list_filter = ('language', 'created_at')
    search_fields = ('shop_id', 'shop_name')

    
    fieldsets = (
        ('General', {
            'fields': ('shop_id', 'shop_name', 'language', 'ai_agent_name')
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
            'fields': ('name', 'shop_id', 'is_active', 'dashboard_token')
        }),
        ('Meta Integration', {
            'fields': ('meta_page_id', 'meta_page_access_token', 'instagram_page_id'),
            'description': 'Facebook Page ID et Token Messenger pour chaque shop.'
        }),
        ('LLM Response Mode', {
            'fields': ('response_mode', 'gemini_api_key', 'llm_context'),
            'description': 'Mode de réponse IA : NLU (TunBERT) ou LLM Direct (Gemini).'
        }),
        ('Bot Configuration', {
            'fields': ('bot_config',),
            'description': 'Lier à une configuration de bot pour la personnalisation.'
        }),
    )
    readonly_fields = ('dashboard_token',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'role', 'created_at')
    list_filter = ('role', 'company')
    search_fields = ('user__username', 'user__email', 'company__name')
    raw_id_fields = ('user', 'company')


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('sender', 'text', 'extracted_intent', 'confidence_badge', 'state_transition', 'pretty_entities', 'is_error', 'is_fallback', 'created_at')
    can_delete = False
    fields = ('sender', 'text', 'extracted_intent', 'confidence_badge', 'state_transition', 'pretty_entities', 'is_error', 'is_fallback', 'created_at')

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
    list_display = ('sender', 'get_lead', 'text_preview', 'extracted_intent', 'confidence_badge', 'is_error', 'is_fallback', 'created_at')
    list_filter = ('sender', 'is_error', 'is_fallback', 'extracted_intent', 'created_at')
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
            'fields': ('text', 'available_variables'),
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


@admin.register(NLUFallbackLog)
class NLUFallbackLogAdmin(admin.ModelAdmin):
    list_display = ('original_text_preview', 'trigger_reason', 'tunbert_intent',
                    'tunbert_confidence_badge', 'gemini_intent', 'gemini_confidence_badge',
                    'intent_changed', 'reviewed', 'created_at')
    list_filter = ('trigger_reason', 'intent_changed', 'reviewed', 'created_at')
    search_fields = ('original_text', 'tunbert_intent', 'gemini_intent')
    readonly_fields = ('message', 'original_text', 'tunbert_intent', 'tunbert_confidence',
                       'pretty_tunbert_entities', 'gemini_intent', 'gemini_confidence',
                       'pretty_gemini_entities', 'trigger_reason', 'intent_changed', 'created_at')
    list_editable = ('reviewed',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    fieldsets = (
        ('Message Original', {
            'fields': ('message', 'original_text', 'trigger_reason')
        }),
        ('TunBERT (avant correction)', {
            'fields': ('tunbert_intent', 'tunbert_confidence', 'pretty_tunbert_entities')
        }),
        ('Gemini (correction)', {
            'fields': ('gemini_intent', 'gemini_confidence', 'pretty_gemini_entities')
        }),
        ('Active Learning', {
            'fields': ('intent_changed', 'reviewed', 'review_label')
        }),
    )

    def original_text_preview(self, obj):
        return obj.original_text[:60] + '...' if len(obj.original_text) > 60 else obj.original_text
    original_text_preview.short_description = 'Texte'

    def tunbert_confidence_badge(self, obj):
        if obj.tunbert_confidence is None:
            return '-'
        score = obj.tunbert_confidence
        pct = f'{score:.0%}'
        color = '#27ae60' if score >= 0.8 else ('#e67e22' if score >= 0.5 else '#e74c3c')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-weight:bold">{}</span>',
            color, pct
        )
    tunbert_confidence_badge.short_description = 'TunBERT Conf.'

    def gemini_confidence_badge(self, obj):
        if obj.gemini_confidence is None:
            return '-'
        score = obj.gemini_confidence
        pct = f'{score:.0%}'
        color = '#27ae60' if score >= 0.8 else ('#e67e22' if score >= 0.5 else '#e74c3c')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-weight:bold">{}</span>',
            color, pct
        )
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


# ── ProductVector Admin (read-only, superuser only) ───────────────────────────

@admin.register(ProductVector)
class ProductVectorAdmin(admin.ModelAdmin):
    """
    Read-only view of the products_vector table (managed by vision-service).
    Accessible only to Django superusers — no add/edit/delete.
    """
    list_display  = ('id', 'shop_id', 'product_id', 'variation_id', 'image_preview', 'created_at')
    list_filter   = ('shop_id',)
    search_fields = ('product_id', 'variation_id', 'shop_id')
    list_per_page = 50
    ordering      = ('shop_id', 'product_id')
    readonly_fields = ('id', 'product_id', 'variation_id', 'shop_id', 'created_at', 'image_preview_large')

    # ── Superuser-only access ─────────────────────────────────────────────
    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # ── Image previews ────────────────────────────────────────────────────
    def image_preview(self, obj):
        if obj.image_url:
            return format_html(
                '<img src="{}" style="height:48px;width:48px;object-fit:cover;'
                'border-radius:4px;border:1px solid #ddd;" '
                'onerror="this.style.display=\'none\'"/>',
                obj.image_url,
            )
        return '—'
    image_preview.short_description = 'Image'

    def image_preview_large(self, obj):
        if obj.image_url:
            return format_html(
                '<img src="{}" style="max-height:200px;max-width:200px;'
                'border-radius:8px;border:1px solid #ddd;"/>'
                '<br><small style="color:#888">{}</small>',
                obj.image_url, obj.image_url,
            )
        return '—'
    image_preview_large.short_description = 'Image'

    # ── Detail view ───────────────────────────────────────────────────────
    fieldsets = (
        ('Identification', {
            'fields': ('id', 'shop_id', 'product_id', 'variation_id', 'created_at'),
        }),
        ('Image', {
            'fields': ('image_preview_large',),
        }),
    )
