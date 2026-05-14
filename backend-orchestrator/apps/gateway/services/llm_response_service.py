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
from apps.crm.models.analytics import ItemVector


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

# Standard clothing sizes
_KNOWN_SIZES_MULTI: tuple = ('3XL', '2XL', 'XXL', 'XL', 'XS')
_KNOWN_SIZES_SINGLE: tuple = ('L', 'M', 'S')

# Match multi-letter sizes case-insensitively (e.g. xl, Xxl)
_SIZE_PATTERN_MULTI = re.compile(
    r'(?:^|[\s,.\-"])(?P<size>' + '|'.join(re.escape(s) for s in _KNOWN_SIZES_MULTI) + r')(?=[\s,.\-"]|$)',
    re.IGNORECASE,
)

# Match single-letter sizes (L, M, S) ONLY if uppercase OR preceded by 'taille', 'size', 'kobr', etc.
_SIZE_PATTERN_SINGLE = re.compile(
    r'(?:(?:taille|size|kobr|nheb)\s+(?P<size_ci>[lmsLMS])(?=[\s,.\-"]|$))|(?:^|[\s,.\-"])(?P<size_cs>[LMS])(?=[\s,.\-"]|$)'
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
        # Check multi-letter sizes first (XL, XXL, XS...)
        m_multi = _SIZE_PATTERN_MULTI.search(text)
        if m_multi:
            safety['size'] = m_multi.group('size').upper()
            logger.info(f"[LLM SAFETY] Server extracted size='{safety['size']}' from: '{text}'")
        else:
            # Check single-letter sizes (L, M, S)
            m_single = _SIZE_PATTERN_SINGLE.search(text)
            if m_single:
                size_val = m_single.group('size_ci') or m_single.group('size_cs')
                if size_val:
                    safety['size'] = size_val.upper()
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
    Format the RAG product catalog as compact text for the LLM system prompt.

    Expects the Visual RAG format (from ItemVector.metadata):
      { name, price, description, in_stock }

    Output example: "- T-Shirt Vintage | 45 TND"
    """
    lines = []
    for p in products:
        if not p.get("active", True):
            continue

        # Support declinaisons (TikTak API) and variations (internal format)
        raw_variations = p.get("declinaisons") or p.get("variations") or []

        # Resolve price: TikTak API uses 'price', internal uses 'base_price'
        try:
            price = int(float(p.get("price") or p.get("base_price") or 0))
        except (ValueError, TypeError):
            price = p.get("price") or p.get("base_price") or "?"

        # Case 1: Simple product without variations
        if not raw_variations:
            product_stock = p.get("stock") or p.get("total_stock") or 0
            if product_stock <= 0 and not p.get("order_without_stock", False):
                continue
            id_str = f" | ID: {p['id']}" if p.get('id') else ""
            lines.append(f"- {p['name']}{id_str} | {price} TND")
            continue

        # Case 2: Product with variations
        available = [
            v for v in raw_variations
            if (v.get("stock_quantity") or v.get("stock") or 0) > 0
            or v.get("order_without_stock", False)
        ]
        if not available:
            continue

        colors: dict[str, list[str]] = {}
        for v in available:
            color = v.get("color") or v.get("couleur") or "Standard"
            size  = v.get("size") or v.get("taille") or ""
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

        id_str = f" | ID: {p['id']}" if p.get('id') else ""
        lines.append(f"- {p['name']}{id_str} | {price} TND | {', '.join(color_parts)}")

    if not lines:
        return "Aucun produit disponible en stock actuellement."
    return "\n".join(lines)


# ── Prompt template ──────────────────────────────────────────────────────────

SYSTEM_PROMPT_LLM_MODE = """⚠️ LANGUE (PRIORITÉ ABSOLUE) :
Si le GÉRANT impose l'arabe → alphabet arabe (أ ب ت) obligatoirement.
Si le GÉRANT impose le français → français obligatoirement.
Sinon → adapte-toi (arabizi/arabe → arabe | français → français).
Ex: "aslema" → "أسلامة", "bonjour" → "Bonjour". JAMAIS de mélange.

Tu es l'assistant de "{company_name}". Ne réponds qu'aux sujets liés à :
{llm_context}

--- CATALOGUE / OFFRES ---
{catalog_section}
Règles : Aucun produit hors liste. Prix fixes. Propose alternatives si rupture.

--- INFOS DÉJÀ COLLECTÉES ---
{collected_entities_str}
(Acquises. Ne les redemande jamais.)

--- HISTORIQUE (6 derniers messages) ---
{conversation_context}

--- RÈGLES ---
1. Ton chaleureux, concis (max 3 phrases).
2. Ne rien inventer.

--- EXTRACTION D'ENTITÉS ---
Extrais TOUTES les nouvelles infos du message ACTUEL (size, phone_number, address, quantity, date/time, color...).
Règles strictes :
1. Liste `items` : Dès qu'un produit est choisi, format : [{{"product_id": "ID", "product_name": "Nom", "price": prix, "quantity": qte}}].
2. N'inclus PAS les infos DÉJÀ COLLECTÉES.
3. Si le client corrige une info, inclus SEULEMENT la valeur corrigée.

--- COLLECTE & FINALISATION ---
1. Demande UNE SEULE info manquante à la fois selon les besoins du gérant.
2. Si TOUT est collecté : mets order_ready=true, envoie un RÉCAPITULATIF avec le total, demande confirmation ("تأكدلي").
3. Si le client CONFIRME ("ok", "oui", "ey") : order_ready=true, extracted_entities={{}}.
4. Si le client CORRIGE/REFUSE ("non", "ghalta") : order_ready=false, extracted_entities={{"clé": "valeur corrigée"}}.

--- FORMAT JSON OBLIGATOIRE ---
Réponds UNIQUEMENT avec ce JSON valide :
{{
  "response_text": "Le message à envoyer au client",
  "detected_intent": "GREETING|ORDER_PRODUCT|BOOK_APPOINTMENT|REQUEST_SERVICE|RESERVE_TABLE|ASK_PRICE|ASK_AVAILABILITY|ASK_DELIVERY|ASK_INFO|FAQ|SUPPORT|CANCEL|OTHER",
  "extracted_entities": {{}},
  "order_ready": false,
  "carousel_items": ["id1", "id2"] // OPTIONNEL: Liste des ID des produits si tu recommandes des articles du catalogue. Limite à 5.
}}"""





def generate_llm_response(
    text: str,
    company,
    shop_id: str = None,
    conversation_history: list = None,
    current_context: dict = None,
    state_before: str = None,
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
        "prompt_tokens": 0,
        "completion_tokens": 0,
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
    # For service businesses (consulting, medical, legal...) with no product
    # catalog, we inject a neutral message so Gemini knows it's a service
    # company and won't try to reference products.
    catalog_section = "Activité sans catalogue produit — référez-vous uniquement au CONTEXTE DU GÉRANT."
    effective_shop = shop_id or getattr(company, 'shop_id', None)
    if effective_shop:
        try:
            
            # Récupération EXCLUSIVE du nouveau catalogue Visual RAG
            # Optimisation: Limite à 15 au lieu de 50 pour économiser drastiquement les tokens (Input)
            rag_items = ItemVector.objects.filter(shop_id=effective_shop).order_by('-created_at')[:15]
            rag_products = []
            for item in rag_items:
                meta = item.metadata or {}
                name = meta.get("name")
                if not name:
                    continue
                # On simule le format attendu par _format_catalog_for_prompt
                rag_products.append({
                    "id": item.item_id,
                    "name": name,
                    "base_price": str(meta.get("price", "Prix sur demande")),
                    "variations": [],
                    "stock": 100,  # En stock par défaut
                    "active": True
                })

            if rag_products:
                catalog_section = _format_catalog_for_prompt(rag_products)
                logger.debug(f"[LLM] RAG Catalog injected: {len(rag_products)} products for shop={effective_shop}")
            else:
                logger.debug(f"[LLM] No catalog for shop={effective_shop} — service-only business")
        except Exception as cat_err:
            logger.warning(f"[LLM] Could not load catalog for shop={effective_shop}: {cat_err}")

    # ── Build collected entities string (shown explicitly in prompt) ──────
    # Dynamic: ALL entities from context are shown, regardless of their key.
    # This supports any domain: e-commerce (product/size/color), restaurant
    # (dish/nb_persons/reservation_date), medical (reason/patient_name), etc.
    # Only internal keys (starting with '_') are excluded.
    collected = {}
    if current_context:
        collected = {
            k: v for k, v in current_context.items()
            if not k.startswith('_') and v
        }

    if collected:
        collected_entities_str = json.dumps(collected, ensure_ascii=False, indent=2)
    else:
        collected_entities_str = "Aucune entité collectée pour l'instant."

    # ── Build conversation history string ─────────────────────────────────
    conversation_context = "Première interaction avec ce client."
    if conversation_history:
        lines = []
        for msg in conversation_history[-6:]:
            role = "CLIENT" if msg.get("role") == "user" else "BOT"
            lines.append(f"{role}: {msg.get('text', '')}")
        if lines:
            conversation_context = "\n".join(lines)

    # ── Compilation du Contexte LLM (Ancien vs Nouveau) ──────────────────
    llm_context_content = company.llm_context or "Aucun contexte spécifique fourni pour cette boutique."
    if hasattr(company, 'bot_config') and company.bot_config:
        llm_context_content = company.bot_config.get_compiled_llm_context()

    # ── Build prompt ──────────────────────────────────────────────────────
    system_prompt = SYSTEM_PROMPT_LLM_MODE.format(
        company_name=company.name,
        llm_context=llm_context_content,
        catalog_section=catalog_section,
        collected_entities_str=collected_entities_str,
        conversation_context=conversation_context,
    )

    if state_before == "LLM_CONFIRMING":
        system_prompt += "\n\n*** ATTENTION CRITIQUE ***\nLe client est dans l'étape finale de confirmation. S'il pose une question (ex: prix de livraison), réponds-lui, mais TU DOIS ABSOLUMENT lui redemander de confirmer la commande à la fin de ton message (ex: 'C'est bien ça ?', 'Est-ce que je confirme ?')."

    # ── Call Gemini ───────────────────────────────────────────────────────
    response = None
    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        import os
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        response = client.models.generate_content(
            model=model_name,
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
        result["carousel_items"] = data.get("carousel_items", [])

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

        # ── Safety check: force order_ready for standard e-commerce only ──
        # For other domains (restaurant, medical, etc.) Gemini decides via
        # llm_context. We only intervene for classic e-commerce fields.
        merged = {**collected, **result["extracted_entities"]}
        ecommerce_complete = all(merged.get(f) for f in ("product", "address", "phone_number"))
        if ecommerce_complete and not result["order_ready"]:
            logger.info(f"[LLM] Forcing order_ready=True (e-commerce) — keys: {list(merged.keys())}")
            result["order_ready"] = True
            
            # Since Gemini didn't realize the order was complete, its original text
            # likely asks the user for the missing entity. We must replace it with a summary.
            summary = "\n".join(f"- {k}: {v}" for k, v in merged.items() if not k.startswith("_"))
            
            # Simple language detection based on Gemini's original text
            is_arabic = any('\u0600' <= c <= '\u06FF' for c in str(result.get("response_text", "")))
            
            if is_arabic:
                result["response_text"] = f"يعيشك، قيدت كل المعطيات. هاو التلخيص متاعك:\n{summary}\n\nنأكدلك الطلبية؟ (نعم/لا)"
            else:
                result["response_text"] = f"Parfait, j'ai toutes les informations. Voici le récapitulatif :\n{summary}\n\nEst-ce que je confirme la commande ? (Oui/Non)"

        # ── Log token usage (tracks Gemini implicit caching savings) ─────
        try:
            usage = response.usage_metadata
            cached = getattr(usage, 'cached_content_token_count', 0) or 0
            prompt_tokens = getattr(usage, 'prompt_token_count', 0)
            completion_tokens = getattr(usage, 'candidates_token_count', 0)
            
            result["prompt_tokens"] = prompt_tokens
            result["completion_tokens"] = completion_tokens
            result["model_name"] = model_name
            
            logger.info(
                f"[LLM] shop={company.shop_id} intent={result['detected_intent']} "
                f"tokens=prompt:{prompt_tokens} "
                f"cached:{cached} "
                f"output:{completion_tokens} "
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
            f"| raw={response.text[:300] if response and hasattr(response, 'text') else 'N/A'}"
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
