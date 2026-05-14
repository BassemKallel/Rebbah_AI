"""
apps/crm/admin/__init__.py

Imports all admin modules so Django registers them automatically.
"""
from .config import BotConfigurationAdmin
from .company import CompanyAdmin, UserProfileAdmin
from .lead import LeadAdmin
from .conversation import ConversationAdmin, MessageAdmin
from .analytics import ItemVectorAdmin, PipelineLogAdmin
from .billing import BillingWalletAdmin, LLMUsageLogAdmin

__all__ = [
    'BotConfigurationAdmin', 'CompanyAdmin', 'UserProfileAdmin',
    'LeadAdmin', 'ConversationAdmin', 'MessageAdmin',
    'ItemVectorAdmin', 'PipelineLogAdmin',
    'BillingWalletAdmin', 'LLMUsageLogAdmin',
]
