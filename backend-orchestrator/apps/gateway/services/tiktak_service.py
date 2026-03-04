"""
tiktak_service.py — Layer 2: TikTak product catalog access

Responsibilities:
- Fetch & cache the product list from the TikTak API
- Normalise the raw API response into the internal format
- Match a product name or image ID against the catalog
"""
import logging
import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

TIKTAK_API_PRODUCTS_URL = settings.TIKTAK_API_BASE_URL.rstrip('/') + settings.TIKTAK_API_PRODUCTS_PATH
REQUEST_TIMEOUT = settings.EXTERNAL_REQUEST_TIMEOUT


# ─── Normalisation ──────────────────────────────────────────────────────────

def normalize_tiktak_products(results: list) -> list:
    """
    Convert the raw TikTak API response into the internal standard format:

    {
        "id":         <int>,
        "name":       <str>,
        "base_price": <str>,
        "variations": [
            {
                "id":             <int>,
                "color":          <str>,
                "size":           <str>,
                "image":          <str>,
                "stock_quantity": <int>,
            }
        ]
    }
    """
    normalized = []
    for p in results:
        if p.get("parent") is not None:
            continue

        variations = []
        for decl in p.get("declinaisons", []):
            color = ""
            size  = ""
            for attr in decl.get("_attributs", []):
                if attr.get("is_color"):
                    color = attr.get("value", "")
                else:
                    size = attr.get("value", "")
            variations.append({
                "id":             decl["id"],
                "color":          color,
                "size":           size,
                "image":          decl.get("photo", ""),
                "stock_quantity": decl.get("stock", 0),
            })

        if not variations:
            variations.append({
                "id":             p["id"],
                "color":          "",
                "size":           "",
                "image":          p.get("photo", ""),
                "stock_quantity": p.get("stock", 0),
            })

        normalized.append({
            "id":         p["id"],
            "name":       p["name"],
            "base_price": str(p.get("price", "0")),
            "variations": variations,
        })

    return normalized


# ─── Fetching ────────────────────────────────────────────────────────────────

def get_products(shop_id: str) -> list:
    """
    Return the full product list for a shop, using Redis cache when available.
    Paginates through all TikTak API pages (max 10).
    """
    cache_key = f"tiktak_products:{shop_id}"
    products = cache.get(cache_key)

    if products is None:
        logger.info(f"[TIKTAK] cache miss shop_id={shop_id}")
        api_headers = {"Authorization": f"Bearer {settings.TIKTAK_API_TOKEN}"}
        all_results = []
        next_url    = TIKTAK_API_PRODUCTS_URL
        params      = {"company": shop_id}
        page_count  = 0

        while next_url and page_count < 10:
            try:
                if page_count == 0:
                    resp = requests.get(next_url, headers=api_headers, params=params, timeout=REQUEST_TIMEOUT)
                else:
                    resp = requests.get(next_url, headers=api_headers, timeout=REQUEST_TIMEOUT)

                if resp.status_code == 200:
                    data = resp.json()
                    all_results.extend(data.get("results", []))
                    next_url = data.get("next")
                    page_count += 1
                else:
                    logger.error(f"[TIKTAK] HTTP {resp.status_code}")
                    break
            except requests.RequestException as e:
                logger.error(f"[TIKTAK] Connection error: {e}")
                break

        products = normalize_tiktak_products(all_results)
        cache.set(cache_key, products, settings.PRODUCTS_CACHE_TTL)
        logger.info(f"[TIKTAK] {len(products)} products cached for shop={shop_id}")
    else:
        logger.debug(f"[TIKTAK] cache hit shop_id={shop_id}")

    return products or []


# ─── Matching ────────────────────────────────────────────────────────────────

def find_product(products: list, prod_name: str, vision_variation_id: str = None) -> tuple:
    """
    Try to match a product from the catalog.

    - If prod_name starts with "Article_From_Image_<id>", do an exact ID match.
    - Otherwise, do a keyword match against product names.

    Returns (matched_product, color_from_variation, candidates_list).
    - matched_product: the full product dict, or None
    - color_from_variation: pre-filled color if image search resolved a variation
    - candidates_list: list of products when keyword match is ambiguous (len > 1)
    """
    matched_product     = None
    color_from_vision   = None
    candidates          = []

    if prod_name.startswith("Article_From_Image_"):
        target_id = prod_name.split("Article_From_Image_")[1]
        eff_id    = str(target_id).lower()

        for p in products:
            p_id = str(p.get("id", "")).lower()
            if p_id == eff_id:
                matched_product = p
                # Pre-fill color from the identified variation
                if vision_variation_id:
                    for v in p.get("variations", []):
                        if str(v.get("id", "")).lower() == str(vision_variation_id).lower():
                            color_from_vision = v["color"]
                            break
                break
            else:
                # Fallback: target_id might be a variation_id
                for v in p.get("variations", []):
                    if str(v.get("id", "")).lower() == eff_id:
                        matched_product   = p
                        color_from_vision = v["color"]
                        break
                if matched_product:
                    break

    else:
        # Keyword match
        candidates = [
            p for p in products
            if p["name"].lower() in prod_name.lower()
            or prod_name.lower() in p["name"].lower()
        ]
        if len(candidates) == 1:
            matched_product = candidates[0]
            candidates      = []          # No ambiguity
        elif len(candidates) == 0:
            candidates = []

    return matched_product, color_from_vision, candidates
