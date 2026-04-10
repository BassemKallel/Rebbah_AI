"""
template_service.py — Response templates lookup service

Lookup chain (fastest to slowest):
  1. Redis cache       — key: tmpl:{shop}:{lang}:{type}:{intent}  TTL=300s
  2. DB shop-specific  — ResponseTemplate(shop_id=shop_id)
  3. DB system default — ResponseTemplate(shop_id=NULL, is_default=True)
  4. Python fallback   — response_templates.py (if DB down)

Pre-warming:
  prewarm_order_templates(shop_id) loads the full ORDER_PRODUCT / INFORM_INFO
  template set into Redis in ONE bulk DB query when a new conversation starts.
  Templates for simple one-shot intents (GREETING, NOISE, etc.) are excluded
  because they are only called once per session and do not justify pre-loading.
"""
import logging
from django.core.cache import cache
from django.db.models import Q

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # 5 minutes

# ── Pre-warm configuration ─────────────────────────────────────────────────
# Templates loaded at conversation start — covers the full ORDER_PRODUCT and
# INFORM_INFO flows including all missing-entity prompts and stock messages.
# Intentionally excludes single-shot intents (GREETING, NOISE, CANCEL_ORDER,
# COMPLAINT, TRACK_ORDER, etc.) that are used at most once per session.
_PREWARM_TEMPLATES = [
    # Missing entity prompts — asked repeatedly until all entities collected
    ("missing_entity", "color"),
    ("missing_entity", "size"),
    ("missing_entity", "address"),
    ("missing_entity", "phone_number"),
    ("missing_entity", "product"),
    ("missing_entity", "quantity"),
    # Out-of-stock messages — may appear multiple times during a flow
    ("out_of_stock", "default"),
    ("out_of_stock", "available"),
    ("out_of_stock", "sizes"),
    ("out_of_stock", "colors"),
    # Misc helpers used inside ORDER_PRODUCT / INFORM_INFO branches
    ("misc", "missing_entity_default"),
    ("misc", "inform_info_default"),
    ("misc", "inform_product_default"),
    ("misc", "stock_check_error"),
    # Order confirmation
    ("order_confirmed", "with_ref"),
    ("order_confirmed", "no_ref"),
    # Direct response templates used inside active order flow
    ("response", "INFORM_INFO"),
    ("response", "ASK_PRICE"),
    ("response", "ASK_AVAILABILITY"),
]
_PREWARM_LANGUAGES = ["FR", "AR", "EN"]


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


def prewarm_order_templates(shop_id: str) -> None:
    """
    Pre-load ORDER_PRODUCT / INFORM_INFO templates into Redis in one bulk DB query.

    Called once when a NEW conversation is created so that every subsequent
    get_template() call during that session is a pure Redis HIT.

    Strategy:
      1. Compute the full set of Redis keys to pre-warm.
      2. Ask Redis which keys are MISSING (cache.get_many — one round-trip).
      3. Fetch all missing templates from PostgreSQL in a SINGLE bulk query
         using IN clauses on (language, template_type, intent).
         Shop-specific rows override system defaults.
      4. For any template not found in DB, fall back to the Python dict.
      5. Write everything to Redis at once (cache.set_many — one round-trip).
    """
    # ── 1. Build full key map ──────────────────────────────────────────────
    all_keys: dict[str, tuple[str, str, str]] = {
        _cache_key(shop_id, lang, ttype, intent): (lang, ttype, intent)
        for lang in _PREWARM_LANGUAGES
        for ttype, intent in _PREWARM_TEMPLATES
    }

    # ── 2. Identify which keys are not yet cached ──────────────────────────
    already_cached = cache.get_many(list(all_keys.keys()))
    missing: list[tuple[str, str, str]] = [
        combo for key, combo in all_keys.items()
        if key not in already_cached
    ]

    if not missing:
        logger.debug(f"[TEMPLATE_SERVICE] Pre-warm skipped — all {len(all_keys)} keys already cached for shop={shop_id}")
        return

    # ── 3. Bulk DB query for all missing combos ────────────────────────────
    missing_langs   = {c[0] for c in missing}
    missing_types   = {c[1] for c in missing}
    missing_intents = {c[2] for c in missing}

    try:
        from apps.crm.models import ResponseTemplate

        rows = ResponseTemplate.objects.filter(
            Q(shop_id=shop_id) | Q(shop_id=None, is_default=True),
            language__in=missing_langs,
            template_type__in=missing_types,
            intent__in=missing_intents,
        ).values("shop_id", "language", "template_type", "intent", "text")

        # Index by (lang, type, intent) — shop-specific wins over system default
        db_index: dict[tuple[str, str, str], str] = {}
        for row in rows:
            key = (row["language"], row["template_type"], row["intent"])
            if key not in db_index or row["shop_id"] is not None:
                db_index[key] = row["text"]

    except Exception as exc:
        logger.warning(f"[TEMPLATE_SERVICE] Pre-warm DB query failed: {exc} — skipping")
        return

    # ── 4. Build cache payload (DB result + Python fallback for gaps) ──────
    to_cache: dict[str, str] = {}
    for lang, ttype, intent in missing:
        text = db_index.get((lang, ttype, intent)) or _python_fallback(ttype, intent, lang)
        if text is not None:
            to_cache[_cache_key(shop_id, lang, ttype, intent)] = text

    # ── 5. Write to Redis in one round-trip ───────────────────────────────
    if to_cache:
        cache.set_many(to_cache, CACHE_TTL)
        logger.info(
            f"[TEMPLATE_SERVICE] Pre-warmed {len(to_cache)} templates "
            f"for shop={shop_id} ({len(already_cached)} were already cached)"
        )


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
