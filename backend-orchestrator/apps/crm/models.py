from django.db import models
from django.utils import timezone

class Lead(models.Model):
    """
    Represents a potential customer identified via WhatsApp/Messenger.
    """
    platform_id = models.CharField(max_length=255, unique=True, help_text="e.g., whatsapp:+21612345678")
    name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name or 'Unknown'} ({self.platform_id})"

class Conversation(models.Model):
    """
    Represents an ongoing chat session with a lead.
    """
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="conversations")
    shop_id = models.CharField(max_length=255, help_text="Which shop context is this happening in?")
    
    # Simple state machine for the POC (e.g., NEW, ASKING_SIZE, ASKING_COLOR, COMPLETED)
    state = models.CharField(max_length=50, default="NEW_CONVERSATION")
    
    # Store currently needed info (e.g., {"product": "t-shirt"}, remaining: ["size"])
    context_data = models.JSONField(default=dict, blank=True, help_text="JSON storing extracted entities across messages")
    missing_entities = models.JSONField(default=list, blank=True, help_text="List of entities still needed to complete the intent")
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Conv {self.id} with {self.lead.platform_id} (State: {self.state})"

class Message(models.Model):
    """
    Stores individual messages in a conversation (both User and Bot).
    """
    SENDER_CHOICES = [
        ('USER', 'User'),
        ('BOT', 'Bot'),
    ]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    text = models.TextField()
    
    # NLU debug info
    extracted_intent = models.CharField(max_length=50, blank=True, null=True)
    extracted_entities = models.JSONField(default=dict, blank=True)
    is_error = models.BooleanField(default=False, help_text="True if NLU failed or fallback was triggered")
    
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"[{self.sender}] {self.text[:30]}..."