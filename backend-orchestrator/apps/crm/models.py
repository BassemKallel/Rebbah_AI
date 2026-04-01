from django.db import models
from django.utils import timezone
import uuid as uuid_lib
import time

class Lead(models.Model):
    """
    Represents a potential customer identified via Messenger.
    Stores both lead info AND pending pre-order data waiting for agent confirmation.
    """
    uuid        = models.UUIDField(default=uuid_lib.uuid4, unique=True, editable=False, help_text="Stable public identifier for this lead")
    platform_id = models.CharField(max_length=255, db_index=True, help_text="e.g., PSID Meta ou whatsapp:+21612345678")
    name        = models.CharField(max_length=255, blank=True, null=True)
    
    # ===== PRÉ-COMMANDE (En attente de confirmation agent) =====
    shop_id = models.CharField(max_length=255, blank=True, null=True, help_text="Associated shop")
    
    # Product details
    product_id = models.CharField(max_length=255, blank=True, null=True, help_text="UUID du produit Mock API")
    variation_id = models.CharField(max_length=255, blank=True, null=True, help_text="UUID de la variation (couleur)")
    color = models.CharField(max_length=100, blank=True, null=True)
    size = models.CharField(max_length=50, blank=True, null=True)
    quantity = models.IntegerField(default=1, help_text="Quantity in pre-order")
    
    # Delivery info
    address = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    
    # Pre-order tracking
    has_pending_order = models.BooleanField(default=False, help_text="True si pré-commande en attente")
    pending_order_reference = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        db_index=True,
        help_text="e.g., PRE-1708960234567"
    )
    pending_order_created_at = models.DateTimeField(blank=True, null=True)
    agent_confirmation_pending = models.BooleanField(default=False, help_text="Attente confirmation agent")
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name or 'Unknown'} ({self.platform_id})"
    
    def create_pending_order(self, shop_id, product_id, variation_id, color, size, address, phone_number, quantity=1):
        """Helper to create a pending order"""
        self.shop_id = shop_id
        self.product_id = product_id
        self.variation_id = variation_id
        self.color = color
        self.size = size
        self.quantity = quantity
        self.address = address
        self.phone_number = phone_number
        self.has_pending_order = True
        self.agent_confirmation_pending = True
        
        # Generate reference if not exists
        if not self.pending_order_reference:
            timestamp = str(int(time.time() * 1000))
            self.pending_order_reference = f"PRE-{timestamp}"
        
        self.pending_order_created_at = timezone.now()
        self.save()


class Conversation(models.Model):
    """
    Represents an ongoing chat session with a lead.
    """
    lead      = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="conversations")
    lead_uuid = models.UUIDField(null=True, blank=True, help_text="Denormalized lead UUID for direct querying")
    sender_id = models.CharField(max_length=255, null=True, blank=True, help_text="Denormalized platform_id of the sender")
    shop_id   = models.CharField(max_length=255, help_text="Which shop context is this happening in?")
    
    # Simple state machine for the POC (e.g., NEW, ASKING_SIZE, ASKING_COLOR, COMPLETED)
    state = models.CharField(max_length=50, default="NEW_CONVERSATION")
    
    # Store currently needed info (e.g., {"product": "t-shirt"}, remaining: ["size"])
    context_data = models.JSONField(default=dict, blank=True, help_text="JSON storing extracted entities across messages")
    missing_entities = models.JSONField(default=list, blank=True, help_text="List of entities still needed to complete the intent")
    
    # Grace period tracking
    completed_at = models.DateTimeField(blank=True, null=True, help_text="Timestamp when order was confirmed — used for AWAITING_CORRECTION grace period")

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
    intent_confidence_score = models.FloatField(
        blank=True, null=True,
        help_text="Confidence score of the detected intent (0.0 to 1.0)"
    )
    extracted_entities = models.JSONField(default=dict, blank=True)
    is_error = models.BooleanField(default=False, help_text="True if NLU failed or fallback was triggered")
    is_fallback = models.BooleanField(default=False, help_text="True si Gemini fallback a ete utilise")

    # Conversation state tracking
    conversation_state_before = models.CharField(
        max_length=50, blank=True, null=True,
        help_text="State of the conversation BEFORE processing this message"
    )
    conversation_state_after = models.CharField(
        max_length=50, blank=True, null=True,
        help_text="State of the conversation AFTER processing this message"
    )
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"[{self.sender}] {self.text[:30]}..."


class BotConfiguration(models.Model):
    """
    Stores the configuration for the AI Agent per shop/client.
    Contains dialect preference, custom greeting, and response delay.
    """
    LANGUAGE_CHOICES = [
        ('AUTO', 'Auto-detect'),
        ('FR', 'French'),
        ('AR', 'Arabizi'),
        ('EN', 'English'),
    ]

    shop_id = models.CharField(max_length=255, unique=True, help_text="The client/shop ID this configuration belongs to.")
    shop_name = models.CharField(max_length=255, blank=True, null=True, help_text="The display name of the shop.")
    
    language = models.CharField(
        max_length=4, 
        choices=LANGUAGE_CHOICES, 
        default='FR',
        help_text="The language the bot should respond in."
    )

    ai_agent_name = models.CharField(max_length=255, default="Tiktak AI", help_text="Le nom donné au Ai agent" )
    
    custom_intents = models.JSONField(
        default=dict, 
        blank=True, 
        help_text="Custom messages per intent (e.g. {\"ASK_PRICE\": \"Price is {{price}}\"}). Overrides defaults."
    )
    

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Config for Django {self.shop_id} ({self.language})"


class Company(models.Model):
    """
    Represents a client company / shop connected to the platform.
    Stores business identity + Meta platform integration details.
    BotConfiguration is for personalization; Company is for identity.
    """
    name = models.CharField(max_length=255, help_text="Nom de la boutique")
    shop_id = models.CharField(
        max_length=255, unique=True,
        help_text="UUID du shop sur la plateforme Tiktak"
    )

    # ── Meta Platform Integration ──────────────────────────────────────
    meta_page_id = models.CharField(
        max_length=100, blank=True, null=True, unique=True,
        help_text="Facebook Page ID (depuis Meta Developer → Messenger → Token d'accès)"
    )
    meta_page_access_token = models.TextField(
        blank=True, null=True,
        help_text="Page Access Token pour envoyer des réponses via Meta Send API"
    )
    instagram_page_id = models.CharField(
        max_length=100, blank=True, null=True, unique=True,
        help_text="Instagram Business Account ID (si différent du Page ID)"
    )

    # ── Tiktak API ─────────────────────────────────────────────────────
    tiktak_api_token = models.TextField(
        blank=True, null=True,
        help_text="Token d'authentification pour l'API Tiktak (Bearer token)"
    )

    # ── Link to BotConfiguration ───────────────────────────────────────
    bot_config = models.OneToOneField(
        BotConfiguration, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='company',
        help_text="Configuration du bot IA associée"
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Companies"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.shop_id})"


class ResponseTemplate(models.Model):
    """
    Stores bot response templates in DB instead of hardcoded Python dicts.
    Supports per-shop customization and multilingual responses.

    Lookup chain in template_service:
    1. Cache Redis
    2. DB: shop-specific (shop_id provided)
    3. DB: system default (shop_id=NULL, is_default=True)
    4. Fallback: response_templates.py (if DB down)
    """
    LANGUAGE_CHOICES = [('FR', 'Français'), ('AR', 'Arabe'), ('EN', 'Anglais')]
    TEMPLATE_TYPE_CHOICES = [
        ('response',        'Réponse intent'),
        ('missing_entity',  'Entité manquante'),
        ('out_of_stock',    'Rupture de stock'),
        ('order_confirmed', 'Commande confirmée'),
        ('disambiguation',  'Disambiguation'),
        ('misc',            'Divers'),
    ]

    shop_id       = models.CharField(max_length=255, blank=True, null=True,
                                     help_text="NULL = défaut système, sinon shop spécifique")
    language      = models.CharField(max_length=5, choices=LANGUAGE_CHOICES)
    template_type = models.CharField(max_length=30, choices=TEMPLATE_TYPE_CHOICES)
    intent        = models.CharField(max_length=100,
                                     help_text="ex: GREETING, color, with_ref, noise_default")
    text          = models.TextField(help_text="Texte avec {variable} placeholders")
    available_variables = models.JSONField(
        default=list, blank=True,
        help_text='Variables utilisables dans ce template, ex: ["product", "price"]'
    )
    is_default    = models.BooleanField(default=False,
                                        help_text="True = template système par défaut")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('shop_id', 'language', 'template_type', 'intent')]
        ordering = ['template_type', 'language', 'intent']
        verbose_name = "Response Template"
        verbose_name_plural = "Response Templates"

    def __str__(self):
        shop = self.shop_id or "DEFAULT"
        return f"[{self.language}] {self.template_type}/{self.intent} ({shop})"


class NLUFallbackLog(models.Model):
    """
    Logs every Gemini fallback for active learning.
    Used to retrain TunBERT with Gemini-corrected labels.
    """
    TRIGGER_CHOICES = [
        ('LOW_CONFIDENCE', 'TunBERT confiance basse'),
        ('SERVICE_DOWN',   'NLU service indisponible'),
        ('ALWAYS_VERIFY',  'Intent destructif verifie'),
    ]

    message = models.OneToOneField(
        'Message', on_delete=models.CASCADE, related_name='fallback_log',
        help_text="Message utilisateur qui a declenche le fallback"
    )

    # Texte original
    original_text = models.TextField(help_text="Message brut de l'utilisateur")

    # TunBERT (avant correction)
    tunbert_intent     = models.CharField(max_length=50, blank=True, null=True)
    tunbert_confidence = models.FloatField(blank=True, null=True)
    tunbert_entities   = models.JSONField(default=list, blank=True,
                                          help_text="raw_entities retournees par GLiNER")

    # Gemini (correction)
    gemini_intent     = models.CharField(max_length=50)
    gemini_confidence = models.FloatField(blank=True, null=True)
    gemini_entities   = models.JSONField(default=list, blank=True,
                                          help_text="Entites extraites par Gemini")

    # Metadata
    trigger_reason = models.CharField(max_length=20, choices=TRIGGER_CHOICES)
    intent_changed = models.BooleanField(
        default=False,
        help_text="True si Gemini a corrige l'intent de TunBERT"
    )

    # Pour le reentrainement
    reviewed       = models.BooleanField(default=False, help_text="Reviewed par un humain")
    review_label   = models.CharField(max_length=50, blank=True, null=True,
                                       help_text="Label final valide par l'humain")

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'NLU Fallback Log'
        verbose_name_plural = 'NLU Fallback Logs'

    def __str__(self):
        arrow = "->" if self.intent_changed else "="
        return f"[{self.trigger_reason}] {self.tunbert_intent} {arrow} {self.gemini_intent} | '{self.original_text[:40]}'"


class ProductVector(models.Model):
    """
    Read-only mirror of the products_vector table (managed by vision-service).
    Exists solely to expose embeddings metadata in the Django Admin panel.
    The embedding column (vector(512)) is excluded — not useful for display.
    """
    product_id   = models.CharField(max_length=255)
    variation_id = models.CharField(max_length=255)
    shop_id      = models.CharField(max_length=255)
    image_url    = models.TextField(blank=True, null=True)

    class Meta:
        managed     = False              # Django never creates/drops this table
        db_table    = 'products_vector'   # exact table name from vision-service
        verbose_name = 'Product Embedding'
        verbose_name_plural = 'Product Embeddings (Vision)'
        ordering    = ['shop_id', 'product_id']

    def __str__(self):
        return f"[{self.shop_id}] product={self.product_id} var={self.variation_id}"
