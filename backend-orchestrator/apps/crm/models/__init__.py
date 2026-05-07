"""
apps/crm/models/__init__.py

Central re-export — all existing imports continue to work without changes.
"""
from .lead import Lead
from .config import BotConfiguration
from .conversation import Conversation, Message
from .company import Company, UserProfile
from .template import ResponseTemplate
from .analytics import NLUFallbackLog, ProductVector, RetrainingLog, ManualDataset

__all__ = [
    'Lead', 'BotConfiguration', 'Conversation', 'Message',
    'Company', 'UserProfile', 'ResponseTemplate',
    'NLUFallbackLog', 'ProductVector', 'RetrainingLog', 'ManualDataset'
]
