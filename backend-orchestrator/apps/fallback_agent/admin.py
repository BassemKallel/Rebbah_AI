from django.contrib import admin
from apps.fallback_agent.models import RetrainingBuffer

@admin.register(RetrainingBuffer)
class RetrainingBufferAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'confidence_score', 'user_query_snippet', 'gemini_fallback_response_snippet')
    readonly_fields = ('created_at',)

    def user_query_snippet(self, obj):
        return obj.user_query[:50] + "..." if len(obj.user_query) > 50 else obj.user_query
    user_query_snippet.short_description = 'User Query'

    def gemini_fallback_response_snippet(self, obj):
        return obj.gemini_fallback_response[:50] + "..." if len(obj.gemini_fallback_response) > 50 else obj.gemini_fallback_response
    gemini_fallback_response_snippet.short_description = 'Fallback Response'
