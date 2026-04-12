from django.contrib import admin
from django.utils.html import format_html
from ..models import Lead, Conversation


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
    readonly_fields = ('uuid', 'pending_order_created_at', 'created_at', 'updated_at', 'pending_order_reference')
    list_editable  = ('agent_confirmation_pending',)
    date_hierarchy = 'created_at'
    inlines        = [ConversationInline]
    ordering       = ('-created_at',)

    fieldsets = (
        ('Info Client', {'fields': ('uuid', 'platform_id', 'name', 'lead_status'), 'classes': ('wide',)}),
        ('Pré-Commande', {'fields': (('has_pending_order', 'agent_confirmation_pending'), ('pending_order_reference', 'pending_order_created_at'), 'shop_id'), 'classes': ('wide',)}),
        ('Détails Produit', {'fields': (('product_id', 'variation_id'), ('color', 'size', 'quantity')), 'classes': ('wide',)}),
        ('Livraison', {'fields': ('address', 'phone_number'), 'classes': ('wide',)}),
        ('Système', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
