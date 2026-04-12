from django.db import models
from django.utils import timezone
from .lead import Lead


class Conversation(models.Model):
    """Ongoing chat session with a lead."""
    lead      = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="conversations")
    lead_uuid = models.UUIDField(null=True, blank=True)
    sender_id = models.CharField(max_length=255, null=True, blank=True)
    shop_id   = models.CharField(max_length=255)

    state            = models.CharField(max_length=50, default="NEW_CONVERSATION")
    context_data     = models.JSONField(default=dict, blank=True)
    missing_entities = models.JSONField(default=list, blank=True)
    completed_at     = models.DateTimeField(blank=True, null=True)

    is_human_controlled = models.BooleanField(default=False)
    human_takeover_at   = models.DateTimeField(blank=True, null=True)
    human_agent         = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='controlled_conversations')

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Conv {self.id} with {self.lead.platform_id} (State: {self.state})"


class Message(models.Model):
    """Individual message in a conversation (USER, BOT, or human AGENT)."""
    SENDER_CHOICES = [('USER', 'User'), ('BOT', 'Bot')]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender       = models.CharField(max_length=10, choices=SENDER_CHOICES)
    text         = models.TextField()

    extracted_intent        = models.CharField(max_length=50, blank=True, null=True)
    intent_confidence_score = models.FloatField(blank=True, null=True)
    extracted_entities      = models.JSONField(default=dict, blank=True)
    is_error                = models.BooleanField(default=False)
    is_fallback             = models.BooleanField(default=False)
    is_human_agent          = models.BooleanField(default=False)

    conversation_state_before = models.CharField(max_length=50, blank=True, null=True)
    conversation_state_after  = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"[{self.sender}] {self.text[:30]}..."
