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

--- RÈGLES CRITIQUES ---
1. Tu comprends parfaitement le dialecte tunisien (Arabizi, Derja, mélange arabe/français).
2. Si le client écrit en arabe ou en arabizi → réponds en ARABE PUR (عربية مبسطة واضحة).
3. Si le client écrit en français → réponds en FRANÇAIS.
4. Ne mélange JAMAIS les deux langues dans une même réponse.
5. Sois professionnel, sympathique et serviable.
6. Ne réponds qu'aux sujets liés à la boutique. Pour tout hors-sujet, redirige poliment.
7. Si tu ne connais pas la réponse, dis-le poliment au lieu d'inventer.

--- CONTEXTE DE LA CONVERSATION ---
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
    "quantity": null,
    "client_name": null
  }},
  "order_ready": false
}}

--- LOGIQUE DE COMMANDE ---
Quand le client veut commander un produit :
1. Collecte TOUTES ces informations une par une : product, color, size, address, phone_number
2. Pour chaque info manquante, demande-la poliment dans response_text
3. Mets les infos déjà collectées dans extracted_entities (valeur réelle, pas null)
4. Quand TOUTES les 5 informations sont collectées → mets "order_ready": true
5. Si order_ready=true, confirme la commande dans response_text avec un récapitulatif

IMPORTANT : Remplis extracted_entities avec les nouvelles infos de CE message uniquement.
Les infos déjà collectées dans les messages précédents sont dans le CONTEXTE ci-dessus."""


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

    # ── Build conversation context string ─────────────────────────────────
    context_parts = []
    if current_context:
        collected = {k: v for k, v in current_context.items() if not k.startswith('_')}
        if collected:
            context_parts.append("Entités déjà collectées : " + json.dumps(collected, ensure_ascii=False))

    if conversation_history:
        lines = []
        for msg in conversation_history[-8:]:  # Last 8 messages
            role = "CLIENT" if msg.get("role") == "user" else "BOT"
            lines.append(f"{role}: {msg.get('text', '')}")
        if lines:
            context_parts.append("Historique récent :\n" + "\n".join(lines))

    conversation_context = "\n\n".join(context_parts) if context_parts else "Première interaction avec ce client."

    # ── Build prompt ──────────────────────────────────────────────────────
    system_prompt = SYSTEM_PROMPT_LLM_MODE.format(
        company_name=company.name,
        llm_context=company.llm_context or "Aucun contexte spécifique fourni pour cette boutique.",
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
                "temperature": 0.3,
            },
        )

        # ── Parse response ────────────────────────────────────────────────
        raw_text = response.text.strip()
        data = json.loads(raw_text)

        result["response_text"] = data.get("response_text", "")
        result["detected_intent"] = data.get("detected_intent", "OTHER")
        result["order_ready"] = bool(data.get("order_ready", False))

        # Extract non-null entities
        raw_entities = data.get("extracted_entities", {})
        if isinstance(raw_entities, dict):
            result["extracted_entities"] = {
                k: v for k, v in raw_entities.items()
                if v is not None and v != "" and v != "null"
            }

        logger.info(
            f"[LLM] shop={company.shop_id} intent={result['detected_intent']} "
            f"entities={list(result['extracted_entities'].keys())} "
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
