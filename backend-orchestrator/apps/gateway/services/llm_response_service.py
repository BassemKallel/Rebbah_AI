"""
llm_response_service.py — LLM Direct Response Mode

When a Company has response_mode='llm', this service replaces the entire
NLU pipeline. Gemini generates a natural-language response using the
company's llm_context, and can also create orders when all entities
are collected.

Key differences from gemini_service.py (NLU fallback):
- gemini_service → returns structured intent+entities for the NLU pipeline
- llm_response_service → returns a direct response to the client + optional order data

Each company uses its OWN Gemini API key (isolation of consumption).
"""
import json
import logging

logger = logging.getLogger(__name__)

# ── Prompt template ──────────────────────────────────────────────────────────

SYSTEM_PROMPT_LLM_MODE = """Tu es l'assistant IA de la boutique "{company_name}".

--- CONTEXTE BOUTIQUE ---
{llm_context}

--- ENTITÉS DÉJÀ COLLECTÉES (NE PAS RE-DEMANDER CES INFORMATIONS) ---
{collected_entities_str}

--- RÈGLES CRITIQUES ---
1. Tu comprends parfaitement le dialecte tunisien (Arabizi, Derja, mélange arabe/français).
2. Si le client écrit en arabe ou en arabizi → réponds en ARABE TUNISIEN (Derja).
3. Si le client écrit en français → réponds en FRANÇAIS.
4. Ne mélange JAMAIS les deux langues dans une même réponse.
5. Sois professionnel, sympathique et concis (2-3 phrases max).
6. Ne réponds qu'aux sujets liés à la boutique.
7. Ne mentionne JAMAIS un produit absent du CONTEXTE BOUTIQUE ci-dessus.

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
4. Dans extracted_entities → mets UNIQUEMENT les nouvelles infos du message ACTUEL (pas les anciennes)
5. CONDITION order_ready=true : product + address + phone_number sont tous présents
   (soit dans ENTITÉS DÉJÀ COLLECTÉES, soit dans ce message)
   → Quand cette condition est remplie : mets order_ready=true ET envoie un récapitulatif complet de confirmation"""


def generate_llm_response(
    text: str,
    company,
    conversation_history: list = None,
    current_context: dict = None,
) -> dict:
    """
    Generate a direct response using the company's Gemini API key.

    Args:
        text: Client's message
        company: Company model instance (with gemini_api_key, llm_context, name)
        conversation_history: List of recent messages [{role, text, intent?}]
        current_context: Accumulated entities from previous messages

    Returns:
        {
            "response_text": str,
            "detected_intent": str,
            "extracted_entities": dict,
            "order_ready": bool,
            "error": bool,
        }
    """
    result = {
        "response_text": "",
        "detected_intent": "OTHER",
        "extracted_entities": {},
        "order_ready": False,
        "error": False,
    }

    # ── Validate API key ──────────────────────────────────────────────────
    api_key = company.gemini_api_key
    if not api_key:
        logger.error(f"[LLM] No Gemini API key for company={company.shop_id}")
        result["response_text"] = "Service temporairement indisponible. Veuillez réessayer plus tard."
        result["error"] = True
        return result

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
        raw_text = response.text.strip()
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

        logger.info(
            f"[LLM] shop={company.shop_id} intent={result['detected_intent']} "
            f"new_entities={list(result['extracted_entities'].keys())} "
            f"collected={list(collected.keys())} "
            f"order_ready={result['order_ready']}"
        )

    except json.JSONDecodeError as e:
        logger.error(f"[LLM] JSON parse error for shop={company.shop_id}: {e}")
        result["response_text"] = "Désolé, une erreur est survenue. Veuillez réessayer."
        result["error"] = True
    except ImportError:
        logger.error("[LLM] google-genai package not installed")
        result["response_text"] = "Service temporairement indisponible."
        result["error"] = True
    except Exception as e:
        logger.error(f"[LLM] API error for shop={company.shop_id}: {e}")
        result["response_text"] = "Désolé, une erreur est survenue. Veuillez réessayer."
        result["error"] = True

    return result
