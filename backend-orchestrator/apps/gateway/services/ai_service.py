"""
ai_service.py — Layer 1: External AI API clients

Responsibilities:
- Call NLU service (intent + entity extraction)
- Call Vision service (image similarity search)
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

NLU_URL         = settings.NLU_SERVICE_URL.rstrip('/') + settings.NLU_PREDICT_PATH
VISION_URL      = settings.VISION_SERVICE_URL.rstrip('/') + settings.VISION_SEARCH_PATH
VISION_URL_FILE = settings.VISION_SERVICE_URL.rstrip('/') + '/search-similar-upload'
REQUEST_TIMEOUT = settings.EXTERNAL_REQUEST_TIMEOUT


def call_vision(shop_id: str, image_url: str = None, image_file=None) -> dict | None:
    """
    Call the vision-service to find the most similar product in the vector DB.

    Returns a dict with {product_id, variation_id, image_url} on success, None on failure.
    """
    try:
        if image_file:
            res = requests.post(
                VISION_URL_FILE,
                files={"image": (image_file.name, image_file.read(), image_file.content_type)},
                data={"shop_id": shop_id, "limit": 1},
                timeout=REQUEST_TIMEOUT,
            )
        elif image_url:
            res = requests.post(
                VISION_URL,
                json={"image_url": image_url, "limit": 1, "shop_id": shop_id},
                timeout=REQUEST_TIMEOUT,
            )
        else:
            return None

        if res.status_code == 200:
            data = res.json()
            results = data.get("results", [])
            if results:
                top = results[0]
                logger.debug(f"[VISION] product_id={top['product_id']} variation_id={top.get('variation_id')}")
                return {
                    "product_id": top["product_id"],
                    "variation_id": top.get("variation_id"),
                    "image_url": top.get("image_url"),
                    "similarity_score": top.get("similarity_score"),
                }
        else:
            logger.error(f"[VISION] HTTP {res.status_code}")
    except requests.RequestException as e:
        logger.error(f"[VISION] Connection error: {e}")

    return None


def call_nlu(text: str) -> dict:
    """
    Call the NLU service (TunBERT intent + GLiNER entities).

    Returns a dict:
    {
        "intent":  str,         # e.g. "ORDER_PRODUCT"
        "entities": dict,       # {label: text} (filtered by caller)
        "raw_entities": list,   # [{text, label, score, start, end}, ...]
        "error": bool
    }
    """
    result = {"intent": "UNKNOWN", "confidence_score": None, "raw_entities": [], "error": False}
    try:
        res = requests.post(NLU_URL, json={"message": text}, timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            data = res.json()
            intent_data = data.get("intent", {})
            logger.debug(f"[NLU] raw intent payload: {intent_data}")
            result["intent"]           = intent_data.get("intent", "UNKNOWN")
            # Try common field names for the confidence score
            result["confidence_score"] = (
                intent_data.get("score")
                or intent_data.get("confidence")
                or intent_data.get("probability")
                or intent_data.get("prob")
            )
            result["raw_entities"]     = data.get("entities", [])
        else:
            logger.error(f"[NLU] HTTP {res.status_code}")
            result["error"] = True
    except requests.RequestException as e:
        logger.error(f"[NLU] Connection error: {e}")
        result["error"] = True

    return result
