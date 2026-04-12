"""
apps/crm/admin/__init__.py

Imports all admin modules so Django registers them automatically.
"""
from .config import BotConfigurationAdmin
from .company import CompanyAdmin, UserProfileAdmin
from .lead import LeadAdmin
from .conversation import ConversationAdmin, MessageAdmin
from .template import ResponseTemplateAdmin
from .analytics import NLUFallbackLogAdmin, ProductVectorAdmin

__all__ = [
    'BotConfigurationAdmin', 'CompanyAdmin', 'UserProfileAdmin',
    'LeadAdmin', 'ConversationAdmin', 'MessageAdmin',
    'ResponseTemplateAdmin', 'NLUFallbackLogAdmin', 'ProductVectorAdmin',
]
