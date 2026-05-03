from django.contrib import admin
from django.utils.html import format_html
from ..models import Lead, Conversation
import json


class ConversationInline(admin.TabularInline):
    model = Conversation
    extra = 0
    readonly_fields = ('sender_id', 'lead_uuid', 'shop_id', 'state', 'created_at', 'updated_at')
    can_delete = False
    fields = ('sender_id', 'lead_uuid', 'shop_id', 'state', 'created_at', 'updated_at')
    show_change_link = True


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display   = ('name', 'platform_id', 'uuid', 'shop_id', 'lead_status', 'pending_order_reference', 'product_id', 'color', 'size', 'agent_confirmation_pending', 'created_at')
    list_filter    = ('lead_status', 'agent_confirmation_pending', 'has_pending_order', 'shop_id', 'created_at')
    search_fields  = ('name', 'platform_id', 'pending_order_reference', 'phone_number', 'product_id')
    readonly_fields = ('uuid', 'pending_order_created_at', 'created_at', 'updated_at', 'pending_order_reference', 'pretty_extra_data')
    list_editable  = ('agent_confirmation_pending',)
    date_hierarchy = 'created_at'
    inlines        = [ConversationInline]
    ordering       = ('-created_at',)

    fieldsets = (
        ('Info Client',    {'fields': ('uuid', 'platform_id', 'name', 'lead_status'), 'classes': ('wide',)}),
        ('Pré-Commande',   {'fields': (('has_pending_order', 'agent_confirmation_pending'), ('pending_order_reference', 'pending_order_created_at'), 'shop_id'), 'classes': ('wide',)}),
        ('Détails Produit',{'fields': (('product_id', 'variation_id'), ('color', 'size', 'quantity')), 'classes': ('wide',)}),
        ('Livraison',      {'fields': ('address', 'phone_number'), 'classes': ('wide',)}),
        ('Données Domaine Spécifique', {
            'fields': ('pretty_extra_data',),
            'classes': ('wide',),
            'description': 'Entités collectées spécifiques au domaine (restaurant, médical, immobilier…)',
        }),
        ('Système',        {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    @admin.display(description='Extra Data (JSON)')
    def pretty_extra_data(self, obj):
        data = obj.extra_data
        if not data:
            return format_html('<span style="color:#999">—</span>')
        formatted = json.dumps(data, ensure_ascii=False, indent=2)
        return format_html(
            '<pre style="background:#f8f8f8;padding:8px;border-radius:4px;'
            'font-size:12px;max-height:200px;overflow:auto;">{}</pre>',
            formatted
        )
