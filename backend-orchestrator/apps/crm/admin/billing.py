from django.contrib import admin
from ..models import BillingWallet, LLMUsageLog

@admin.register(BillingWallet)
class BillingWalletAdmin(admin.ModelAdmin):
    list_display = ('company', 'current_month_usage', 'monthly_limit', 'is_limit_exceeded', 'last_updated')
    list_filter = ('last_updated',)
    search_fields = ('company__name',)
    readonly_fields = ('current_month_usage', 'last_updated')

@admin.register(LLMUsageLog)
class LLMUsageLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'company', 'model_name', 'input_tokens', 'output_tokens', 'total_cost', 'created_at')
    list_filter = ('model_name', 'created_at', 'company')
    search_fields = ('company__name',)
    readonly_fields = ('company', 'message', 'model_name', 'input_tokens', 'output_tokens', 'cost_input', 'cost_output', 'total_cost', 'created_at')

    def has_add_permission(self, request):
        return False  # Logs should be immutable
    
    def has_change_permission(self, request, obj=None):
        return False  # Logs should be immutable
