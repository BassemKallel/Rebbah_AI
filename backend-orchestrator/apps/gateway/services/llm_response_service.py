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


# ── Server-side entity extraction (safety net for Gemini misses) ─────────────

# Standard clothing sizes — ordered longest first to avoid S matching inside XS/XL
_KNOWN_SIZES: tuple = ('3XL', '2XL', 'XXL', 'XL', 'XS', 'L', 'M', 'S')
_SIZE_PATTERN = re.compile(
    r'(?<!\w)(' + '|'.join(re.escape(s) for s in _KNOWN_SIZES) + r')(?!\w)',
    re.IGNORECASE,
)
# Tunisian phone: starts with 2,4,5,7,9 and has exactly 8 digits
_PHONE_PATTERN = re.compile(r'(?<!\d)([2457-9]\d{7})(?!\d)')


def _extract_entities_server_side(text: str, existing_entities: dict, collected: dict) -> dict:
    """
    Server-side safety net that runs AFTER Gemini to catch entities it missed.

    Handles cases Gemini frequently misses with Tunisian arabizi:
      - Standalone size letters : "M", "nheb M", "a3tini XL", "bghit L"
      - Tunisian phone numbers  : "55 123 456", "55123456"

    Only fills a field if BOTH Gemini missed it AND it's not already in context.
    """
    safety = {}

    # ── Size ─────────────────────────────────────────────────────────────────
    if not existing_entities.get('size') and not collected.get('size'):
        m = _SIZE_PATTERN.search(text)
        if m:
            safety['size'] = m.group(1).upper()
            logger.info(f"[LLM SAFETY] Server extracted size='{safety['size']}' from: '{text}'")

    # ── Phone number ─────────────────────────────────────────────────────────
    if not existing_entities.get('phone_number') and not collected.get('phone_number'):
        m = _PHONE_PATTERN.search(re.sub(r'[\s.\-]', '', text))
        if m:
            safety['phone_number'] = m.group(1)
            logger.info(f"[LLM SAFETY] Server extracted phone='{safety['phone_number']}' from: '{text}'")

    return safety


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

SYSTEM_PROMPT_LLM_MODE = """Tu es l'assistant IA de "{company_name}".

╔══════════════════════════════════════════════════════════════════════╗
║  CONTEXTE ET INSTRUCTIONS DU GÉRANT                                  ║
╚══════════════════════════════════════════════════════════════════════╝
{llm_context}

⚙️  Ce bloc définit TOUT : l'activité, les règles métier, les informations
    à collecter, la langue imposée, et ce qui constitue une "action complète".
    Respecte ces instructions à la lettre — elles ont la priorité absolue.

╔══════════════════════════════════════════════════════════════════════╗
║  CATALOGUE / OFFRES / SERVICES DISPONIBLES                           ║
╚══════════════════════════════════════════════════════════════════════╝
{catalog_section}

⚠️  Ne mentionne JAMAIS une offre, un produit ou un service absent de cette liste.
⚠️  Si une option demandée (variante, créneau, taille, couleur...) n'est pas disponible
    → informe clairement le client et propose les alternatives existantes.

╔══════════════════════════════════════════════════════════════════════╗
║  INFORMATIONS DÉJÀ RECUEILLIES  (NE PAS RE-DEMANDER)                ║
╚══════════════════════════════════════════════════════════════════════╝
{collected_entities_str}

╔══════════════════════════════════════════════════════════════════════╗
║  RÈGLES DE COMMUNICATION                                             ║
╚══════════════════════════════════════════════════════════════════════╝
1. Tu comprends le dialecte tunisien (Arabizi, Derja, mélange arabe/français).
2. LANGUE — Priorité STRICTE :
   a. Si le CONTEXTE DU GÉRANT impose une langue (ex : "Réponds en arabe") →
      RESPECTE-LA toujours, quelle que soit la langue du client.
   b. Sinon → adapte-toi à la langue du client :
      - Arabe / arabizi → ARABE TUNISIEN (Derja)
      - Français        → FRANÇAIS
3. Ne mélange JAMAIS deux langues dans une même réponse.
4. Sois professionnel, chaleureux et concis (2-3 phrases max par réponse).
5. Réponds uniquement aux sujets liés à l'activité décrite dans le contexte du gérant.
6. Ne fournis jamais d'informations incertaines ou inventées.

╔══════════════════════════════════════════════════════════════════════╗
║  EXTRACTION D'INFORMATIONS                                           ║
╚══════════════════════════════════════════════════════════════════════╝
Extrais TOUTE information utile mentionnée par le client dans ce message.

PRINCIPE CLÉ : Les clés à utiliser dans extracted_entities sont définies
par le CONTEXTE DU GÉRANT, pas par cette liste. Adapte-toi à l'activité.

Détection automatique obligatoire (quelle que soit l'activité) :
  • Tailles standards  → S, M, L, XL, XXL, 2XL, 3XL — même en arabizi isolé
    "nheb M" → size:M | "a3tini XL" → size:XL | "bghit L" → size:L
  • Téléphone tunisien → 8 chiffres, préfixe 2/4/5/7/9  → clé "phone_number"
  • Adresses complètes → clé "address"
  • Dates / horaires   → clé "date", "time" ou "datetime"
  • Quantités          → clé "quantity"

Exemples de clés selon le sous-domaine (liste NON exhaustive, INDICATIVE) :
  Mode / vêtements     → "product", "color", "size", "address", "phone_number", "quantity"
  Chaussures           → "product", "color", "shoe_size", "address", "phone_number"
  Électronique         → "product", "storage", "color", "address", "phone_number", "quantity"
  Alimentaire / épicerie → "product", "quantity", "address", "phone_number"
  Cosmétiques / beauté → "product", "shade", "address", "phone_number", "quantity"
  Mobilier / déco      → "product", "color", "dimensions", "address", "phone_number"
  Restaurant / traiteur → "dish", "nb_persons", "reservation_date", "time_slot", "phone_number"
  Service / artisan    → "service_type", "location", "preferred_date", "phone_number", "notes"
  Médical / RDV        → "reason", "patient_name", "preferred_date", "time_slot", "phone_number"
  Immobilier           → "property_type", "budget", "location", "nb_rooms", "phone_number"
  Hôtel / tourisme     → "destination", "checkin_date", "checkout_date", "nb_persons", "phone_number"

Si l'activité ne correspond à aucun exemple ci-dessus → invente les clés les plus
logiques et explicites en accord avec le CONTEXTE DU GÉRANT.

RÈGLES ABSOLUES :
  1. N'inclus dans extracted_entities QUE les nouvelles infos du message ACTUEL.
  2. Si une information figure dans "INFORMATIONS DÉJÀ RECUEILLIES" →
     ne la redemande JAMAIS et ne l'inclus PAS dans extracted_entities.
  3. Ne mets JAMAIS d'IDs techniques (product_id, variation_id) — uniquement
     des valeurs lisibles (noms, dates, numéros).

╔══════════════════════════════════════════════════════════════════════╗
║  HISTORIQUE RÉCENT                                                   ║
╚══════════════════════════════════════════════════════════════════════╝
{conversation_context}

╔══════════════════════════════════════════════════════════════════════╗
║  FORMAT DE RÉPONSE JSON — OBLIGATOIRE                                ║
╚══════════════════════════════════════════════════════════════════════╝
Réponds TOUJOURS avec ce JSON exact (pas de texte autour) :
{{
  "response_text": "Le message à envoyer au client",
  "detected_intent": "GREETING|ORDER_PRODUCT|BOOK_APPOINTMENT|REQUEST_SERVICE|RESERVE_TABLE|ASK_PRICE|ASK_AVAILABILITY|ASK_DELIVERY|ASK_INFO|FAQ|SUPPORT|CANCEL|OTHER",
  "extracted_entities": {{
    // Inclus UNIQUEMENT les nouvelles infos extraites du message ACTUEL
    // Utilise les clés appropriées à l'activité (voir exemples ci-dessus)
  }},
  "order_ready": false
}}

╔══════════════════════════════════════════════════════════════════════╗
║  LOGIQUE DE COLLECTE ET DE FINALISATION                              ║
╚══════════════════════════════════════════════════════════════════════╝
Le CONTEXTE DU GÉRANT définit quelles informations sont nécessaires pour
finaliser l'action (commande, réservation, rendez-vous, devis, etc.).

Processus :
1. Identifie les informations REQUISES selon le contexte du gérant
2. Vérifie "INFORMATIONS DÉJÀ RECUEILLIES" — ces données sont acquises
3. Demande UNE SEULE information manquante à la fois dans response_text
4. Mets dans extracted_entities UNIQUEMENT les nouvelles infos du message actuel
5. Quand TOUTES les informations requises sont collectées :
   → Mets order_ready: true
   → Envoie un RÉCAPITULATIF COMPLET et demande une confirmation explicite

PHASE DE CONFIRMATION (état LLM_CONFIRMING) :
  • Client confirme ("oui / ey / ok / behi / confirme / na3am / go") →
    maintiens order_ready: true
  • Client corrige une info → mets la nouvelle valeur dans extracted_entities
    + order_ready: true + envoie un récapitulatif mis à jour
  • Ne finalise JAMAIS l'action sans confirmation explicite du client"""


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

        # ── Server-side safety net ────────────────────────────────────────
        # Catches entities Gemini missed (sizes, phone numbers in arabizi context)
        safety_entities = _extract_entities_server_side(
            text, result["extracted_entities"], collected
        )
        result["extracted_entities"].update(safety_entities)

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
