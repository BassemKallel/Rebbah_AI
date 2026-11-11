from django.contrib import admin
from django.utils.html import format_html
import json
from ..models import Conversation, Message


def _get_agent_badge(obj):
    if obj.is_human_agent or obj.agent == "HUMAN":
        return format_html('<span style="background:#f1c40f;color:#000;padding:2px 8px;border-radius:4px;font-weight:bold;font-size:10px">HUMAIN</span>')
    if not obj.agent:
        return "-"
    
    agent_upper = obj.agent.upper().strip()
    color_map = {
        "FAQ": "#3498db",        # Blue
        "SALES": "#2ecc71",      # Green
        "CHECKOUT": "#9b59b6",   # Purple
        "POST_SALES": "#e67e22",  # Orange
        "ERROR": "#e74c3c",      # Red
    }
    color = color_map.get(agent_upper, "#7f8c8d")  # Grey fallback
    return format_html('<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-weight:bold;font-size:10px">{}</span>', color, agent_upper)


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    can_delete = False
    readonly_fields = ('sender', 'text', 'agent', 'extracted_intent', 'state_transition', 'pretty_entities', 'is_error', 'agent_badge', 'created_at')
    fields = ('sender', 'text', 'agent', 'extracted_intent', 'state_transition', 'pretty_entities', 'is_error', 'agent_badge', 'created_at')

    def state_transition(self, obj):
        before = obj.conversation_state_before or "?"
        after  = obj.conversation_state_after  or "?"
        if before == after:
            return format_html('<span style="color:#888">{}</span>', before)
        return format_html('<span style="color:#2980b9;font-weight:bold">{}</span> → <span style="color:#27ae60;font-weight:bold">{}</span>', before, after)
    state_transition.short_description = "État (avant → après)"

    def pretty_entities(self, obj):
        if not obj.extracted_entities:
            return "-"
        return format_html("<pre>{}</pre>", json.dumps(obj.extracted_entities, indent=2, ensure_ascii=False))
    pretty_entities.short_description = "Entités"

    def agent_badge(self, obj):
        return _get_agent_badge(obj)
    agent_badge.short_description = "Agent (Badge)"



@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display   = ('sender_id', 'lead', 'shop_id', 'state', 'handoff_badge', 'human_agent', 'updated_at')
    list_filter    = ('state', 'shop_id', 'is_human_controlled')
    search_fields  = ('sender_id', 'lead__platform_id', 'lead__name', 'lead_uuid')
    readonly_fields = ('sender_id', 'created_at', 'updated_at', 'pretty_context', 'pretty_missing', 'human_takeover_at')
    inlines        = [MessageInline]
    date_hierarchy = 'created_at'
    ordering       = ('-updated_at',)

    fieldsets = (
        ('Identification', {'fields': ('sender_id', 'lead', 'shop_id', 'state')}),
        ('Human Handoff', {'fields': ('is_human_controlled', 'human_agent', 'human_takeover_at'), 'description': 'Gerer manuellement le handoff pour cette conversation.'}),
        ('Contexte & État', {'fields': ('pretty_context', 'pretty_missing')}),
        ('Système', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def handoff_badge(self, obj):
        if obj.is_human_controlled:
            return format_html('<span style="background:#e67e22;color:#fff;padding:2px 8px;border-radius:4px;font-weight:bold;font-size:10px">En direct</span>')
        return format_html('<span style="background:#27ae60;color:#fff;padding:2px 8px;border-radius:4px;font-size:10px">Bot</span>')
    handoff_badge.short_description = 'Controle'

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
    list_display  = ('sender', 'agent_badge', 'get_lead', 'text_preview', 'extracted_intent', 'is_error', 'created_at')
    list_filter   = ('sender', 'agent', 'is_error', 'is_human_agent', 'extracted_intent', 'created_at')
    search_fields = ('text', 'conversation__lead__platform_id', 'extracted_intent')
    readonly_fields = ('pretty_entities', 'agent')
    date_hierarchy = 'created_at'
    ordering      = ('-created_at',)

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

    def agent_badge(self, obj):
        return _get_agent_badge(obj)
    agent_badge.short_description = "Agent"

