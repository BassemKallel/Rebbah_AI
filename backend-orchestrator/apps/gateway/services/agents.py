import json
import logging
import os
import re
from typing import Dict, Any, List, Optional, Tuple
import requests
from pydantic import BaseModel, Field

from django.utils import timezone
from apps.crm.models import Lead, Conversation, Message
from apps.crm.models.analytics import ItemVector

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.adk.events import Event
from google.genai import Client
from google.genai import types

from .entity_normalizer import normalize_entities

logger = logging.getLogger(__name__)

# Silence Google ADK session service deprecation warning log
logging.getLogger("google_adk.google.adk.sessions.in_memory_session_service").setLevel(logging.ERROR)

class ExtractedEntity(BaseModel):
    key: str = Field(
        description="Le nom ou la clé de l'information obligatoire (ex: 'name', 'phone_number', 'address', 'shop_name', 'daily_volume')"
    )
    value: Any = Field(
        description="La valeur extraite de la conversation pour ce champ"
    )


# ── Dynamic Checkout Schema ──────────────────────────────────────────────────
class DynamicCheckoutSchema(BaseModel):
    response_text: str = Field(
        description="Message de réponse destiné au client"
    )
    checkout_summary: Optional[str] = Field(
        default=None,
        description="Le récapitulatif textuel formaté de toutes les informations collectées, rédigé STRICTEMENT dans la langue configurée par la boutique. Généré uniquement lorsque 'order_ready' est True, se terminant par une question de confirmation claire."
    )
    extracted_entities: List[ExtractedEntity] = Field(
        default_factory=list,
        description="Liste des informations obligatoires extraites de la conversation actuelle."
    )
    order_ready: bool = Field(
        default=False,
        description="Doit passer à True si et seulement si toutes les informations requises par la boutique ont été collectées avec succès."
    )
    order_confirmed: bool = Field(
        default=False,
        description="Doit passer à True si et seulement si le client a explicitement et clairement confirmé le récapitulatif de sa commande (sois très flexible et accepte toutes les variantes courantes : 'oui', 'ey', 'ok', 'okay', 'mrigl', 'c'est bon', 'd'accord', 'عديها'). Sinon False."
    )
    carousel_items: List[str] = Field(
        default_factory=list,
        description="Liste des identifiants (IDs) des produits ou services à recommander (facultatif, max 5)"
    )


# ── Dynamic Sales Schema ─────────────────────────────────────────────────────
class DynamicSalesSchema(BaseModel):
    response_text: str = Field(
        description="Message de réponse destiné au client, rédigé STRICTEMENT dans la langue configurée par la boutique."
    )
    carousel_items: List[str] = Field(
        default_factory=list,
        description="Liste des identifiants (IDs) des produits du catalogue recommandés ou correspondants à la demande du client (facultatif, max 5, ex: ['prod_100', 'prod_200'])"
    )


# ── LLM Routing Pydantic Schema ──────────────────────────────────────────────
class AgentRoutingDecision(BaseModel):
    target_agent: str = Field(
        description="L'agent cible choisi. Doit être strictement l'un de : 'FAQ', 'SALES', 'CHECKOUT', 'POST_SALES'"
    )
    reasoning: str = Field(
        description="Explication concise de la décision de routage"
    )


# ── Checkout Lock Schema ─────────────────────────────────────────────────────
class CheckoutLockDecision(BaseModel):
    should_release_lock: bool = Field(
        description=(
            "True si le client pose une question (prix, stock, livraison, etc.) ou s'il "
            "souhaite abandonner/annuler la commande en cours. False si le message "
            "continue le checkout, corrige une information, confirme ou donne des coordonnées."
        )
    )
    is_abandonment: bool = Field(
        description=(
            "True uniquement si le client exprime explicitement l'intention d'abandonner, "
            "d'annuler, de stopper ou de vider son panier. False s'il pose simplement une question "
            "sur le prix, la livraison, le stock, etc., ou s'il continue la commande."
        )
    )
    reasoning: str = Field(
        description="Explication concise de la decision en une phrase."
    )


def _get_shop_catalog_text(shop_id: str) -> str:
    """
    Retrieve and format a lightweight catalog index for the shop from ItemVector (no descriptions).
    """
    try:
        items = ItemVector.objects.filter(shop_id=shop_id)
        if not items.exists():
            return "Aucun produit dans le catalogue."
        
        lines = []
        for item in items:
            meta = item.metadata or {}
            name = meta.get("name") or "Produit sans nom"
            price = meta.get("price") or meta.get("base_price") or "sur demande"
            in_stock = "En stock" if meta.get("in_stock", True) else "En rupture"
            lines.append(f"- ID: {item.item_id} | {name} | Prix: {price} TND | {in_stock}")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"[CATALOG INJECTION] Error fetching catalog: {e}")
        return "Erreur lors du chargement du catalogue."


def determine_target_agent_with_llm(
    user_message: str,
    history: List[Dict[str, Any]],
    current_agent: str,
    api_key: str,
    shop_name: str,
    business_domain: str,
) -> str:
    """
    Use Gemini to dynamically classify the user message and history into one of the 4 agents:
    - FAQ: General questions (hours, location, contact, company info, how to buy general policies).
    - SALES: Inquiries about product availability, prices, specifics, recommendations, catalogue browsing.
    - CHECKOUT: User wants to order, purchase, confirm, checkout, or is providing billing/shipping information.
    - POST_SALES: Package tracking, order status, return, exchange, refund, support.
    """
    try:
        client = Client(api_key=api_key)
        
        # Format recent history for classification context
        history_lines = []
        for msg in history[-5:]:
            role = "Client" if msg.get("role") == "user" else "Assistant"
            history_lines.append(f"{role}: {msg.get('text', '')}")
        history_context = "\n".join(history_lines)

        system_instruction = f"""Tu es l'aiguilleur intelligent (router) pour la boutique "{shop_name}" (Domaine: {business_domain}).
Ton rôle est de catégoriser le dernier message du client et l'historique dans l'un des 4 agents spécialisés :

1. FAQ :
   - Rôle : Répond aux questions générales sur la boutique (adresse, horaires, contact, modes de livraison, modes de paiement, tarifs de livraison).
   - Exemples de phrases (Derja / Français) : "win jinekom", "ba3tha mnin", "fama livraison?", "wa9tech t7ellou", "site mte3kom", "kifech nechri".

2. SALES :
   - Rôle : Aide le client à trouver, choisir, comparer et découvrir les produits de la boutique (recherche de produits, questions de prix, disponibilité, recommandations de jeux/articles).
   - Exemples de phrases (Derja / Français) : "chnw aandkom lo3ab", "fama jeu X", "b9adech l'article hetha", "a3tini catalogue", "3andkom al3ab", "boutique", "shop", "jeux dispo".

3. CHECKOUT :
   - Rôle : Gère le processus d'achat, de commande et la saisie des informations de livraison (nom, adresse, téléphone, validation de commande).
   - Exemples de phrases (Derja / Français) : "nheb nechri", "nheb ncommondi", "atini lo3bet X", "a3tini ka3ba", "اعطيني لعبة", "نحب كعبة", "commander", "checkout", "panier", "mon numéro est 98...", "j'habite à Tunis", "oui c'est parfait" (validation de commande).

4. POST_SALES :
   - Rôle : Service Après-Vente (SAV), suivi de colis, statut d'une commande déjà passée, retours, échanges, réclamations.
   - Exemples de phrases (Derja / Français) : "mon colis", "suivi commande", "ou est ma commande", "rajah", "reclamation", "echange", "remboursement".

RÈGLES CRITIQUES DE ROUTAGE :
- Le dialecte tunisien (Derja) est couramment utilisé. Analyse attentivement les mots en arabizi (ex: aandkom, nechri, lo3ab, win, ba3tha) et en arabe (عندكم، نحب، ألعاب، وين).
- Si le client dit simplement "bonjour", "aslema", "salut" ou s'il s'agit d'une salutation d'ouverture, dirige-le vers FAQ ou garde l'agent actuel si une transaction est déjà engagée.
- Si le dernier message du client contient des informations de contact ou de commande (comme un nom propre, un numéro de téléphone à 8 chiffres, une adresse, un nom de boutique, ou un volume de commandes), ou s'il s'agit d'une réponse à une collecte d'informations, dirige-le STRICTEMENT vers CHECKOUT.
- Si le dernier message du client exprime directement l'intention d'obtenir, commander ou acheter un produit spécifique (ex: "atini lo3bet X", "a3tini ka3ba", "اعطيني لعبة..."), même sans mentionner explicitement de quantité, dirige-le STRICTEMENT vers CHECKOUT.
- Si l'AGENT ACTUEL est CHECKOUT et que le message semble etre une reponse a une question en cours de collecte (nom de produit, taille, couleur, quantite, adresse, telephone, confirmation, correction ou toute autre information de livraison), maintiens STRICTEMENT l'agent CHECKOUT. Un mot isole ou une phrase courte qui ne contient PAS de signal explicite d'abandon ne doit JAMAIS declencher un changement d'agent depuis CHECKOUT.
"""

        prompt = f"""HISTORIQUE DE CONVERSATION :
{history_context}

DERNIER MESSAGE DU CLIENT :
Client: {user_message}

AGENT ACTUEL :
{current_agent}

Détermine l'agent cible."""

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=AgentRoutingDecision,
                temperature=0.0,
            ),
        )

        decision_data = json.loads(response.text)
        target = decision_data.get("target_agent", "FAQ").upper().strip()
        reasoning = decision_data.get("reasoning", "")
        logger.info(f"[LLM ROUTER] Decided agent={target} | Reason: {reasoning}")
        
        if target in ("FAQ", "SALES", "CHECKOUT", "POST_SALES"):
            return target
        return "FAQ"
    except Exception as e:
        logger.error(f"[LLM ROUTER ERROR] Failed to classify route: {e}")
        return current_agent


# ── Common System Instructions ───────────────────────────────────────────────
COMMON_LINGUISTIC_INSTRUCTION = """
RÈGLES DE LANGUE ET DE TON (CRITIQUE DE SÉCURITÉ) :
1. Adapte-toi TOUJOURS à la langue du client :
   - Si le client utilise l'arabe ou le dialecte tunisien (Derja en caractères arabes ou arabizi/latin comme 'aslema', 'nheb', 'b9adech', 'fama'), réponds EXCLUSIVEMENT en Derja tunisienne chaleureuse, naturelle, polie et concise.
   - Si le client utilise le français, réponds en français.
   - Ne mélange JAMAIS les langues dans une même phrase (pas de mélange Derja/Français).
2. Ton chaleureux, amical, concis (maximum 2 à 3 phrases).
3. Ne rien inventer qui ne figure pas dans le contexte ou le catalogue fourni.
"""

# ── Server-side Entity Extraction Safety Net ──────────────────────────────────
_KNOWN_SIZES_MULTI = ('3XL', '2XL', 'XXL', 'XL', 'XS')
_KNOWN_SIZES_SINGLE = ('L', 'M', 'S')

_SIZE_PATTERN_MULTI = re.compile(
    r'(?:^|[\s,.\-"])(?P<size>' + '|'.join(re.escape(s) for s in _KNOWN_SIZES_MULTI) + r')(?=[\s,.\-"]|$)',
    re.IGNORECASE,
)

_SIZE_PATTERN_SINGLE = re.compile(
    r'(?:(?:taille|size|kobr|nheb)\s+(?P<size_ci>[lmsLMS])(?=[\s,.\-"]|$))|(?:^|[\s,.\-"])(?P<size_cs>[LMS])(?=[\s,.\-"]|$)'
)

_PHONE_PATTERN = re.compile(r'(?<!\d)([2457-9]\d{7})(?!\d)')

def _extract_entities_server_side(text: str, existing_entities: dict, collected: dict) -> dict:
    """
    Server-side safety net that runs AFTER Gemini to catch entities it missed (sizes, phone numbers in arabizi).
    """
    safety = {}
    if not existing_entities.get('size') and not collected.get('size'):
        m_multi = _SIZE_PATTERN_MULTI.search(text)
        if m_multi:
            safety['size'] = m_multi.group('size').upper()
            logger.info(f"[LLM SAFETY] Server extracted size='{safety['size']}' from: '{text}'")
        else:
            m_single = _SIZE_PATTERN_SINGLE.search(text)
            if m_single:
                size_val = m_single.group('size_ci') or m_single.group('size_cs')
                if size_val:
                    safety['size'] = size_val.upper()
                    logger.info(f"[LLM SAFETY] Server extracted size='{safety['size']}' from: '{text}'")

    if not existing_entities.get('phone_number') and not collected.get('phone_number'):
        m = _PHONE_PATTERN.search(re.sub(r'[\s.\-]', '', text))
        if m:
            safety['phone_number'] = m.group(1)
            logger.info(f"[LLM SAFETY] Server extracted phone='{safety['phone_number']}' from: '{text}'")

    return safety


def _format_entity_value_for_summary(value: Any) -> str:
    if isinstance(value, list):
        item_lines = []
        for item in value:
            if isinstance(item, dict):
                name = item.get("product_name") or item.get("name") or item.get("product") or "item"
                quantity = item.get("quantity") or item.get("qty") or 1
                item_lines.append(f"{quantity} x {name}")
            else:
                item_lines.append(str(item))
        return ", ".join(item_lines)
    if isinstance(value, dict):
        return ", ".join(f"{key}: {val}" for key, val in value.items() if val not in (None, "", [], {}))
    return str(value)


def _build_checkout_summary_text(merged: Dict[str, Any], response_text: str, is_standard_arabic: bool = False) -> str:
    public_entities = {
        key: value
        for key, value in merged.items()
        if not str(key).startswith("_") and value not in (None, "", [], {})
    }
    summary = "\n".join(
        f"- {key}: {_format_entity_value_for_summary(value)}"
        for key, value in public_entities.items()
    )
    is_arabic = any('\u0600' <= c <= '\u06FF' for c in str(response_text))
    if is_arabic:
        if is_standard_arabic:
            return f"إليك ملخص المعلومات التي لدي:\n{summary}\n\nهل تؤكد الطلب؟ (نعم/لا)"
        return f"هاو ملخص المعلومات اللي عندي:\n{summary}\n\nنأكد الطلبية هكا؟ (ey/la)"
    return f"Voici le récapitulatif des informations collectées :\n{summary}\n\nEst-ce que je confirme avec ces informations ? (Oui/Non)"


def _should_replace_with_summary(response_text: str, order_ready: bool, order_confirmed: bool) -> bool:
    if not order_ready or order_confirmed:
        return False
    text = (response_text or "").lower()
    summary_markers = ("récap", "recap", "ملخص", "résumé", "resume", "confirme", "تأكد", "n'aked", "naكد")
    return not any(marker in text for marker in summary_markers)


def _process_checkout_output(output_data, user_message, collected, result, company=None):
    checkout_summary = None
    if isinstance(output_data, dict):
        result["response_text"] = output_data.get("response_text", "")
        checkout_summary = output_data.get("checkout_summary")
        
        # Convert list of objects to dict
        raw_entities = output_data.get("extracted_entities", [])
        entities_dict = {}
        if isinstance(raw_entities, list):
            for item in raw_entities:
                if isinstance(item, dict) and "key" in item:
                    entities_dict[item["key"]] = item.get("value", "")
        elif isinstance(raw_entities, dict):
            entities_dict = raw_entities
        result["extracted_entities"] = normalize_entities(entities_dict)
        
        result["order_ready"] = bool(output_data.get("order_ready", False))
        result["order_confirmed"] = bool(output_data.get("order_confirmed", False))
        result["carousel_items"] = output_data.get("carousel_items", [])
    else:
        result["response_text"] = getattr(output_data, "response_text", "")
        checkout_summary = getattr(output_data, "checkout_summary", None)
        
        # Convert list of objects to dict
        raw_entities = getattr(output_data, "extracted_entities", [])
        entities_dict = {}
        if isinstance(raw_entities, list):
            for item in raw_entities:
                if hasattr(item, "key"):
                    entities_dict[item.key] = getattr(item, "value", "")
                elif isinstance(item, dict) and "key" in item:
                    entities_dict[item["key"]] = item.get("value", "")
        elif isinstance(raw_entities, dict):
            entities_dict = raw_entities
        result["extracted_entities"] = normalize_entities(entities_dict)
        
        result["order_ready"] = bool(getattr(output_data, "order_ready", False))
        result["order_confirmed"] = bool(getattr(output_data, "order_confirmed", False))
        result["carousel_items"] = getattr(output_data, "carousel_items", [])

    # Server-side safety net
    safety_entities = _extract_entities_server_side(
        user_message, result["extracted_entities"], collected
    )
    result["extracted_entities"].update(safety_entities)
    result["extracted_entities"] = normalize_entities(result["extracted_entities"])

    # Safety check: force order_ready for standard e-commerce only
    merged = {**collected, **result["extracted_entities"]}
    has_product_or_items = bool(merged.get("product") or merged.get("items"))
    ecommerce_complete = bool(has_product_or_items and merged.get("address") and merged.get("phone_number"))
    if ecommerce_complete and not result["order_ready"]:
        logger.info(f"[LLM] Forcing order_ready=True (e-commerce) — keys: {list(merged.keys())}")
        result["order_ready"] = True

    if checkout_summary and not result.get("order_confirmed", False):
        logger.info(f"[LLM] Using dynamically generated checkout_summary from LLM Pydantic output.")
        result["response_text"] = checkout_summary
    elif _should_replace_with_summary(
        result.get("response_text", ""),
        result.get("order_ready", False),
        result.get("order_confirmed", False)
    ):
        is_standard_arabic = False
        if company and getattr(company, "bot_config", None):
            lang_rules = getattr(company.bot_config, "language_rules", "").lower()
            is_standard_arabic = any(keyword in lang_rules for keyword in [
                "arabe pur", "arabe standard", "fusha", "classique", "littéraire", 
                "pas de tunisien", "sans tunisien", "pas de dialecte", "sans dialecte"
            ])
            
        result["response_text"] = _build_checkout_summary_text(
            merged,
            result.get("response_text", ""),
            is_standard_arabic=is_standard_arabic
        )


def _process_sales_output(output_data, result):
    if isinstance(output_data, dict):
        result["response_text"] = output_data.get("response_text", "")
        result["carousel_items"] = output_data.get("carousel_items", [])
    else:
        result["response_text"] = getattr(output_data, "response_text", "")
        result["carousel_items"] = getattr(output_data, "carousel_items", [])


def _extract_json_string(text: str) -> str:
    if not text:
        return ""
    trimmed = text.strip()
    code_block_match = re.search(r'```(?:json)?\s*(.*?)\s*```', trimmed, re.DOTALL)
    if code_block_match:
        return code_block_match.group(1).strip()
    return trimmed


def clean_llm_response(text: str) -> str:
    if not text:
        return text

    trimmed = text.strip()

    # 1. First, check if the entire message is a raw JSON structure
    if trimmed.startswith('{') and trimmed.endswith('}'):
        try:
            data = json.loads(trimmed)
            for key in ['response', 'response_text', 'text', 'message']:
                if key in data and isinstance(data[key], str):
                    return data[key]
        except Exception:
            pass

    # 2. Match any markdown code blocks and either extract response or strip them
    def replace_block(match):
        full_match_str = match.group(0)
        block_content = match.group(1).strip()
        if block_content.startswith('{') and block_content.endswith('}'):
            try:
                data = json.loads(block_content)
                for key in ['response', 'response_text', 'text', 'message']:
                    if key in data and isinstance(data[key], str):
                        return data[key]
                # If valid JSON but doesn't contain a text field, strip it completely
                return ""
            except Exception:
                pass
        return full_match_str

    cleaned_text = re.sub(r'```(?:json)?\s*(.*?)\s*```', replace_block, text, flags=re.DOTALL)
    
    # Clean up extra newlines/whitespace left after stripping
    cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text).strip()
    return cleaned_text


# ── Helper functions for run_orchestrator ─────────────────────────────────────

def make_search_products_tool(shop_id: str):
    """
    Returns search_products tool closure configured for the specific shop.
    """
    def search_products(query: str) -> str:
        """
        Recherche des produits ou services dans le catalogue de la boutique par mot-clé.
        Renvoie les produits trouvés (nom, prix, disponibilité).

        Args:
            query (str): Le terme de recherche sémantique ou mot-clé.
        """
        try:
            items = ItemVector.objects.filter(shop_id=shop_id)
            if query:
                words = query.lower().split()
                # Check for generic queries where the user just asks to see products or games in general
                generic_words = {"jeu", "jeux", "lo3ab", "l3ab", "game", "games", "produit", "produits", "article", "articles", "tout", "tous", "العاب", "ألعاب", "لعبة"}
                is_generic = any(w in generic_words for w in words)
                
                matched = []
                if not is_generic:
                    for item in items:
                        meta = item.metadata or {}
                        name = meta.get("name", "").lower()
                        desc = meta.get("description", "").lower()
                        if any(w in name or w in desc for w in words):
                            matched.append(item)
                
                if not matched:
                    # Fallback: if no specific product matched or it is a generic query, return the top 5 products
                    items = list(items.order_by("-created_at")[:5])
                else:
                    items = matched[:5]
            else:
                items = items.order_by("-created_at")[:5]

            if not items:
                return "Aucun produit trouvé dans notre catalogue pour cette recherche."

            lines = []
            for item in items:
                meta = item.metadata or {}
                price = meta.get("price") or meta.get("base_price") or "sur demande"
                in_stock = "En stock" if meta.get("in_stock", True) else "En rupture"
                lines.append(f"- ID: {item.item_id} | {meta.get('name')} | Prix: {price} TND | {in_stock}")
            return "\n".join(lines)
        except Exception as ex:
            logger.error(f"[ADK TOOL] search_products error: {ex}")
            return "Une erreur est survenue lors de la recherche des produits."
    return search_products


def make_get_product_details_tool(shop_id: str):
    """
    Returns get_product_details tool closure configured for the specific shop.
    """
    def get_product_details(item_id: str) -> str:
        """
        Récupère la description complète et détaillée d'un produit spécifique à partir de son ID.
        À appeler uniquement si le client demande des informations détaillées ou la description d'un produit spécifique.

        Args:
            item_id (str): L'identifiant unique du produit (ex: 'prod_100').
        """
        try:
            item = ItemVector.objects.filter(shop_id=shop_id, item_id=item_id).first()
            if not item:
                return "Produit introuvable."
            meta = item.metadata or {}
            name = meta.get("name") or "Produit sans nom"
            desc = meta.get("description") or "Pas de description détaillée disponible."
            price = meta.get("price") or meta.get("base_price") or "sur demande"
            in_stock = "En stock" if meta.get("in_stock", True) else "En rupture"
            return f"Produit : {name}\n- Prix : {price} TND\n- Disponibilité : {in_stock}\n- Description : {desc}"
        except Exception as e:
            logger.error(f"[ADK TOOL] get_product_details error: {e}")
            return "Une erreur est survenue lors de la récupération des détails du produit."
    return get_product_details


def make_check_order_status_tool(shop_id: str):
    """
    Returns check_order_status tool closure configured for the specific shop.
    """
    def check_order_status(order_reference: str, phone_number: str) -> str:
        """
        Vérifie le statut d'une commande dans la base de données.

        Args:
            order_reference (str): Référence de la commande (ex: PRE-17163829).
            phone_number (str): Numéro de téléphone de la commande (8 chiffres).
        """
        try:
            ref = order_reference.strip()
            phone = phone_number.strip()
            lead = Lead.objects.filter(
                pending_order_reference=ref,
                shop_id=shop_id,
                extracted_data__phone_number=phone
            ).first()

            if not lead:
                return f"Aucune commande trouvée avec la référence {ref} et le numéro {phone}."

            status_map = {
                "NEW_CONVERSATION": "Reçue",
                "WAITING_USER_REPLY": "En cours",
                "LLM_ACTIVE": "En traitement",
                "LLM_CONFIRMING": "En attente de confirmation",
                "COMPLETED": "Confirmée",
                "CANCELLED": "Annulée",
            }
            friendly_status = status_map.get(lead.lead_status or "", "En traitement")
            items_str = ", ".join([item.product_name for item in lead.items.all()]) or "Articles"

            created_date = "N/A"
            if lead.pending_order_created_at:
                created_date = lead.pending_order_created_at.strftime("%d/%m/%Y")

            return (
                f"Statut de la commande {ref} :\n"
                f"- Date : {created_date}\n"
                f"- Statut actuel : {friendly_status}\n"
                f"- Articles commandés : {items_str}"
            )
        except Exception as ex:
            logger.error(f"[ADK TOOL] check_order_status error: {ex}")
            return "Impossible de récupérer le statut de la commande actuellement."
    return check_order_status


def _init_orchestrator_result() -> Dict[str, Any]:
    return {
        "response_text": "",
        "detected_intent": "OTHER",
        "extracted_entities": {},
        "order_ready": False,
        "order_confirmed": False,
        "carousel_items": [],
        "active_agent": "FAQ",
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "model_name": "gemini-2.5-flash",
        "error": False,
        "error_type": "none",
        "error_detail": "",
        "checkout_abandoned": False,
    }


def _detect_checkout_abandon_with_llm(user_message: str, api_key: str) -> Tuple[bool, bool]:
    """
    Detect whether an active checkout lock should be released and/or if the checkout is abandoned.

    Returns (should_release_lock, is_abandonment). On failure, keeps the lock active (False, False).
    """
    try:
        client = Client(api_key=api_key)
        system_instruction = (
            "Tu es un classificateur binaire pour libérer ou non le verrou de checkout. "
            "Un client est actuellement dans un processus de checkout actif. "
            "Tu dois remplir le schéma JSON en évaluant deux variables :\n"
            "1. 'should_release_lock': True si le dernier message du client pose une question (prix, stock, livraison, etc.) "
            "OU s'il souhaite annuler/abandonner la commande en cours. False s'il continue simplement le checkout.\n"
            "2. 'is_abandonment': True uniquement si le client exprime explicitement l'intention d'abandonner, d'annuler, "
            "de stopper ou de vider son panier. Sois extrêmement attentif aux expressions d'annulation en dialecte tunisien (Derja), "
            "arabizi ou français comme : 'annule', 'annuler', 'annuli', 'batal', 'batalet', 'non annule', 'samhni ncommondich', "
            "'nahhi', 'sayeb 3lya', 'faddit', 'je veux annuler', 'non c'est bon', 'la la batalet'. "
            "False s'il pose simplement une question (ex: 'combien ça coute ?', 'kadesh l soum', 'fama stock ?') sans annuler."
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Message du client : {user_message}",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=CheckoutLockDecision,
                temperature=0.0,
            ),
        )
        decision_data = json.loads(response.text or "{}")
        should_release = bool(decision_data.get("should_release_lock", False))
        is_abandonment = bool(decision_data.get("is_abandonment", False))
        reasoning = decision_data.get("reasoning", "")
        logger.info(
            f"[CHECKOUT LOCK LLM] should_release={should_release} | is_abandonment={is_abandonment} | Reason: {reasoning}"
        )
        return should_release, is_abandonment
    except Exception as e:
        logger.warning(
            f"[CHECKOUT LOCK LLM] Detection failed ({e}). Keeping checkout lock active."
        )
        return False, False


def _should_lock_to_checkout(
    current_agent: str,
    conversation_state: str,
    should_release_lock: bool,
) -> bool:
    """
    Return True when the router must skip the main LLM and keep CHECKOUT active.
    """
    if current_agent != "CHECKOUT":
        return False

    locked_states = {"LLM_ACTIVE", "LLM_CONFIRMING"}
    if conversation_state not in locked_states:
        return False

    if should_release_lock:
        logger.info("[CHECKOUT LOCK] Lock released by LLM detection. Routing normally.")
        return False

    logger.info(
        f"[CHECKOUT LOCK] Active. Forcing CHECKOUT (state={conversation_state})."
    )
    return True


def _resolve_target_agent(
    image_url: Optional[str],
    user_message: str,
    history: List[Dict[str, Any]],
    current_agent: str,
    conversation_state: str,
    api_key: str,
    company: Any,
    should_release_lock: bool,
) -> str:
    if image_url:
        return "SALES"
    if _should_lock_to_checkout(current_agent, conversation_state, should_release_lock):
        return "CHECKOUT"
    return determine_target_agent_with_llm(
        user_message=user_message,
        history=history,
        current_agent=current_agent,
        api_key=api_key,
        shop_name=company.name,
        business_domain=getattr(company.bot_config, "business_domain", "Boutique en ligne"),
    )


def _update_active_agent_context(conversation: Conversation, context_data: dict, target_agent: str, result: dict):
    context_data["_active_agent"] = target_agent
    conversation.context_data = context_data
    try:
        if conversation.pk:
            conversation.save(update_fields=["context_data"])
        else:
            conversation.save()
    except Exception as e:
        logger.warning(f"[AGENT CONTEXT] Failed to save conversation with update_fields: {e}. Retrying full save.")
        conversation.save()
    result["active_agent"] = target_agent


def _compile_agent_instructions(company, catalog_text: str, collected: dict, context_data: dict = None) -> dict:
    bot_config = getattr(company, "bot_config", None)
    shop_name = company.name
    llm_context = company.llm_context or "Aucun contexte fourni."
    required_checkout_info = "1. Nom, 2. Adresse, 3. Téléphone"
    delivery_policy = ""
    business_domain = "Boutique en ligne"
    target_audience = "Grand public"
    communication_tone = "Chaleureux et professionnel"
    language_rules = "Réponds en ARABE si le client écrit en arabe ou arabizi. Réponds en FRANÇAIS si le client écrit en français."
    ai_agent_name = "Tiktak AI"

    if bot_config:
        shop_name = bot_config.shop_name or company.name
        llm_context = bot_config.get_compiled_llm_context()
        required_checkout_info = bot_config.required_checkout_info
        delivery_policy = bot_config.delivery_policy
        business_domain = bot_config.business_domain or "Boutique en ligne"
        target_audience = bot_config.target_audience or "Grand public"
        communication_tone = bot_config.communication_tone or "Chaleureux et professionnel"
        language_rules = bot_config.language_rules or "Réponds en ARABE si le client écrit en arabe ou arabizi. Réponds en FRANÇAIS si le client écrit en français."
        ai_agent_name = bot_config.ai_agent_name or "Tiktak AI"

    dynamic_linguistic_rules = (
        f"RÈGLES DE LANGUE ET DE TON (CRITIQUE DE SÉCURITÉ) :\n"
        f"1. CONSIGNES DE LANGUE PRIORITAIRES (DÉFINIES PAR LA BOUTIQUE) :\n"
        f"   -> {language_rules}\n\n"
        f"2. DIRECTIVES DE SECOURS PAR DÉFAUT (Applicables uniquement s'il n'y a aucun conflit avec les consignes prioritaires ci-dessus) :\n"
        f"   - Si le client utilise le dialecte tunisien (Derja ou arabizi) et qu'aucune consigne prioritaire ci-dessus ne l'interdit, tu peux lui répondre en Derja tunisienne chaleureuse.\n"
        f"   - Ne mélange JAMAIS les langues dans une même phrase (pas de mélange de langues).\n\n"
        f"3. Ton général à adopter : {communication_tone}.\n"
        f"4. Ne rien inventer qui ne figure pas dans le contexte ou le catalogue fourni.\n"
        f"5. ⚠️ RÈGLE DE SÉCURITÉ DES IDENTIFIANTS : Ne mentionne JAMAIS l'identifiant technique (ex: 'prod_1778769497868' ou 'ID: 3') d'un produit dans le texte de ta réponse envoyée au client. Les identifiants (item_id) sont réservés uniquement aux structures de données de sortie (comme 'carousel_items') ou aux appels d'outils."
    )
    
    agent_identity_prefix = f"Tu t'appelles '{ai_agent_name}' et tu es l'assistant de la boutique '{shop_name}' (Domaine : {business_domain}, Cible : {target_audience}).\n"

    collected_info_str = ""
    if collected:
        collected_info_str = "INFORMATIONS DÉJÀ COLLECTÉES (GROUND TRUTH) :\n" + "\n".join(f"- {k}: {v}" for k, v in collected.items()) + "\n\n"

    last_viewed = context_data.get("_last_viewed_product") if context_data else None
    last_viewed_rule = ""
    if last_viewed:
        last_viewed_rule = (
            f"⚠️ CONTEXTE ANAPHORIQUE DE SÉCURITÉ (CRITIQUE DE SÉCURITÉ) :\n"
            f"- Le dernier produit consulté, décrit ou discuté avec le client est : '{last_viewed}'.\n"
            f"- Si le client dit 'commande cet article', 'ok c'est bon', 'passe la commande', 'عديلي commande', ou exprime l'intention de commander sans répéter explicitement le nom du produit, tu DOIS assumer qu'il veut commander ce produit '{last_viewed}' avec quantité 1 par défaut, et l'ajouter immédiatement à 'items' dans ton schéma de sortie Pydantic !\n\n"
        )

    return {
        "FAQ": (
            f"{dynamic_linguistic_rules}\n\n"
            f"{agent_identity_prefix}"
            f"Tu es l'agent FAQ. Réponds uniquement aux questions générales de la boutique (horaires, adresse, contact, politique générale).\n"
            f"CONTEXTE DE LA BOUTIQUE :\n{llm_context}\n"
            f"LIVRAISON ET PAIEMENT :\n{delivery_policy}"
        ),
        "SALES": (
            f"{dynamic_linguistic_rules}\n\n"
            f"{agent_identity_prefix}"
            f"Tu es l'agent de Vente (Sales). Aide les clients à trouver, comparer et choisir des produits.\n\n"
            f"INDEX DU CATALOGUE DES PRODUITS DE LA BOUTIQUE (SANS DESCRIPTION) :\n"
            f"{catalog_text}\n\n"
            f"RÈGLES :\n"
            f"- Tu DOIS t'appuyer sur l'index du catalogue ci-dessus pour renseigner le client sur les produits existants, leurs prix et leurs disponibilités.\n"
            f"- Si le client demande des informations détaillées, la description ou des spécifications sur un produit spécifique, tu DOIS impérativement appeler l'outil `get_product_details` en lui transmettant son 'item_id'. Ne cherche pas à deviner la description sans appeler cet outil.\n"
            f"- Si besoin d'une recherche sémantique ou plus fine, tu peux également utiliser l'outil `search_products`.\n"
            f"- ⚠️ RÈGLE ABSOLUE — carousel_items OBLIGATOIRE (ZÉRO EXCEPTION) :\n"
            f"  Chaque fois que tu mentionnes OU que tu réponds à propos d'un article, produit ou service SPÉCIFIQUE du catalogue — que ce soit pour donner son prix, sa disponibilité, sa description ou pour le recommander — tu DOIS retourner son item_id dans le champ 'carousel_items'. Ce retour est OBLIGATOIRE même si : (a) le client ne demande que le prix, (b) c'est un seul produit, (c) le message du client est très court. Omettre 'carousel_items' quand un produit du catalogue est cité est une ERREUR CRITIQUE qui empêche le système de mémoriser l'article pour le checkout suivant.\n"
            f"  → Si l'item_id est clairement identifiable dans l'index ci-dessus, utilise-le directement. Si tu as le moindre doute sur l'identifiant exact, appelle OBLIGATOIREMENT l'outil `search_products` pour trouver le bon item_id AVANT de formuler ta réponse.\n"
            f"- ⚠️ RÈGLE MULTI-LANGUE (CRITIQUE DE SÉCURITÉ) : Le client peut nommer un produit du catalogue en arabe ('دقز'), en arabizi ('daggez', 'lo3ba daggez'), en français ('le jeu dagz') ou avec des variations orthographiques. Tu DOIS dans tous les cas identifier le produit correspondant dans le catalogue et retourner son item_id dans 'carousel_items'. Ne laisse JAMAIS 'carousel_items' vide si un produit du catalogue a été identifié dans le message du client.\n"
            f"- Si le client envoie une photo de produit ou demande un article similaire, propose des alternatives en stock et renvoie tous leurs IDs dans `carousel_items`.\n"
            f"- Ne propose JAMAIS de prix ou d'articles n'existant pas dans le catalogue.\n"
            f"- ⚠️ GARDE-FOU ANTI-HALLUCINATION : Si le catalogue est vide ou si aucun article du catalogue ne correspond à la demande du client, laisse 'carousel_items' vide. Ne jamais inventer ou supposer un item_id."
        ),
        "CHECKOUT": (
            f"{dynamic_linguistic_rules}\n\n"
            f"{agent_identity_prefix}"
            f"Tu es l'agent Checkout. Ton unique rôle est de collecter les informations requises pour finaliser la commande ou la réservation, puis de demander confirmation du récapitulatif de la commande.\n\n"
            f"INDEX DU CATALOGUE DES PRODUITS DE LA BOUTIQUE (SANS DESCRIPTION) :\n"
            f"{catalog_text}\n\n"
            f"INFORMATIONS OBLIGATOIRES À COLLECTER :\n{required_checkout_info}\n\n"
            f"{last_viewed_rule}"
            f"{collected_info_str}"
            f"RÈGLES DE COLLECTE ET DE CONFIRMATION :\n"
            f"- ⚠️ RÈGLE DE VÉRIFICATION DU PRODUIT (CRITIQUE DE SÉCURITÉ) : Avant de commencer à collecter les informations du client (comme le nom, l\\'adresse ou le téléphone), tu DOIS impérativement vérifier que le produit demandé figure dans l\\'INDEX DU CATALOGUE ci-dessus. Si le produit n\\'existe pas ou s\\'il est en rupture de stock (indiqué par \\'En rupture\\'), tu ne dois pas initier ou continuer le processus de commande : réponds poliment au client qu\\'il n\\'est pas disponible, propose-lui de choisir un autre produit en stock, et n\\'ajoute pas ce produit dans \\'extracted_entities\\' ni dans \\'items\\'.\n"
            f"- Ne redemande JAMAIS une information déjà présente dans 'INFORMATIONS DÉJÀ COLLECTÉES' (sauf si le client demande explicitement à la corriger).\n"
            f"- Demande UNE SEULE information manquante à la fois.\n"
            f"- N'invente aucune valeur. Demande confirmation poliment si nécessaire.\n"
            f"- Extrais dynamiquement les informations demandées par la boutique dans 'INFORMATIONS OBLIGATOIRES À COLLECTER'.\n"
            f"- Pour les concepts universels, utilise strictement ces clés canoniques si elles s'appliquent : 'name', 'phone_number', 'address', 'items'.\n"
            f"- Pour une commande de produits physiques ou catalogue, 'items' doit être une liste d'objets avec au minimum 'product_name' et 'quantity'. Ajoute 'attributes' pour les variantes comme taille, couleur ou parfum.\n"
            f"- ⚠️ RÈGLE DE SÉCURITÉ PANIER OBLIGATOIRE : Pour la clé 'product_name' (ou dans le panier 'items'), utilise TOUJOURS le nom exact du produit tel qu'il est écrit dans le catalogue ou les messages précédents de la conversation (généralement en caractères latins, ex: 'Fakret Noukat'). Ne traduis JAMAIS le nom du produit en caractères arabes (n'écris pas 'فقرة نكت' ou 'منوبولي').\n"
            f"- Pour les autres informations métier spécifiques à la boutique, utilise des clés en anglais snake_case non traduites (ex: company_name, daily_volume, appointment_date, service_type, preferred_time).\n"
            f"- Dès que TOUTES les informations requises ont une valeur valide et non vide dans l'historique ou dans 'INFORMATIONS DÉJÀ COLLECTÉES', passe 'order_ready' à True.\n"
            f"- Si le client demande à corriger ou modifier une information (ex: 'L'adresse beb mnara', 'Desloe beb mnara', 'non mon numero est 98...'), tu DOIS extraire cette nouvelle valeur corrigée dans 'extracted_entities' sous la clé correspondante (ex: 'address' ou 'phone_number') pour écraser la précédente, et confirme poliment la modification.\n"
            f"- Si le client refuse, s'oppose, dit 'Non', ou demande à annuler la commande (ex: 'Non annule', 'annuler'), garde 'order_confirmed' à False, indique poliment dans ton message que le changement ou l'annulation a été pris en compte, et passe 'order_ready' à False pour lui permettre de modifier ou de recommencer.\n"
            f"- Quand 'order_ready' vaut True (et seulement s'il n'y a pas d'annulation/refusal ou de correction en cours), ta réponse au client DOIT toujours contenir un récapitulatif clair de toutes les entités collectées (produits/quantités, adresse, téléphone, nom et champs métier dynamiques), puis une question de confirmation explicite.\n"
            f"- Ne finalise jamais sans cette étape de récapitulatif : le client doit répondre clairement oui/non après avoir vu les informations collectées.\n"
            f"- Une fois le récapitulatif présenté, si le client confirme explicitement son accord (sois très flexible et accepte toutes les variantes courantes : 'oui', 'ey', 'ok', 'okay', 'mrigl', 'c'est bon', 'd'accord', 'عديها'), passe 'order_confirmed' à True et génère un message de remerciement et de confirmation de commande/démo très chaleureux et rassurant, en accord parfait avec le domaine d'activité de la boutique (ex: confirmer qu'un expert va appeler pour la démo B2B, ou que le colis B2C est enregistré pour expédition sous 2-3 jours) et ses règles de langue.\n"
            f"- Si le client s'oppose, annule ou modifie une information, garde 'order_confirmed' à False et ajuste les informations ou réponds de manière appropriée.\n"
            f"- ⚠️ RÈGLE DE QUESTION / CLARIFICATION : Si le client pose une question ou demande des précisions (ex: sur le prix d'un produit, les conditions, la livraison) au lieu de répondre par une confirmation claire (Oui/Non), tu DOIS impérativement garder 'order_confirmed' à False (car le client n'a pas encore validé), répondre précisément à sa question dans 'response_text' (en t'appuyant sur l'historique ou le catalogue), et garder 'order_ready' à True pour lui présenter à nouveau le récapitulatif ensuite."
        ),
        "POST_SALES": (
            f"{dynamic_linguistic_rules}\n\n"
            f"{agent_identity_prefix}"
            f"Tu es l'agent de Service Après-Vente (SAV / Post-Sales).\n"
            f"RÈGLES :\n"
            f"- Pour suivre un colis ou une commande, demande la référence et le numéro de téléphone, puis utilise l'outil `check_order_status`.\n"
            f"- Gère les demandes de retours, d'échanges ou de réclamations conformément à la politique de la boutique :\n{delivery_policy}"
        )
    }


def _create_adk_agents(instructions: dict, search_tool, details_tool, status_tool) -> dict:
    faq_agent = Agent(
        name="faq_agent",
        model="gemini-2.5-flash",
        instruction=instructions["FAQ"],
        tools=[],
        sub_agents=[],
    )

    sales_agent = Agent(
        name="sales_agent",
        model="gemini-2.5-flash",
        instruction=instructions["SALES"],
        tools=[search_tool, details_tool],
        sub_agents=[],
        output_schema=DynamicSalesSchema,
    )

    checkout_agent = Agent(
        name="checkout_agent",
        model="gemini-2.5-flash",
        instruction=instructions["CHECKOUT"],
        tools=[],
        sub_agents=[],
        output_schema=DynamicCheckoutSchema,
    )

    post_sales_agent = Agent(
        name="post_sales_agent",
        model="gemini-2.5-flash",
        instruction=instructions["POST_SALES"],
        tools=[status_tool],
        sub_agents=[],
    )

    return {
        "FAQ": faq_agent,
        "SALES": sales_agent,
        "CHECKOUT": checkout_agent,
        "POST_SALES": post_sales_agent,
    }


def _initialize_runner_with_history(selected_agent: Agent, conversation: Conversation, history: List[dict]) -> InMemoryRunner:
    runner = InMemoryRunner(agent=selected_agent)
    session_id = f"sess_{conversation.id}"
    user_id = f"user_{conversation.sender_id}"

    runner.session_service.create_session_sync(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id
    )

    session = runner.session_service.get_session_sync(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id
    )

    for msg_history in history:
        role = "user" if msg_history.get("role") == "user" else "model"
        content_obj = types.Content(
            role=role,
            parts=[types.Part.from_text(text=msg_history.get("text", ""))]
        )
        author = "user" if role == "user" else selected_agent.name
        event = Event(
            invocation_id=session_id,
            author=author,
            content=content_obj
        )
        session.events.append(event)

    return runner


def _append_image_to_parts(parts: list, image_url: Optional[str]):
    if image_url:
        if image_url.startswith("http"):
            try:
                resp = requests.get(image_url, timeout=10)
                if resp.status_code == 200:
                    mime_type = resp.headers.get("content-type", "image/jpeg")
                    parts.append(types.Part.from_bytes(data=resp.content, mime_type=mime_type))
                else:
                    logger.warning(f"[ADK] Failed to fetch image from URL: status {resp.status_code}")
            except Exception as e:
                logger.warning(f"[ADK] Error downloading image URL: {e}")
        else:
            parts.append(types.Part.from_uri(file_uri=image_url, mime_type="image/jpeg"))


def _parse_runner_events(events, target_agent, user_message, collected, result, company=None):
    for event in events:
        if event.usage_metadata:
            result["prompt_tokens"] += event.usage_metadata.prompt_token_count or 0
            result["completion_tokens"] += event.usage_metadata.candidates_token_count or 0

        if event.error_code:
            result["error"] = True
            result["error_type"] = "api_error"
            result["error_detail"] = event.error_message or ""

        if event.is_final_response():
            if target_agent == "CHECKOUT" and event.output:
                try:
                    _process_checkout_output(event.output, user_message, collected, result, company=company)
                except Exception as parse_err:
                    logger.error(f"[ADK] Checkout schema parse error: {parse_err}")
                    result["error"] = True
                    result["error_type"] = "json_parse"
            elif target_agent == "SALES" and event.output:
                try:
                    _process_sales_output(event.output, result)
                except Exception as parse_err:
                    logger.error(f"[ADK] Sales schema parse error: {parse_err}")
                    result["error"] = True
                    result["error_type"] = "json_parse"
            elif event.content and event.content.parts:
                text_parts = [p.text for p in event.content.parts if p.text]
                joined_text = "\n".join(text_parts)
                
                json_str = _extract_json_string(joined_text)
                if target_agent == "CHECKOUT" and json_str.startswith("{") and json_str.endswith("}"):
                    try:
                        output_data = json.loads(json_str)
                        _process_checkout_output(output_data, user_message, collected, result, company=company)
                    except Exception as e:
                        logger.warning(f"[ADK] Fallback JSON parse failed: {e}")
                        result["response_text"] = joined_text
                elif target_agent == "SALES" and json_str.startswith("{") and json_str.endswith("}"):
                    try:
                        output_data = json.loads(json_str)
                        _process_sales_output(output_data, result)
                    except Exception as e:
                        logger.warning(f"[ADK] Fallback Sales JSON parse failed: {e}")
                        result["response_text"] = joined_text
                else:
                    result["response_text"] = joined_text


def _get_intent_for_agent(target_agent: str) -> str:
    intent_map = {
        "FAQ": "FAQ",
        "SALES": "ASK_PRICE",
        "CHECKOUT": "ORDER_PRODUCT",
        "POST_SALES": "SUPPORT",
    }
    return intent_map.get(target_agent, "OTHER")


def run_orchestrator(
    user_message: str,
    image_url: Optional[str],
    conversation: Conversation,
    company,
    history: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Orchestrate between the 4 specialized agents (FAQ, Sales, Checkout, PostSales)
    using the Google ADK runner.
    """
    shop_id = company.shop_id
    api_key = company.gemini_api_key

    # Fetch full product catalog
    catalog_text = _get_shop_catalog_text(shop_id)

    # Initialize result structure
    result = _init_orchestrator_result()

    if not api_key:
        result["error"] = True
        result["error_type"] = "no_api_key"
        result["response_text"] = "Service temporairement indisponible (Clé API manquante)."
        return result

    # Set Gemini API Key in the environment for ADK to pick up
    os.environ["GEMINI_API_KEY"] = api_key
    # Allow async unsafe Django operations inside ADK async execution
    os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

    # Determine current context data
    context_data = conversation.context_data or {}
    current_agent = context_data.get("_active_agent", "FAQ")
    
    # Pre-detect checkout lock release/abandonment if in checkout
    should_release_lock = False
    is_abandonment = False
    if current_agent == "CHECKOUT" and conversation.state in {"LLM_ACTIVE", "LLM_CONFIRMING"}:
        should_release_lock, is_abandonment = _detect_checkout_abandon_with_llm(user_message, api_key)

    # Check if the user is in an active checkout and explicitly cancels or abandons
    checkout_abandoned = False
    if is_abandonment:
        logger.info("[CHECKOUT CANCEL] Checkout abandonment detected. Clearing context data and completing conversation.")
        checkout_abandoned = True
        # Clear all non-system checkout entities from context_data
        keys_to_clear = [k for k in context_data.keys() if not k.startswith('_')]
        for k in keys_to_clear:
            context_data.pop(k, None)
        conversation.context_data = context_data
        conversation.state = "LLM_CANCELED"
        conversation.completed_at = timezone.now()
        conversation.save()

        # Clear Redis context memory so the history is cleaned
        from apps.gateway.services.pipeline import context_manager
        context_manager.clear_context(conversation.sender_id, shop_id)

        # Determine cancellation message based on language config
        is_arabic = bool(re.search(r'[\u0600-\u06FF]', user_message))
        is_standard_arabic = False
        bot_config = getattr(company, "bot_config", None)
        if bot_config:
            lang_rules = getattr(bot_config, "language_rules", "").lower()
            if "arabe" in lang_rules or "fusha" in lang_rules:
                is_arabic = True
            is_standard_arabic = any(keyword in lang_rules for keyword in [
                "arabe pur", "arabe standard", "fusha", "classique", "littéraire", 
                "pas de tunisien", "sans tunisien", "pas de dialecte", "sans dialecte"
            ])

        if is_arabic:
            if is_standard_arabic:
                bot_text = "تم إلغاء طلبكم بنجاح وإفراغ سلة المشتريات. إذا كنتم ترغبون في تقديم طلب جديد، نحن في خدمتكم."
            else:
                bot_text = "حسناً، تم إلغاء طلبكم بنجاح وتفريغ سلة المشتريات. إذا كنتم ترغبون في بدء طلب جديد أو لديكم أي استفسار آخر، فنحن في خدمتكم."
        else:
            bot_text = "Votre commande a été annulée avec succès et votre panier a été vidé. N'hésitez pas si vous avez d'autres questions !"

        result["response_text"] = bot_text
        result["checkout_abandoned"] = True
        result["detected_intent"] = "CANCEL_ORDER"
        return result

    collected = {k: v for k, v in context_data.items() if not k.startswith('_') and v}

    # Resolve target agent
    target_agent = _resolve_target_agent(
        image_url,
        user_message,
        history,
        current_agent,
        conversation.state,
        api_key,
        company,
        should_release_lock
    )

    # Update active agent context
    _update_active_agent_context(conversation, context_data, target_agent, result)

    # Compile instructions
    instructions = _compile_agent_instructions(company, catalog_text, collected, context_data)

    # Define tools
    search_products_tool = make_search_products_tool(shop_id)
    get_product_details_tool = make_get_product_details_tool(shop_id)
    check_order_status_tool = make_check_order_status_tool(shop_id)

    # Build agents
    agents = _create_adk_agents(instructions, search_products_tool, get_product_details_tool, check_order_status_tool)
    selected_agent = agents.get(target_agent, agents["FAQ"])

    # Run ADK agent
    try:
        runner = _initialize_runner_with_history(selected_agent, conversation, history)
        parts = [types.Part.from_text(text=user_message)]
        _append_image_to_parts(parts, image_url)
        current_msg = types.Content(role="user", parts=parts)

        events = list(runner.run(
            user_id=f"user_{conversation.sender_id}",
            session_id=f"sess_{conversation.id}",
            new_message=current_msg
        ))

        _parse_runner_events(events, target_agent, user_message, collected, result, company=company)
        result["detected_intent"] = _get_intent_for_agent(target_agent)

    except Exception as e:
        logger.error(f"[ADK RUNNER ERROR] Failed to run agent={target_agent}: {e}")
        result["error"] = True
        result["error_type"] = "api_error"
        result["error_detail"] = str(e)
        result["response_text"] = "Désolé, je rencontre des difficultés pour traiter votre demande actuellement."

    # Clean the response text
    result["response_text"] = clean_llm_response(result["response_text"])
    result["checkout_abandoned"] = checkout_abandoned

    return result
