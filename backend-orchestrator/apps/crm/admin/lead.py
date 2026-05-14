from django.contrib import admin
from django.utils.html import format_html
from ..models import Lead, Conversation
from ..models.lead import OrderItem
import json


class ConversationInline(admin.TabularInline):
    model = Conversation
    extra = 0
    readonly_fields = ('sender_id', 'shop_id', 'state', 'created_at', 'updated_at')
    can_delete = False
    fields = ('sender_id', 'shop_id', 'state', 'created_at', 'updated_at')
    show_change_link = True

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_id', 'product_name', 'quantity', 'price', 'attributes', 'created_at')
    can_delete = False
    fields = ('product_id', 'product_name', 'quantity', 'price', 'attributes', 'created_at')


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display   = ('name', 'platform_id', 'shop_id', 'lead_status', 'pending_order_reference', 'agent_confirmation_pending', 'created_at')
    list_filter    = ('lead_status', 'agent_confirmation_pending', 'has_pending_order', 'shop_id', 'created_at')
    search_fields  = ('name', 'platform_id', 'pending_order_reference', 'uuid')
    readonly_fields = ('pending_order_created_at', 'created_at', 'updated_at', 'pending_order_reference', 'pretty_extracted_data')
    list_editable  = ('agent_confirmation_pending',)
    date_hierarchy = 'created_at'
    inlines        = [OrderItemInline, ConversationInline]
    ordering       = ('-created_at',)

    fieldsets = (
        ('Info Client',    {'fields': ('platform_id', 'name', 'lead_status'), 'classes': ('wide',)}),
        ('Pré-Commande / Lead',   {'fields': (('has_pending_order', 'agent_confirmation_pending'), ('pending_order_reference', 'pending_order_created_at'), 'shop_id'), 'classes': ('wide',)}),
        ('Entités Extraites (IA)', {
            'fields': ('pretty_extracted_data',),
            'classes': ('wide',),
            'description': 'Toutes les informations métier universelles capturées par Gemini.',
        }),
        ('Système',        {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    @admin.display(description='Extracted Data (JSON)')
    def pretty_extracted_data(self, obj):
        data = obj.extracted_data
        if not data:
            return format_html('<span style="color:#999">—</span>')
        formatted = json.dumps(data, ensure_ascii=False, indent=2)
        return format_html(
            '<pre style="background:var(--darkened-bg, rgba(128,128,128,0.1)); color:var(--body-fg); '
            'padding:8px; border-radius:4px; font-size:12px; max-height:200px; overflow:auto;">{}</pre>',
            formatted
        )
