from django.contrib import admin
from django.utils.html import format_html
from ..models import Company, UserProfile


class UserProfileInline(admin.TabularInline):
    model = UserProfile
    extra = 1
    fields = ('user', 'role', 'created_at')
    readonly_fields = ('created_at',)
    autocomplete_fields = ['user']


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display   = ('name', 'shop_id', 'meta_page_id', 'is_active', 'created_at')
    list_filter    = ('is_active', 'created_at')
    search_fields  = ('name', 'shop_id', 'meta_page_id')
    list_editable  = ('is_active',)
    inlines        = [UserProfileInline]
    actions        = ['sync_catalog_action']

    fieldsets = (
        ('Identité', {'fields': ('name', 'shop_id', 'is_active')}),
        ('Auth & Accès Dashboard', {'fields': ('dashboard_token',), 'description': 'Token statique utilisé pour les webhooks TikTak PRO.'}),
        ('Meta Integration', {'fields': ('meta_page_id', 'meta_page_access_token', 'instagram_page_id'), 'description': 'Facebook Page ID, Token Messenger.'}),
        ('Bot Configuration', {'fields': ('bot_config',), 'description': 'Lier à une configuration de bot pour la personnalisation.'}),
    )

    @admin.action(description="Synchroniser le catalogue de la boutique (API TikTak)")
    def sync_catalog_action(self, request, queryset):
        from apps.gateway.services import tiktak_service
        from django.core.cache import cache
        from django.contrib import messages

        success_count = 0
        error_count = 0

        for company in queryset:
            try:
                # Invalider le cache existant
                cache_key = f"tiktak_products:{company.shop_id}"
                cache.delete(cache_key)

                # Forcer le téléchargement
                tiktak_service.get_products(company.shop_id)
                success_count += 1
            except Exception as e:
                error_count += 1
                self.message_user(
                    request,
                    f"Erreur pour la boutique {company.name}: {str(e)}",
                    level=messages.ERROR
                )

        if success_count > 0:
            self.message_user(
                request,
                f"Catalogue synchronisé avec succès pour {success_count} boutique(s).",
                level=messages.SUCCESS
            )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display        = ('user', 'get_company', 'role', 'created_at')
    list_filter         = ('role', 'company')
    search_fields       = ('user__username', 'user__email', 'company__name', 'company__shop_id')
    autocomplete_fields = ['user', 'company']
    readonly_fields     = ('created_at',)

    fieldsets = (
        ('Utilisateur', {'fields': ('user', 'role')}),
        ('Boutique', {'fields': ('company',)}),
        ('Système', {'fields': ('created_at',), 'classes': ('collapse',)}),
    )

    def get_company(self, obj):
        if not obj.company:
            return format_html('<span style="color:#888;"><i>Aucune (Global)</i></span>')
        return format_html('<span style="font-weight:bold">{}</span> <small style="color:#888">({})</small>', obj.company.name, obj.company.shop_id)
    get_company.short_description = 'Boutique'
    get_company.admin_order_field = 'company__name'
