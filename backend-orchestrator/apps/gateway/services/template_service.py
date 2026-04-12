"""
template_service.py — Response templates lookup service

Lookup chain (fastest to slowest):
  1. Redis cache       — key: tmpl:{shop}:{lang}:{type}:{intent}  TTL=300s
  2. DB shop-specific  — ResponseTemplate(shop_id=shop_id)
  3. DB system default — ResponseTemplate(shop_id=NULL, is_default=True)
  4. Python fallback   — response_templates.py (if DB down)
"""
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # 5 minutes


def _cache_key(shop_id, language, template_type, intent):
    shop = shop_id or "default"
    return f"tmpl:{shop}:{language}:{template_type}:{intent}"


def get_template(template_type: str, intent: str, language: str,
                 shop_id: str = None) -> str | None:
    """
    Retrieve a response template text.
    Returns None if not found anywhere (caller should handle gracefully).
    """
    key = _cache_key(shop_id, language, template_type, intent)

    # ── 1. Redis cache ──────────────────────────────────────────────────
    cached = cache.get(key)
    if cached is not None:
        return cached

    # ── 2 & 3. Database lookup ──────────────────────────────────────────
    try:
        from apps.crm.models import ResponseTemplate

        # Lookup 2: shop-specific
        if shop_id:
            tmpl = ResponseTemplate.objects.filter(
                shop_id=shop_id,
                language=language,
                template_type=template_type,
                intent=intent,
            ).first()
            if tmpl:
                cache.set(key, tmpl.text, CACHE_TTL)
                return tmpl.text

        # Lookup 3: system default
        tmpl = ResponseTemplate.objects.filter(
            shop_id=None,
            is_default=True,
            language=language,
            template_type=template_type,
            intent=intent,
        ).first()
        if tmpl:
            cache.set(key, tmpl.text, CACHE_TTL)
            return tmpl.text

    except Exception as e:
        logger.warning(f"[TEMPLATE_SERVICE] DB lookup failed: {e} — using Python fallback")

    # ── 4. Python fallback (response_templates.py) ─────────────────────
    return _python_fallback(template_type, intent, language)


def invalidate_template_cache(shop_id, language, template_type, intent):
    """Invalidate a specific cache entry — called from Admin post_save signal."""
    key = _cache_key(shop_id, language, template_type, intent)
    cache.delete(key)
    # Also invalidate the default key in case client was using the default
    default_key = _cache_key(None, language, template_type, intent)
    cache.delete(default_key)
    logger.info(f"[TEMPLATE_SERVICE] Cache invalidated: {key}")


# ── Pre-warm ORDER_PRODUCT / INFORM_INFO templates ─────────────────────────
# Intents used in ORDER_PRODUCT and INFORM_INFO flows
_PREWARM_INTENTS = {
    "response": ["ORDER_PRODUCT", "INFORM_INFO", "ASK_AVAILABILITY"],
    "missing_entity": ["color", "size", "quantity", "phone", "address", "name"],
    "out_of_stock": ["default", "available", "sizes", "colors"],
    "order_confirmed": ["with_ref", "no_ref"],
    "misc": ["missing_entity_default", "inform_info_default", "inform_product_default"],
}
_PREWARM_LANGUAGES = ["fr", "ar", "en"]


def prewarm_order_templates(shop_id: str | None = None):
    """
    Pre-load ORDER flow templates into Redis in a single DB query + set_many.
    Called once per new conversation. Non-blocking: failures are caught by the caller.
    """
    try:
        from apps.crm.models import ResponseTemplate

        qs = ResponseTemplate.objects.all()
        if shop_id:
            # Fetch both shop-specific and system defaults in one query
            from django.db.models import Q
            qs = qs.filter(Q(shop_id=shop_id) | Q(shop_id=None, is_default=True))
        else:
            qs = qs.filter(shop_id=None, is_default=True)

        to_cache = {}
        for tmpl in qs:
            key = _cache_key(tmpl.shop_id, tmpl.language, tmpl.template_type, tmpl.intent)
            to_cache[key] = tmpl.text

        if to_cache:
            cache.set_many(to_cache, CACHE_TTL)
            logger.info(f"[TEMPLATE_SERVICE] Pre-warmed {len(to_cache)} templates for shop={shop_id}")

    except Exception as e:
        logger.warning(f"[TEMPLATE_SERVICE] prewarm_order_templates failed: {e}")


# ── Python fallback (exact copies from response_templates.py) ──────────────
def _python_fallback(template_type: str, intent: str, language: str) -> str | None:
    from apps.gateway.response_templates import (
        TEMPLATES, MISSING_ENTITY_TEMPLATES, OUT_OF_STOCK_TEMPLATE,
        OUT_OF_STOCK_AVAILABLE, OUT_OF_STOCK_SIZES, OUT_OF_STOCK_COLORS,
        ORDER_CONFIRMED_TEMPLATE, ORDER_CONFIRMED_NO_REF_TEMPLATE,
        DISAMBIGUATION_TEMPLATE, MISSING_ENTITY_DEFAULT, INFORM_INFO_DEFAULT,
        INFORM_PRODUCT_DEFAULT, ASK_AVAILABILITY_DEFAULT, ASK_PRICE_DEFAULT,
        NOISE_DEFAULT, STOCK_CHECK_ERROR,
    )

    if template_type == "response":
        return TEMPLATES.get(language, {}).get(intent)

    if template_type == "missing_entity":
        return MISSING_ENTITY_TEMPLATES.get(language, {}).get(intent)

    if template_type == "out_of_stock":
        mapping = {
            "default":    OUT_OF_STOCK_TEMPLATE,
            "available":  OUT_OF_STOCK_AVAILABLE,
            "sizes":      OUT_OF_STOCK_SIZES,
            "colors":     OUT_OF_STOCK_COLORS,
        }
        return mapping.get(intent, {}).get(language)

    if template_type == "order_confirmed":
        mapping = {
            "with_ref": ORDER_CONFIRMED_TEMPLATE,
            "no_ref":   ORDER_CONFIRMED_NO_REF_TEMPLATE,
        }
        return mapping.get(intent, {}).get(language)

    if template_type == "disambiguation":
        return DISAMBIGUATION_TEMPLATE.get(language)

    if template_type == "misc":
        mapping = {
            "missing_entity_default":   MISSING_ENTITY_DEFAULT,
            "inform_info_default":       INFORM_INFO_DEFAULT,
            "inform_product_default":    INFORM_PRODUCT_DEFAULT,
            "ask_availability_default":  ASK_AVAILABILITY_DEFAULT,
            "ask_price_default":         ASK_PRICE_DEFAULT,
            "noise_default":             NOISE_DEFAULT,
            "stock_check_error":         STOCK_CHECK_ERROR,
        }
        return mapping.get(intent, {}).get(language)

    return None
