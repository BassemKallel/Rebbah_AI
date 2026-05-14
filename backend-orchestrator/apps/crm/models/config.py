from django.db import models
from django.utils import timezone


class BotConfiguration(models.Model):
    """Stores the AI Agent configuration per shop."""
    LANGUAGE_CHOICES = [('AUTO', 'Auto-detect'), ('FR', 'French'), ('AR', 'Arabizi'), ('EN', 'English')]

    shop_id        = models.CharField(max_length=255, unique=True)
    shop_name      = models.CharField(max_length=255, blank=True, null=True)
    ai_agent_name  = models.CharField(max_length=255, default="Tiktak AI")
    custom_intents = models.JSONField(default=dict, blank=True)

    # ── Configuration du Contexte LLM (Fragmenté) ──────────────────────────
    business_domain = models.CharField(max_length=255, default="Boutique en ligne", help_text="Ex: Boutique de jeux de société, Clinique médicale")
    target_audience = models.CharField(max_length=255, default="Grand public", help_text="Ex: Jeunes tunisiens, Professionnels")
    communication_tone = models.CharField(max_length=255, default="Chaleureux et professionnel", help_text="Ex: Fun et décontracté, Très formel")
    language_rules = models.TextField(default="Réponds en ARABE si le client écrit en arabe ou arabizi. Réponds en FRANÇAIS si le client écrit en français.", help_text="Règles conditionnelles pour le LLM")
    delivery_policy = models.TextField(default="Livraison sur toute la Tunisie.\nDélai : 2-3 jours ouvrables.\nFrais de livraison : 7 TND.\nPaiement à la livraison.", help_text="Politique de livraison et paiement")
    required_checkout_info = models.TextField(default="1. Le produit souhaité\n2. La quantité\n3. L'adresse de livraison\n4. Le numéro de téléphone (8 chiffres)", help_text="Informations obligatoires pour finaliser")

    bot_enabled     = models.BooleanField(default=True)
    bot_disabled_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Config for {self.shop_id}"

    def get_compiled_llm_context(self):
        """Compile les champs fragmentés en un seul prompt structuré."""
        return f"""=== IDENTITÉ ET DOMAINE ===
Tu t'appelles "{self.ai_agent_name}" et tu es l'assistant de "{self.shop_name}". Activité : {self.business_domain}.
Cible principale : {self.target_audience}.

=== RÈGLES DE COMMUNICATION ===
Ton à adopter : {self.communication_tone}.
Règles de langue : {self.language_rules}

=== CONDITIONS ET LIVRAISON ===
{self.delivery_policy}

=== FINALISATION DE L'ACTION ===
Pour valider l'action du client, tu DOIS collecter ces informations :
{self.required_checkout_info}

---
INSTRUCTION SYSTÈME STRICTE (NE PAS IGNORER) :
Tu DOIS structurer ta réponse en JSON et inclure toutes les entités extraites ci-dessus. Utilise des clés en anglais simples (ex: 'name', 'phone', 'items' pour un panier de produits, 'address', etc.). Si tu as collecté toutes les infos requises, passe la clé 'order_ready' à true."""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps

@receiver(post_save, sender=BotConfiguration)
def link_bot_config_to_company(sender, instance, created, **kwargs):
    """
    Auto-links the BotConfiguration to the Company model when created via Admin
    if they share the same shop_id.
    """
    Company = apps.get_model('crm', 'Company')
    company = Company.objects.filter(shop_id=instance.shop_id).first()
    if company and company.bot_config != instance:
        company.bot_config = instance
        company.save(update_fields=['bot_config'])
