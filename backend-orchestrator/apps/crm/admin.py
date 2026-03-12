from django.contrib import admin
from django.utils.html import format_html
import json
from .models import Lead, Conversation, Message, BotConfiguration
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


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('sender', 'text', 'extracted_intent', 'pretty_entities', 'is_error', 'created_at')
    can_delete = False
    fields = ('sender', 'text', 'extracted_intent', 'pretty_entities', 'is_error', 'created_at')

    def pretty_entities(self, obj):
        if not obj.extracted_entities:
            return "-"
        return format_html("<pre>{}</pre>", json.dumps(obj.extracted_entities, indent=2, ensure_ascii=False))
    pretty_entities.short_description = "Entités Extraites"

class ConversationInline(admin.TabularInline):
    model = Conversation
    extra = 0
    readonly_fields = ('shop_id', 'state', 'created_at', 'updated_at')
    can_delete = False
    fields = ('shop_id', 'state', 'created_at', 'updated_at')
    show_change_link = True

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'platform_id', 'shop_id', 'pending_order_reference', 'product_id', 'color', 'size', 'agent_confirmation_pending', 'created_at')
    list_filter = ('agent_confirmation_pending', 'has_pending_order', 'shop_id', 'created_at')
    search_fields = ('name', 'platform_id', 'pending_order_reference', 'phone_number', 'product_id')
    readonly_fields = ('pending_order_created_at', 'created_at', 'updated_at', 'pending_order_reference')
    list_editable = ('agent_confirmation_pending',)
    date_hierarchy = 'created_at'
    inlines = [ConversationInline]
    
    fieldsets = (
        ('Info Client', {
            'fields': ('platform_id', 'name'),
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
    list_display = ('__str__', 'lead', 'shop_id', 'state', 'created_at')
    list_filter = ('state', 'shop_id')
    search_fields = ('lead__platform_id', 'lead__name')
    readonly_fields = ('created_at', 'updated_at', 'pretty_context', 'pretty_missing')
    inlines = [MessageInline]
    date_hierarchy = 'created_at'
    ordering = ('-updated_at',)

    fieldsets = (
        ('Général', {
            'fields': ('lead', 'shop_id', 'state')
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
    list_display = ('sender', 'get_lead', 'text_preview', 'extracted_intent', 'is_error', 'created_at')
    list_filter = ('sender', 'is_error', 'extracted_intent', 'created_at')
    search_fields = ('text', 'conversation__lead__platform_id', 'extracted_intent')
    readonly_fields = ('pretty_entities',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    def text_preview(self, obj):
        return obj.text[:80] + "..." if len(obj.text) > 80 else obj.text
    text_preview.short_description = 'Message Content'

    def get_lead(self, obj):
        return obj.conversation.lead
    get_lead.short_description = 'Lead'
    get_lead.admin_order_field = 'conversation__lead'

    def pretty_entities(self, obj):
        if not obj.extracted_entities:
            return "-"
        return format_html("<pre>{}</pre>", json.dumps(obj.extracted_entities, indent=2, ensure_ascii=False))
    pretty_entities.short_description = "Extraction Data"
