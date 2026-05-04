from django.contrib import admin
from django.utils.html import format_html
import json
from ..models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    can_delete = False
    readonly_fields = ('sender', 'text', 'extracted_intent', 'confidence_badge', 'state_transition', 'pretty_entities', 'is_error', 'is_fallback', 'agent_badge', 'created_at')
    fields = ('sender', 'text', 'extracted_intent', 'confidence_badge', 'state_transition', 'pretty_entities', 'is_error', 'is_fallback', 'agent_badge', 'created_at')

    def confidence_badge(self, obj):
        if obj.intent_confidence_score is None:
            return "-"
        score = obj.intent_confidence_score
        color = "#27ae60" if score >= 0.8 else ("#e67e22" if score >= 0.5 else "#e74c3c")
        return format_html('<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-weight:bold">{}</span>', color, f"{score:.0%}")
    confidence_badge.short_description = "Confiance"

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
        if obj.is_human_agent:
            return format_html('<span style="background:#f39c12;color:#fff;padding:2px 8px;border-radius:4px;font-weight:bold;font-size:10px">Agent</span>')
        return ""
    agent_badge.short_description = "Agent"


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
    list_display  = ('sender', 'agent_badge', 'get_lead', 'text_preview', 'extracted_intent', 'confidence_badge', 'is_error', 'is_fallback', 'created_at')
    list_filter   = ('sender', 'is_error', 'is_fallback', 'is_human_agent', 'extracted_intent', 'created_at')
    search_fields = ('text', 'conversation__lead__platform_id', 'extracted_intent')
    readonly_fields = ('pretty_entities', 'confidence_badge')
    date_hierarchy = 'created_at'
    ordering      = ('-created_at',)

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
        color = "#27ae60" if score >= 0.8 else ("#e67e22" if score >= 0.5 else "#e74c3c")
        return format_html('<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-weight:bold">{}</span>', color, f"{score:.0%}")
    confidence_badge.short_description = "Confiance Intention"

    def pretty_entities(self, obj):
        if not obj.extracted_entities:
            return "-"
        return format_html("<pre>{}</pre>", json.dumps(obj.extracted_entities, indent=2, ensure_ascii=False))
    pretty_entities.short_description = "Extraction Data"

    def agent_badge(self, obj):
        if obj.is_human_agent:
            return format_html('<span style="background:#f39c12;color:#fff;padding:2px 8px;border-radius:4px;font-weight:bold;font-size:10px">Agent Humain</span>')
        return ""
    agent_badge.short_description = "Type"
