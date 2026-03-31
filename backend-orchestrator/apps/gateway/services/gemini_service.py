"""
gemini_service.py — Gemini NLU Fallback Service

Responsibilities:
- Provide fallback NLU (intent classification + entity extraction)
  when TunBERT is down or returns low-confidence results.
- Return the same dict format as ai_service.call_nlu() for seamless
  pipeline integration.
"""
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# ── 17 TunBERT intents (must match nlu-service/config.py) ─────────────────
VALID_INTENTS = {
    "ASK_ADVICE", "ASK_AVAILABILITY", "ASK_DELIVERY", "ASK_DETAILS",
    "ASK_DISCOUNT", "ASK_LOCATION", "ASK_PRICE", "CANCEL_ORDER",
    "CHECK_PACKAGE", "COMPLAINT", "CONFIRM_DENY", "ECHANGE",
    "GREETING", "INFORM_INFO", "NOISE", "ORDER_PRODUCT", "TRACK_ORDER",
}

# ── 7 GLiNER entity labels ────────────────────────────────────────────────
VALID_ENTITY_LABELS = [
    "product", "color", "size", "address", "phone_number", "quantity", "client_name"
]

SYSTEM_PROMPT = """Tu es un système NLU pour un chatbot e-commerce tunisien.
Le texte utilisateur est en dialecte tunisien (mélange arabe/français/arabizi).

Classifie l'intent parmi EXACTEMENT ces 17 labels :
ASK_ADVICE, ASK_AVAILABILITY, ASK_DELIVERY, ASK_DETAILS, ASK_DISCOUNT,
ASK_LOCATION, ASK_PRICE, CANCEL_ORDER, CHECK_PACKAGE, COMPLAINT,
CONFIRM_DENY, ECHANGE, GREETING, INFORM_INFO, NOISE, ORDER_PRODUCT, TRACK_ORDER

ATTENTION CRITIQUE :
- CANCEL_ORDER = l'utilisateur veut EXPLICITEMENT annuler sa commande.
- "non nheb X" (non, je veux X) n'est PAS une annulation. C'est INFORM_INFO.
- "ma nebich" / "nhabbi nalghilha" = CANCEL_ORDER.

Extrais les entités suivantes si présentes dans le texte :
product, color, size, address, phone_number, quantity, client_name

Réponds UNIQUEMENT en JSON avec cette structure exacte :
{
  "intent": "ORDER_PRODUCT",
  "confidence": 0.92,
  "entities": [
    {"text": "pull noir", "label": "product", "score": 0.95, "start": 0, "end": 9}
  ]
}"""


def call_gemini_nlu(text: str, conversation_history: list = None) -> dict:
    """
    Call Gemini API as NLU fallback.

    Returns the same format as ai_service.call_nlu():
    {
        "intent": str,
        "confidence_score": float | None,
        "raw_entities": list,
        "error": bool,
        "fallback_used": bool,
    }
    """
    result = {
        "intent": "NOISE",
        "confidence_score": None,
        "raw_entities": [],
        "error": False,
        "fallback_used": True,
    }

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        logger.error("[GEMINI] No API key configured (GEMINI_API_KEY)")
        result["error"] = True
        return result

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        # Build prompt with conversation context
        history_str = ""
        if conversation_history:
            lines = []
            for msg in conversation_history[-5:]:
                role = msg["role"].upper()
                intent_tag = f" [{msg['intent']}]" if msg.get("intent") else ""
                lines.append(f"{role}{intent_tag}: {msg['text']}")
            history_str = "\nHistorique récent de la conversation:\n" + "\n".join(lines) + "\n\n"

        contents = f"{history_str}Message à classifier: {text}"

        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=contents,
            config={
                "system_instruction": SYSTEM_PROMPT,
                "response_mime_type": "application/json",
                "temperature": 0.1,
            },
        )

        # Parse JSON response
        raw_text = response.text.strip()
        data = json.loads(raw_text)

        # Validate intent
        intent = data.get("intent", "NOISE")
        if intent not in VALID_INTENTS:
            logger.warning(f"[GEMINI] Invalid intent '{intent}' — defaulting to NOISE")
            intent = "NOISE"

        result["intent"] = intent
        result["confidence_score"] = data.get("confidence")

        # Validate and normalize entities
        raw_entities = data.get("entities", [])
        validated_entities = []
        for ent in raw_entities:
            if isinstance(ent, dict) and ent.get("label") in VALID_ENTITY_LABELS:
                validated_entities.append({
                    "text": ent.get("text", ""),
                    "label": ent["label"],
                    "score": ent.get("score", 0.8),
                    "start": ent.get("start", 0),
                    "end": ent.get("end", 0),
                })
        result["raw_entities"] = validated_entities

        logger.info(
            f"[GEMINI] intent={intent} confidence={result['confidence_score']} "
            f"entities={[e['label'] for e in validated_entities]}"
        )

    except json.JSONDecodeError as e:
        logger.error(f"[GEMINI] JSON parse error: {e}")
        result["error"] = True
    except ImportError:
        logger.error("[GEMINI] google-genai package not installed")
        result["error"] = True
    except Exception as e:
        logger.error(f"[GEMINI] API error: {e}")
        result["error"] = True

    return result
