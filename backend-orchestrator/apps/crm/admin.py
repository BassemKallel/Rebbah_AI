from django.contrib import admin
from .models import Lead, Conversation, Message

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('sender', 'text', 'extracted_intent', 'extracted_entities', 'is_error', 'created_at')
    can_delete = False

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'platform_id', 'pending_order_reference', 'color', 'size', 'agent_confirmation_pending', 'created_at')
    list_filter = ('agent_confirmation_pending', 'has_pending_order', 'created_at')
    search_fields = ('name', 'platform_id', 'pending_order_reference')
    readonly_fields = ('pending_order_created_at', 'created_at', 'updated_at', 'pending_order_reference')
    
    fieldsets = (
        ('Client Info', {
            'fields': ('platform_id', 'name')
        }),
        ('Pré-Commande', {
            'fields': (
                'has_pending_order', 'agent_confirmation_pending', 
                'pending_order_reference', 'pending_order_created_at',
                'shop_id'
            )
        }),
        ('Produit', {
            'fields': ('product_id', 'variation_id', 'color', 'size', 'quantity')
        }),
        ('Livraison', {
            'fields': ('address', 'phone_number')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    ordering = ('-created_at',)

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'shop_id', 'state', 'created_at')
    list_filter = ('state', 'shop_id')
    search_fields = ('lead__platform_id', 'lead__name')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [MessageInline]
    ordering = ('-updated_at',)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'get_lead', 'text_preview', 'extracted_intent', 'is_error', 'created_at')
    list_filter = ('sender', 'is_error', 'extracted_intent')
    search_fields = ('text', 'conversation__lead__platform_id')
    ordering = ('-created_at',)

    def text_preview(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Message Text'

    def get_lead(self, obj):
        return obj.conversation.lead
    get_lead.short_description = 'Lead'
    get_lead.admin_order_field = 'conversation__lead'
