"""
llm_response_service.py — LLM Direct Response Mode

When a Company has response_mode='llm', this service replaces the entire
NLU pipeline. Gemini generates a natural-language response using the
company's llm_context + live product catalog with stock, and can also
create orders when all entities are collected.

Key differences from gemini_service.py (NLU fallback):
- gemini_service → returns structured intent+entities for the NLU pipeline
- llm_response_service → returns a direct response to the client + optional order data

Each company uses its OWN Gemini API key (isolation of consumption).
"""
import re
import json
import logging

logger = logging.getLogger(__name__)


# ── Utilities ────────────────────────────────────────────────────────────────

def _clean_json(text: str) -> str:
    """
    Strip markdown code fences that Gemini sometimes adds around JSON,
    especially when the content contains Arabic/RTL characters.
    e.g.  ```json\n{...}\n```  →  {...}
    """
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ``` wrappers
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    # Remove BOM or zero-width chars
    text = text.lstrip('\ufeff\u200b\u200f\u200e')
    return text.strip()


def _detect_lang(text: str) -> str:
    """
    Detect if text is Arabic (contains Arabic Unicode block chars).
    Returns 'ar' or 'fr'.
    """
    arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06ff')
    return 'ar' if arabic_chars > len(text) * 0.1 else 'fr'


_ERROR_MESSAGES = {
    'ar': {
        'retry':       'عذراً، حدث خطأ. الرجاء المحاولة مجدداً.',
        'unavailable': 'الخدمة غير متاحة حالياً. الرجاء المحاولة لاحقاً.',
    },
    'fr': {
        'retry':       'Désolé, une erreur est survenue. Veuillez réessayer.',
        'unavailable': 'Service temporairement indisponible. Veuillez réessayer plus tard.',
    },
}


def _format_catalog_for_prompt(products: list) -> str:
    """
    Format the product catalog as compact text for the LLM system prompt.

    Only includes products with at least one variation in stock.
    Format is kept minimal (~5 tokens per product) to avoid token bloat.
    The data comes from Redis cache (tiktak_service.get_products) — no extra HTTP calls.

    Example output:
        - Pull Polo | 42 TND | Marron(S/M/L), Bleu Canard(S/M/L/XL/XXL)
        - T-Shirt Basic | 29 TND | Blanc(S/M/L/XL), Noir(S/M/L)
    """
    lines = []
    for p in products:
        # Keep only variations with stock > 0
        available = [
            v for v in p.get("variations", [])
            if v.get("stock_quantity", 0) > 0
        ]
        if not available:
            continue  # Entirely out of stock → skip

        # Group sizes by color
        colors: dict[str, list[str]] = {}
        for v in available:
            color = v.get("color") or "Standard"
            size  = v.get("size") or ""
            if color not in colors:
                colors[color] = []
            if size:
                colors[color].append(size)

        color_parts = []
        for color, sizes in colors.items():
            if sizes:
                color_parts.append(f"{color}({'/'.join(sizes)})")
            else:
                color_parts.append(color)

        try:
            price = int(float(p.get("base_price", 0)))
        except (ValueError, TypeError):
            price = p.get("base_price", "?")

        lines.append(f"- {p['name']} | {price} TND | {', '.join(color_parts)}")

    if not lines:
        return "Aucun produit disponible en stock actuellement."
    return "\n".join(lines)


# ── Prompt template ──────────────────────────────────────────────────────────

SYSTEM_PROMPT_LLM_MODE = """Tu es l'assistant IA de la boutique "{company_name}".

--- CONTEXTE BOUTIQUE ---
{llm_context}

--- CATALOGUE PRODUITS ET STOCK EN TEMPS RÉEL ---
{catalog_section}
⚠️ Ne propose JAMAIS un produit absent de cette liste.
⚠️ Si la couleur/taille demandée n'est PAS dans la liste → dis clairement que c'est épuisé et propose les alternatives disponibles.

--- ENTITÉS DÉJÀ COLLECTÉES (NE PAS RE-DEMANDER CES INFORMATIONS) ---
{collected_entities_str}

--- RÈGLES CRITIQUES ---
1. Tu comprends parfaitement le dialecte tunisien (Arabizi, Derja, mélange arabe/français).
2. LANGUE DE RÉPONSE — Ordre de priorité STRICT :
   a. Si le CONTEXTE BOUTIQUE ci-dessus indique explicitement une langue (ex: "Réponds en arabe",
      "répondre en français"...) → RESPECTE TOUJOURS cette langue, quelle que soit la langue du client.
   b. Sinon (aucune langue imposée dans le contexte) → adapte-toi à la langue du client :
      - Client écrit en arabe ou arabizi → réponds en ARABE TUNISIEN (Derja)
      - Client écrit en français → réponds en FRANÇAIS
3. Ne mélange JAMAIS les deux langues dans une même réponse.
4. Sois professionnel, sympathique et concis (2-3 phrases max).
5. Ne réponds qu'aux sujets liés à la boutique.
6. Ne mentionne JAMAIS un produit absent du CATALOGUE ci-dessus.

--- HISTORIQUE RÉCENT ---
{conversation_context}

--- FORMAT DE RÉPONSE ---
Réponds TOUJOURS en JSON avec cette structure EXACTE :
{{
  "response_text": "Le texte à envoyer au client",
  "detected_intent": "GREETING|ORDER_PRODUCT|ASK_PRICE|ASK_AVAILABILITY|ASK_DELIVERY|FAQ|SUPPORT|CANCEL_ORDER|OTHER",
  "extracted_entities": {{
    "product": null,
    "color": null,
    "size": null,
    "address": null,
    "phone_number": null,
    "quantity": null
  }},
  "order_ready": false
}}

IMPORTANT : Ne mets JAMAIS "product_id" dans extracted_entities. Uniquement le NOM du produit dans le champ "product".

--- LOGIQUE DE COMMANDE ---
Entités OBLIGATOIRES pour finaliser une commande : product, address, phone_number
Entités OPTIONNELLES : color, size, quantity (défaut = 1 si non précisé)

Processus strict :
1. Consulte "ENTITÉS DÉJÀ COLLECTÉES" — ces infos sont ACQUISES, ne les re-demande JAMAIS
2. Identifie les entités OBLIGATOIRES encore manquantes
3. Demande UNE SEULE info manquante à la fois dans response_text
4. Dans extracted_entities → mets UNIQUEMENT les nouvelles infos du message ACTUEL
5. CONDITION order_ready=true : product + address + phone_number sont tous présents
   (soit dans ENTITÉS DÉJÀ COLLECTÉES, soit dans ce message)
   → Quand cette condition est remplie : mets order_ready=true ET envoie un
     RÉCAPITULATIF COMPLET en demandant confirmation (ex: "Confirmes-tu ta commande ?")

PHASE DE CONFIRMATION (quand l'état est LLM_CONFIRMING) :
- Si le client dit "oui/ey/ok/behi/confirme" → mets order_ready=true
- Si le client CORRIGE une info (nouveau numéro, nouvelle adresse...) →
  mets la nouvelle valeur dans extracted_entities + mets order_ready=true
  et envoie un nouveau récapitulatif mis à jour
- Ne crée jamais la commande sans confirmation explicite du client"""


def generate_llm_response(
    text: str,
    company,
    shop_id: str = None,
    conversation_history: list = None,
    current_context: dict = None,
) -> dict:
    """
    Generate a direct response using the company's Gemini API key.

    Args:
        text: Client's message
        company: Company model instance (with gemini_api_key, llm_context, name)
        shop_id: Shop identifier — used to fetch the live product catalog for stock injection
        conversation_history: List of recent messages [{role, text, intent?}]
        current_context: Accumulated entities from previous messages

    Returns:
        {
            "response_text": str,
            "detected_intent": str,
            "extracted_entities": dict,
            "order_ready": bool,
            "error": bool,
            "error_type": str,   # "none" | "json_parse" | "api_error" | ...
        }
    """
    result = {
        "response_text": "",
        "detected_intent": "OTHER",
        "extracted_entities": {},
        "order_ready": False,
        "error": False,
        "error_type": "none",
    }

    # ── Validate API key ──────────────────────────────────────────────────
    api_key = company.gemini_api_key
    lang = _detect_lang(text)
    if not api_key:
        logger.error(f"[LLM] No Gemini API key for company={company.shop_id}")
        result["response_text"] = _ERROR_MESSAGES[lang]['unavailable']
        result["error"] = True
        result["error_type"] = "no_api_key"
        return result

    # ── Build live catalog section (from Redis cache — no extra HTTP call) ─
    catalog_section = "Catalogue non disponible."
    effective_shop = shop_id or getattr(company, 'shop_id', None)
    if effective_shop:
        try:
            from .tiktak_service import get_products
            products = get_products(effective_shop)
            if products:
                catalog_section = _format_catalog_for_prompt(products)
                logger.debug(f"[LLM] Catalog injected: {len(products)} products for shop={effective_shop}")
        except Exception as cat_err:
            logger.warning(f"[LLM] Could not load catalog for shop={effective_shop}: {cat_err}")

    # ── Build collected entities string (shown explicitly in prompt) ──────
    ORDER_FIELDS = {"product", "color", "size", "address", "phone_number", "quantity"}
    collected = {}
    if current_context:
        collected = {
            k: v for k, v in current_context.items()
            if not k.startswith('_') and k in ORDER_FIELDS and v
        }

    if collected:
        collected_entities_str = json.dumps(collected, ensure_ascii=False, indent=2)
    else:
        collected_entities_str = "Aucune entité collectée pour l'instant."

    # ── Build conversation history string ─────────────────────────────────
    conversation_context = "Première interaction avec ce client."
    if conversation_history:
        lines = []
        for msg in conversation_history[-8:]:
            role = "CLIENT" if msg.get("role") == "user" else "BOT"
            lines.append(f"{role}: {msg.get('text', '')}")
        if lines:
            conversation_context = "\n".join(lines)

    # ── Build prompt ──────────────────────────────────────────────────────
    system_prompt = SYSTEM_PROMPT_LLM_MODE.format(
        company_name=company.name,
        llm_context=company.llm_context or "Aucun contexte spécifique fourni pour cette boutique.",
        catalog_section=catalog_section,
        collected_entities_str=collected_entities_str,
        conversation_context=conversation_context,
    )

    # ── Call Gemini ───────────────────────────────────────────────────────
    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=f"CLIENT: {text}",
            config={
                "system_instruction": system_prompt,
                "response_mime_type": "application/json",
                "temperature": 0.2,
            },
        )

        # ── Parse response ────────────────────────────────────────────────
        # _clean_json strips markdown fences Gemini adds for Arabic/RTL content
        raw_text = _clean_json(response.text)
        logger.debug(f"[LLM] Raw Gemini response: {raw_text[:200]}")
        data = json.loads(raw_text)

        result["response_text"] = data.get("response_text", "")
        result["detected_intent"] = data.get("detected_intent", "OTHER")
        result["order_ready"] = bool(data.get("order_ready", False))

        # Extract non-null entities from THIS message only
        raw_entities = data.get("extracted_entities", {})
        if isinstance(raw_entities, dict):
            result["extracted_entities"] = {
                k: v for k, v in raw_entities.items()
                if v is not None and v != "" and v != "null"
            }

        # ── Safety check: verify order_ready conditions server-side ──────
        # Merge context + new entities to check if mandatory fields are present
        merged = {**collected, **result["extracted_entities"]}
        mandatory_present = all(merged.get(f) for f in ("product", "address", "phone_number"))
        if mandatory_present and not result["order_ready"]:
            logger.info(f"[LLM] Forcing order_ready=True — all mandatory entities present: {merged}")
            result["order_ready"] = True

        # ── Log token usage (tracks Gemini implicit caching savings) ─────
        try:
            usage = response.usage_metadata
            cached = getattr(usage, 'cached_content_token_count', 0) or 0
            logger.info(
                f"[LLM] shop={company.shop_id} intent={result['detected_intent']} "
                f"tokens=prompt:{usage.prompt_token_count} "
                f"cached:{cached} "
                f"output:{usage.candidates_token_count} "
                f"new_entities={list(result['extracted_entities'].keys())} "
                f"order_ready={result['order_ready']}"
            )
        except Exception:
            logger.info(
                f"[LLM] shop={company.shop_id} intent={result['detected_intent']} "
                f"order_ready={result['order_ready']}"
            )

    except json.JSONDecodeError as e:
        logger.error(
            f"[LLM] JSON parse error for shop={company.shop_id}: {e} "
            f"| raw={response.text[:300] if 'response' in dir() else 'N/A'}"
        )
        result["response_text"] = _ERROR_MESSAGES[lang]['retry']
        result["error"] = True
        result["error_type"] = "json_parse"
    except ImportError:
        logger.error("[LLM] google-genai package not installed")
        result["response_text"] = _ERROR_MESSAGES[lang]['unavailable']
        result["error"] = True
        result["error_type"] = "import_error"
    except Exception as e:
        logger.error(f"[LLM] API error for shop={company.shop_id}: {type(e).__name__}: {e}")
        result["response_text"] = _ERROR_MESSAGES[lang]['retry']
        result["error"] = True
        result["error_type"] = "api_error"

    return result
