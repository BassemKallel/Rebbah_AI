from django.contrib import admin
from django.utils.html import format_html
import json
from ..models import BotConfiguration


@admin.register(BotConfiguration)
class BotConfigurationAdmin(admin.ModelAdmin):
    list_display  = ('shop_id', 'shop_name', 'bot_status_badge', 'created_at')
    list_filter   = ('bot_enabled', 'created_at')
    search_fields = ('shop_id', 'shop_name')
    readonly_fields = ('bot_disabled_at',)

    fieldsets = (
        ('Identité de Base', {
            'fields': ('shop_id', 'shop_name', 'ai_agent_name')
        }),
        ('Comportement IA (Contexte LLM)', {
            'fields': (
                'business_domain',
                'target_audience',
                'communication_tone',
                'language_rules',
                'delivery_policy',
                'required_checkout_info'
            ),
            'description': "Ces paramètres génèrent automatiquement le prompt système qui contrôle le comportement de l'IA."
        }),
        ('Bot Handoff Global', {
            'fields': ('bot_enabled', 'bot_disabled_at'),
            'description': 'Désactiver le bot pour que le marchand gère toutes les conversations manuellement.',
        }),
    )

    def bot_status_badge(self, obj):
        if obj.bot_enabled:
            return format_html('<span style="background:#27ae60;color:#fff;padding:2px 10px;border-radius:4px;font-weight:bold;font-size:11px">Actif</span>')
        return format_html('<span style="background:#e74c3c;color:#fff;padding:2px 10px;border-radius:4px;font-weight:bold;font-size:11px">Desactive</span>')
    bot_status_badge.short_description = 'Statut Bot'

