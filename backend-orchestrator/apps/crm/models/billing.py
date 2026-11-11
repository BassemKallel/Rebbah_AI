from django.db import models
from django.utils import timezone
from apps.crm.models.company import Company
from apps.crm.models.conversation import Message

class BillingWallet(models.Model):
    """Tracks the financial usage and limits for a company's LLM usage."""
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='wallet')
    
    # Financial Limit
    monthly_limit = models.DecimalField(max_digits=10, decimal_places=4, default=10.00, help_text="Limite de dépense mensuelle en $")
    current_month_usage = models.DecimalField(max_digits=10, decimal_places=4, default=0.00, help_text="Dépense accumulée ce mois-ci en $")
    
    last_reset_date = models.DateTimeField(default=timezone.now)
    last_updated = models.DateTimeField(auto_now=True)

    # Statistics
    total_messages_count = models.IntegerField(default=0, help_text="Nombre total de messages traités")
    average_cost_per_message = models.DecimalField(max_digits=10, decimal_places=6, default=0.000000, help_text="Coût moyen par message en $")

    def __str__(self):
        return f"Wallet - {self.company.name}: ${self.current_month_usage} / ${self.monthly_limit}"

    def is_limit_exceeded(self):
        return self.current_month_usage >= self.monthly_limit


class LLMUsageLog(models.Model):
    """Immutable log of every LLM API call for billing and audit purposes."""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='usage_logs')
    message = models.OneToOneField(Message, on_delete=models.SET_NULL, null=True, blank=True, related_name='usage_log')
    
    model_name = models.CharField(max_length=50) # Ex: "gemini-1.5-flash"
    
    # Tokens
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    
    # Financial details
    cost_input = models.DecimalField(max_digits=10, decimal_places=6, default=0.0)
    cost_output = models.DecimalField(max_digits=10, decimal_places=6, default=0.0)
    total_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0.0)
    
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Log {self.id} | {self.company.name} | ${self.total_cost}"
