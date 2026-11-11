import requests as _requests
from django.conf import settings as _settings
from django.contrib import admin, messages as _messages
from django.utils.html import format_html
import json
from ..models import ItemVector, PipelineLog

def _vision_base():
    return _settings.VISION_SERVICE_URL.rstrip('/')

@admin.register(ItemVector)
class ItemVectorAdmin(admin.ModelAdmin):
    list_display    = ('id', 'shop_id', 'item_id', 'metadata_display', 'image_preview', 'created_at')
    list_filter     = ('shop_id',)
    search_fields   = ('item_id', 'shop_id')
    list_per_page   = 50
    ordering        = ('shop_id', '-created_at')
    readonly_fields = ('id', 'item_id', 'shop_id', 'created_at', 'image_preview_large', 'metadata_pretty', 'embedding_preview')
    actions         = ['clear_vectors_by_shop', 'clear_all_vectors']

    def has_module_permission(self, request): return request.user.is_active and request.user.is_superuser
    def has_view_permission(self, request, obj=None): return request.user.is_active and request.user.is_superuser
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

    @admin.action(description="Vider les vecteurs des boutiques selectionnees")
    def clear_vectors_by_shop(self, request, queryset):
        for shop_id in queryset.values_list('shop_id', flat=True).distinct():
            try:
                resp = _requests.delete(f"{_vision_base()}/vectors/", params={"shop_id": shop_id}, timeout=10)
                resp.raise_for_status()
                self.message_user(request, f"Boutique {shop_id} : {resp.json().get('deleted', '?')} vecteurs supprimes.", level=_messages.SUCCESS)
            except Exception as e:
                self.message_user(request, f"Erreur pour {shop_id} : {e}", level=_messages.ERROR)

    @admin.action(description="VIDER TOUTE LA BASE VECTORIELLE (toutes boutiques)")
    def clear_all_vectors(self, request, queryset):
        try:
            resp = _requests.delete(f"{_vision_base()}/vectors/", timeout=10)
            resp.raise_for_status()
            self.message_user(request, f"Base vectorielle videe : {resp.json().get('deleted', '?')} vecteurs supprimes.", level=_messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Erreur : {e}", level=_messages.ERROR)

    def image_preview(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="height:60px;width:60px;object-fit:cover;border-radius:6px;border:1px solid #ddd;" onerror="this.style.display=\'none\'"/>', obj.image_url)
        return '—'
    image_preview.short_description = 'Image'

    def image_preview_large(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="max-height:250px;max-width:250px;border-radius:8px;border:1px solid #ddd;box-shadow:0 4px 6px rgba(0,0,0,0.1);"/><br><small style="color:#888;word-break:break-all;">{}</small>', obj.image_url, obj.image_url)
        return '—'
    image_preview_large.short_description = 'Image'

    def metadata_display(self, obj):
        if obj.metadata:
            return format_html('<pre style="margin:0; font-size:11px; font-family:monospace; color:#2c3e50; max-width: 300px; white-space: pre-wrap;">{}</pre>', json.dumps(obj.metadata, indent=2, ensure_ascii=False))
        return '—'
    metadata_display.short_description = 'Metadata'

    def metadata_pretty(self, obj):
        if obj.metadata:
            return format_html('<pre style="background:#1e1e1e;color:#d4d4d4;padding:12px;border-radius:6px;border:1px solid #333;font-family:monospace;font-size:12px;">{}</pre>', json.dumps(obj.metadata, indent=2, ensure_ascii=False))
        return '—'
    metadata_pretty.short_description = 'Metadata Complet'

    def embedding_preview(self, obj):
        if obj.embedding:
            # On affiche un aperçu textuel du vecteur (les premiers et derniers caractères)
            emb_str = str(obj.embedding)
            return format_html('<div style="word-wrap: break-word; font-family: monospace; font-size: 11px; color: #569cd6; background: #1e1e1e; padding: 12px; border-radius: 6px; border: 1px solid #333; max-height: 100px; overflow-y: auto;">{}</div><br><i style="color:#888;">(Vecteur CLIP 512 dimensions de pgvector)</i>', emb_str)
        return '—'
    embedding_preview.short_description = 'Embedding (pgvector)'

    fieldsets = (
        ('Identification', {'fields': ('id', 'shop_id', 'item_id', 'created_at')}),
        ('Informations', {'fields': ('metadata_pretty', 'embedding_preview')}),
        ('Image', {'fields': ('image_preview_large',)}),
    )


@admin.register(PipelineLog)
class PipelineLogAdmin(admin.ModelAdmin):
    list_display  = (
        'created_at', 'mode_badge', 'shop_id', 'sender_id_short',
        'user_text_preview', 'detected_intent', 'state_transition',
        'status_badge', 'error_type', 'duration_badge', 'order_created', 'log_count',
    )
    list_filter   = ('mode', 'has_error', 'error_type', 'order_created', 'created_at')
    search_fields = ('shop_id', 'sender_id', 'user_text', 'bot_text', 'detected_intent', 'log_messages')
    readonly_fields = (
        'shop_id', 'sender_id', 'mode', 'user_text', 'bot_text',
        'detected_intent', 'has_image', 'state_before', 'state_after',
        'order_created', 'has_error', 'error_type', 'error_detail',
        'duration_ms', 'created_at', 'pretty_logs',
    )
    date_hierarchy = 'created_at'
    ordering       = ('-created_at',)
    list_per_page  = 50

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False

    fieldsets = (
        ('Identification', {
            'fields': ('created_at', 'shop_id', 'sender_id', 'mode'),
        }),
        ('Message', {
            'fields': ('user_text', 'bot_text', 'detected_intent', 'has_image'),
        }),
        ('État Machine', {
            'fields': ('state_before', 'state_after', 'order_created'),
        }),
        ('Erreur', {
            'fields': ('has_error', 'error_type', 'error_detail'),
            'classes': ('collapse',),
        }),
        ('Performance', {
            'fields': ('duration_ms',),
        }),
        ('Trace Complète des Logs', {
            'fields': ('pretty_logs',),
        }),
    )

    def mode_badge(self, obj):
        color = '#2980b9' if obj.mode == 'llm' else '#8e44ad'
        label = obj.get_mode_display()
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold">{}</span>',
            color, label,
        )
    mode_badge.short_description = 'Mode'

    def status_badge(self, obj):
        if obj.has_error:
            return format_html('<span style="background:#e74c3c;color:#fff;padding:2px 8px;border-radius:4px;font-weight:bold">❌ Erreur</span>')
        return format_html('<span style="background:#27ae60;color:#fff;padding:2px 8px;border-radius:4px;font-weight:bold">✅ OK</span>')
    status_badge.short_description = 'Statut'

    def user_text_preview(self, obj):
        t = obj.user_text or ''
        return (t[:50] + '…') if len(t) > 50 else t
    user_text_preview.short_description = 'Message client'

    def sender_id_short(self, obj):
        s = obj.sender_id or ''
        return s[-12:] if len(s) > 12 else s
    sender_id_short.short_description = 'Sender'

    def state_transition(self, obj):
        if obj.state_before or obj.state_after:
            return format_html(
                '<small style="color:#666">{} → {}</small>',
                obj.state_before or '—', obj.state_after or '—',
            )
        return '—'
    state_transition.short_description = 'État'

    def duration_badge(self, obj):
        if obj.duration_ms is None:
            return '—'
        color = '#27ae60' if obj.duration_ms < 1000 else ('#e67e22' if obj.duration_ms < 3000 else '#e74c3c')
        return format_html(
            '<span style="color:{};font-weight:bold">{}ms</span>',
            color, obj.duration_ms,
        )
    duration_badge.short_description = 'Durée'

    def log_count(self, obj):
        if not obj.log_messages:
            return '—'
        # Format the actual logs nicely with a max-height to avoid breaking the table
        return format_html(
            '<div style="max-height:120px; overflow-y:auto; max-width:400px; white-space:pre-wrap; font-family:monospace; font-size:11px; background:#1e1e1e; color:#d4d4d4; padding:6px; border:1px solid #333; border-radius:4px;">{}</div>',
            obj.log_messages
        )
    log_count.short_description = 'Logs'

    def pretty_logs(self, obj):
        if not obj.log_messages:
            return format_html('<em style="color:#888">Aucun log capturé</em>')
        lines = obj.log_messages.split('\n')
        colored = []
        for line in lines:
            if '[ERROR]' in line:
                colored.append(f'<span style="color:#e74c3c;font-weight:bold">{line}</span>')
            elif '[WARNING]' in line:
                colored.append(f'<span style="color:#e67e22">{line}</span>')
            elif '[INFO]' in line:
                colored.append(f'<span style="color:#27ae60">{line}</span>')
            else:
                colored.append(line)
        html_content = '<br>'.join(colored)
        return format_html(
            '<div style="background:var(--darkened-bg);padding:12px;border-radius:6px;'
            'font-family:monospace;font-size:12px;line-height:1.6;max-height:500px;overflow-y:auto">{}</div>',
            format_html(html_content),
        )
    pretty_logs.short_description = 'Trace Logs'
