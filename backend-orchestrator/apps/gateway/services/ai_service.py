"""
ai_service.py — Layer 1: External Vision API client

Responsibilities:
- Call Vision service for Image-to-Image similarity search (Visual RAG)
- Supports both URL-based and file-upload-based image queries
"""
import logging
import requests
from django.conf import settings


logger = logging.getLogger(__name__)

VISION_URL      = settings.VISION_SERVICE_URL.rstrip('/') + settings.VISION_SEARCH_PATH
VISION_URL_FILE = settings.VISION_SERVICE_URL.rstrip('/') + '/search-similar-upload'
REQUEST_TIMEOUT = settings.EXTERNAL_REQUEST_TIMEOUT


def call_vision(shop_id: str, image_url: str = None, image_file=None, limit: int = 3) -> list | None:
    """
    Call the vision-service to find the most similar products in the vector DB (Visual RAG).

    Returns a list of dicts with {item_id, image_url, metadata} on success, None on failure.
    """
    try:
        if image_file:
            res = requests.post(
                VISION_URL_FILE,
                files={"image": (image_file.name, image_file.read(), image_file.content_type)},
                data={"shop_id": shop_id, "limit": limit},
                timeout=REQUEST_TIMEOUT,
            )
        elif image_url:
            res = requests.post(
                VISION_URL,
                json={"image_url": image_url, "limit": limit, "shop_id": shop_id},
                timeout=REQUEST_TIMEOUT,
            )
        else:
            return None

        if res.status_code == 200:
            data = res.json()
            results = data.get("results", [])
            logger.debug(f"[VISION] Found {len(results)} matches via RAG.")
            return results
        else:
            logger.error(f"[VISION] HTTP {res.status_code}")
    except requests.RequestException as e:
        logger.error(f"[VISION] Connection error: {e}")

    return None


