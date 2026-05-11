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
# Pattern checks for spaces, standard punctuation (but EXCLUDES apostrophes to prevent "l'adresse" -> L)
_SIZE_PATTERN = re.compile(
    r'(?:^|[\s,.\-"])(?P<size>' + '|'.join(re.escape(s) for s in _KNOWN_SIZES) + r')(?=[\s,.\-"]|$)',
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
            safety['size'] = m.group('size').upper()
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

    Supports two product structures from tiktak_service.get_products():
      1. Simple products (no variations): declinaisons=[] or variations=[]
         Uses product-level stock and price.
         Output: "- Jeu Ken T7ebni | 59 TND"
      2. Products with variations: declinaisons=[...] or variations=[...]
         Groups in-stock variations by color/size.
         Output: "- Pull Polo | 42 TND | Marron(S/M/L)"

    Supports both TikTak API fields (price, declinaisons) and
    internal format fields (base_price, variations).
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
            lines.append(f"- {p['name']} | {price} TND")
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

        lines.append(f"- {p['name']} | {price} TND | {', '.join(color_parts)}")

    if not lines:
        return "Aucun produit disponible en stock actuellement."
    return "\n".join(lines)


# ── Prompt template ──────────────────────────────────────────────────────────

SYSTEM_PROMPT_LLM_MODE = """Tu es l'assistant IA de "{company_name}". Tu ne réponds QU'aux sujets liés à l'activité décrite ci-dessous. Si le client parle d'autre chose, redirige-le poliment vers l'activité.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 INSTRUCTIONS DU GÉRANT (PRIORITÉ ABSOLUE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{llm_context}

Ces instructions définissent : l'activité, les règles métier, la langue imposée,
et ce qui constitue une "action complète". Elles ont la priorité sur tout le reste.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 CATALOGUE / OFFRES DISPONIBLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{catalog_section}

RÈGLES CATALOGUE :
- Ne mentionne JAMAIS un produit ou service absent de cette liste.
- Si une option n'est pas disponible → informe et propose les alternatives existantes.
- Les prix sont FIXES tels qu'indiqués — ne les modifie jamais.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 INFORMATIONS DÉJÀ COLLECTÉES (NE PAS RE-DEMANDER)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{collected_entities_str}

Ces données sont ACQUISES. Ne les redemande JAMAIS. Utilise-les directement dans
le récapitulatif ou dans ta réponse.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 HISTORIQUE DE LA CONVERSATION (10 derniers messages)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{conversation_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 RÈGLES DE COMMUNICATION (PRIORITÉ ABSOLUE AU GÉRANT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. LANGUE — LA RÈGLE DU GÉRANT EST LA LOI :
   a. Si le CONTEXTE DU GÉRANT demande explicitement d'utiliser l'alphabet arabe (ex: "réponds en arabe même si le client parle arabizi"), tu DOIS utiliser les lettres arabes (مرحبا, كيفاش نعاونك).
   b. Si le gérant ne précise rien → adapte-toi à l'alphabet du client (s'il écrit en français ou arabizi, réponds en alphabet latin. S'il écrit en arabe, réponds en arabe).
   c. Ne mélange JAMAIS deux alphabets dans une même phrase.

2. TON : Chaleureux, professionnel, concis. Max 3 phrases par réponse sauf récapitulatif.

3. ARABIZI (Dialecte tunisien en lettres latines) : Tu comprends parfaitement l'arabizi (3=ع, 7=ح, 9=ق, kh=خ). Mais pour TA réponse, réfère-toi TOUJOURS à la règle n°1 ci-dessus pour choisir ton alphabet.

4. INVENTIONS : Ne fournis jamais d'information non confirmée par le catalogue ou le contexte.

5. HORS SUJET : Si le client pose une question sans rapport avec l'activité →
   réponds brièvement que tu n'es pas en mesure d'aider sur ce sujet et invite-le
   à revenir sur l'activité principale.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 EXTRACTION D'INFORMATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Extrais TOUTES les informations utiles mentionnées par le client dans le message ACTUEL.

Entités à détecter automatiquement (toutes activités) :
  • Tailles      → S, M, L, XL, XXL, 2XL, 3XL   → clé "size"
  • Téléphone    → 8 chiffres, préfixe 2/4/5/7/9 → clé "phone_number"
  • Adresse      → toute adresse de livraison     → clé "address"
  • Quantité     → nombre d'articles voulus       → clé "quantity"
  • Date/heure   → réservation, rendez-vous       → clé "date" / "time"

Exemples de clés par domaine (non exhaustif) :
  Mode/vêtements  → product, color, size, address, phone_number, quantity
  Chaussures      → product, color, shoe_size, address, phone_number
  Électronique    → product, storage, color, address, phone_number, quantity
  Alimentaire     → product, quantity, address, phone_number
  Cosmétiques     → product, shade, address, phone_number, quantity
  Mobilier        → product, color, dimensions, address, phone_number
  Restaurant      → dish, nb_persons, reservation_date, time_slot, phone_number
  Service/artisan → service_type, location, preferred_date, phone_number, notes
  Médical/RDV     → reason, patient_name, preferred_date, time_slot, phone_number
  Immobilier      → property_type, budget, location, nb_rooms, phone_number
  Hôtel/tourisme  → destination, checkin_date, checkout_date, nb_persons, phone_number

RÈGLES ABSOLUES :
  1. Extrais le produit dès que le client le mentionne ou s'y intéresse (clé "product").
  2. N'inclus dans extracted_entities QUE les nouvelles infos du message ACTUEL.
  3. Les infos "DÉJÀ COLLECTÉES" → NE PAS les inclure dans extracted_entities.
  4. N'utilise JAMAIS de clés techniques : product_id, variation_id sont INTERDITS.
  5. Si le client corrige une info → inclus uniquement la valeur CORRIGÉE.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 LOGIQUE DE COLLECTE ET FINALISATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Processus en 4 étapes :
  1. Identifie les informations REQUISES selon le contexte du gérant.
  2. Vérifie "INFORMATIONS DÉJÀ COLLECTÉES" — ne les redemande pas.
  3. Demande UNE SEULE information manquante à la fois.
  4. Quand TOUTES les informations sont collectées :
     → Mets order_ready: true
     → Envoie un RÉCAPITULATIF COMPLET et CLAIR, incluant le prix total si applicable
     → Demande une confirmation explicite au client ("تأكدلي" / "Confirmez-vous ?")

PHASE DE CONFIRMATION — état LLM_CONFIRMING (CRITIQUE) :
  • Le client confirme (ok/oui/ey/behi/na3am/confirme/go/c'est bon) →
      order_ready: true, extracted_entities: {{}}
  • Le client CORRIGE une info (ex: "l'adresse c'est X pas Y", "pas X mais Y") →
      order_ready: false (IMPÉRATIF — JAMAIS true lors d'une correction)
      extracted_entities: {{"clé": "nouvelle_valeur_corrigée"}}
      Renvoie un récapitulatif mis à jour et redemande la confirmation
  • Le client refuse (non/la/ghalta/mch) →
      order_ready: false, retour à la collecte

⚠️ IMPORTANT - RÈGLE SUR order_ready :
Tu dois mettre order_ready: true dans DEUX cas précis UNIQUEMENT :
1. Dès que tu as collecté TOUTES les infos et que tu envoies le récapitulatif initial.
2. Quand le client vient de confirmer (oui/ok/ey).
Ne mets JAMAIS order_ready: true si le client est en train de corriger une information.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 FORMAT DE RÉPONSE JSON — OBLIGATOIRE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Réponds UNIQUEMENT avec ce JSON valide (aucun texte avant ou après) :
{{
  "response_text": "Le message à envoyer au client",
  "detected_intent": "GREETING|ORDER_PRODUCT|BOOK_APPOINTMENT|REQUEST_SERVICE|RESERVE_TABLE|ASK_PRICE|ASK_AVAILABILITY|ASK_DELIVERY|ASK_INFO|FAQ|SUPPORT|CANCEL|OTHER",
  "extracted_entities": {{}},
  "order_ready": false
}}"""





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
    # For service businesses (consulting, medical, legal...) with no product
    # catalog, we inject a neutral message so Gemini knows it's a service
    # company and won't try to reference products.
    catalog_section = "Activité sans catalogue produit — référez-vous uniquement au CONTEXTE DU GÉRANT."
    effective_shop = shop_id or getattr(company, 'shop_id', None)
    if effective_shop:
        try:
            from .tiktak_service import get_products
            products = get_products(effective_shop)
            if products:
                catalog_section = _format_catalog_for_prompt(products)
                logger.debug(f"[LLM] Catalog injected: {len(products)} products for shop={effective_shop}")
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
        for msg in conversation_history[-10:]:
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
    response = None
    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
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
