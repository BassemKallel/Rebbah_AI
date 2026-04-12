from django.contrib import admin
from django.utils.html import format_html
import json
from ..models import BotConfiguration
from apps.gateway.response_templates import TEMPLATES


@admin.register(BotConfiguration)
class BotConfigurationAdmin(admin.ModelAdmin):
    list_display  = ('shop_id', 'shop_name', 'language', 'bot_status_badge', 'created_at')
    list_filter   = ('language', 'bot_enabled', 'created_at')
    search_fields = ('shop_id', 'shop_name')
    readonly_fields = ('bot_disabled_at',)

    fieldsets = (
        ('General', {'fields': ('shop_id', 'shop_name', 'language', 'ai_agent_name')}),
        ('Bot Handoff Global', {
            'fields': ('bot_enabled', 'bot_disabled_at'),
            'description': 'Desactiver le bot pour que le marchand gere toutes les conversations manuellement.',
        }),
    )

    def bot_status_badge(self, obj):
        if obj.bot_enabled:
            return format_html('<span style="background:#27ae60;color:#fff;padding:2px 10px;border-radius:4px;font-weight:bold;font-size:11px">Actif</span>')
        return format_html('<span style="background:#e74c3c;color:#fff;padding:2px 10px;border-radius:4px;font-weight:bold;font-size:11px">Desactive</span>')
    bot_status_badge.short_description = 'Statut Bot'

    def default_intents(self, obj):
        if not obj or not getattr(obj, 'language', None):
            return "-"
        lang = obj.language if obj.language in TEMPLATES else 'FR'
        data = TEMPLATES.get(lang, {})
        return format_html("<pre>{}</pre>", json.dumps(data, indent=2, ensure_ascii=False))
    default_intents.short_description = "Default Intents (Usine)"
