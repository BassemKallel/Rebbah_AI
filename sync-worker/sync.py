"""
Multi-shop product sync worker.
Reads all active companies from the crm_company table,
then syncs each shop's catalog via the TikTak API → Vision Service pipeline.

NOTE: The TikTak PRO API is public — no authentication token required.
"""
import os
import time
import requests
import logging
import psycopg2

# ── Configuration ────────────────────────────────────────────────────────────

TIKTAK_API_BASE_URL = os.getenv("TIKTAK_API_BASE_URL", "https://api.tiktakpro.com")
VISION_SERVICE_URL  = os.getenv("VISION_SERVICE_URL",  "http://vision-service:8002/vectorize")

# Django DB — same env vars as backend-orchestrator
DB_HOST     = os.getenv("POSTGRES_HOST", "")
DB_PORT     = os.getenv("POSTGRES_PORT", "5432")
DB_NAME     = os.getenv("POSTGRES_DB",   "")
DB_USER     = os.getenv("POSTGRES_USER", "")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ── Database ─────────────────────────────────────────────────────────────────

def get_active_companies():
    """
    Read all active companies from crm_company table.
    Returns list of dicts: [{shop_id, name}, ...]
    """
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
            user=DB_USER, password=DB_PASSWORD,
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT shop_id, name
            FROM crm_company
            WHERE is_active = TRUE
              AND shop_id IS NOT NULL
        """)
        companies = [
            {"shop_id": row[0], "name": row[1]}
            for row in cursor.fetchall()
        ]
        cursor.close()
        conn.close()
        logger.info(f"Found {len(companies)} active companies in DB")
        return companies
    except Exception as e:
        logger.error(f"Failed to read companies from DB: {e}")
        return []


def get_existing_vectors(shop_id):
    """
    Return the set of (product_id, image_url) already indexed in pgvector
    for a given shop. Using product_id (= parent_id for children) + image_url
    as the uniqueness key avoids re-vectorizing the same image if the API
    returns children in a different order across sync cycles.
    """
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
            user=DB_USER, password=DB_PASSWORD,
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT product_id, image_url
            FROM products_vector
            WHERE shop_id = %s
        """, (str(shop_id),))
        existing = {(str(row[0]), row[1]) for row in cursor.fetchall()}
        cursor.close()
        conn.close()
        logger.info(f"  Found {len(existing)} already-indexed vectors for shop={shop_id}")
        return existing
    except Exception as e:
        logger.warning(f"  Could not read existing vectors ({e}) — will re-vectorize all")
        return set()


# ── TikTak API ───────────────────────────────────────────────────────────────

def fetch_products(shop_id):
    """Fetch all products for a shop with pagination. No auth required."""
    url = f"{TIKTAK_API_BASE_URL}/api/v1/products-read/"
    all_results = []
    params = {"company": shop_id}
    page_count = 0

    while url and page_count < 50:
        try:
            if page_count == 0:
                resp = requests.get(url, params=params, timeout=10)
            else:
                resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            all_results.extend(data.get("results", []))
            url = data.get("next")
            page_count += 1
        except requests.exceptions.RequestException as e:
            logger.error(f"  Erreur page {page_count}: {e}")
            break

    return all_results


def vectorize_image(image_url, product_id, shop_id, variation_id):
    """Send image to vision-service for vectorization."""
    payload = {
        "image_url":       image_url,
        "product_id":      str(product_id),
        "variation_id":    str(variation_id),
        "shop_id":         str(shop_id),
        "store_image_url": image_url,
    }
    try:
        response = requests.post(VISION_SERVICE_URL, json=payload, timeout=30)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"  Vectorize failed: {e}")
        return False


# ── Sync Logic ───────────────────────────────────────────────────────────────

def sync_shop(shop_id, shop_name):
    """Sync a single shop's catalog."""
    logger.info(f"── Syncing [{shop_name}] (shop_id={shop_id}) ──")

    # Pre-load already-indexed (variation_id, image_url) to avoid re-encoding
    existing_vectors = get_existing_vectors(shop_id)

    raw_results = fetch_products(shop_id)
    if not raw_results:
        logger.warning(f"  No products for {shop_name}")
        return 0, 0, 0

    success_count = 0
    failure_count = 0
    skipped_count = 0
    seen_images   = set()

    for product in raw_results:
        parent_id = product.get("parent")

        # ── Child product ────────────────────────────────────────────────────
        # Children appear as flat items in the API response with parent != null.
        # Their individual photos (per colour/size) must be captured here because
        # the parent's embedded declinaisons often have photo=null.
        # We vectorize them attributed to the parent (product_id=parent_id).
        if parent_id is not None:
            image_url = product.get("photo")
            if image_url:
                variation_id = product.get("id")
                # Skip if parent+image already indexed (regardless of which child
                # arrived first — API order may vary between cycles)
                if (str(parent_id), image_url) in existing_vectors:
                    skipped_count += 1
                    continue
                dedup_key = (str(parent_id), image_url)
                if dedup_key not in seen_images:
                    seen_images.add(dedup_key)
                    if vectorize_image(image_url, parent_id, shop_id, variation_id):
                        success_count += 1
                        existing_vectors.add(dedup_key)  # prevent re-send this cycle
                    else:
                        failure_count += 1
                    time.sleep(0.5)
                else:
                    skipped_count += 1
            continue

        # ── Parent product ───────────────────────────────────────────────────
        product_id = product.get("id")
        product_vectorized = False

        # Products with variations
        for decl in product.get("declinaisons", []):
            image_url    = decl.get("photo")
            variation_id = decl.get("id")

            if not image_url:
                skipped_count += 1
                continue

            # Skip if product+image already indexed
            if (str(product_id), image_url) in existing_vectors:
                skipped_count += 1
                continue

            dedup_key = (str(product_id), image_url)
            if dedup_key in seen_images:
                skipped_count += 1
                continue

            seen_images.add(dedup_key)
            if vectorize_image(image_url, product_id, shop_id, variation_id):
                success_count += 1
                product_vectorized = True
            else:
                failure_count += 1
            time.sleep(0.5)

        # Fallback: use parent photo when no variation had an image
        if not product_vectorized and product.get("photo"):
            image_url = product["photo"]
            dedup_key = (str(product_id), image_url)
            if dedup_key not in seen_images:
                seen_images.add(dedup_key)
                if vectorize_image(image_url, product_id, shop_id, product_id):
                    success_count += 1
                else:
                    failure_count += 1
                time.sleep(0.5)

    logger.info(
        f"  [{shop_name}] Done: "
        f"vectorized={success_count} | failed={failure_count} | skipped={skipped_count}"
    )
    return success_count, failure_count, skipped_count


def sync_all():
    """Main entry: sync all active companies from DB."""
    companies = get_active_companies()

    if not companies:
        logger.warning("No active companies found — nothing to sync.")
        return

    total_ok = total_fail = total_skip = 0

    for company in companies:
        ok, fail, skip = sync_shop(
            shop_id=company["shop_id"],
            shop_name=company["name"],
        )
        total_ok   += ok
        total_fail += fail
        total_skip += skip

    logger.info(
        f"═══ ALL SHOPS SYNC COMPLETE ═══ "
        f"shops={len(companies)} | "
        f"vectorized={total_ok} | failed={total_fail} | skipped={total_skip}"
    )


if __name__ == "__main__":
    logger.info("Starting Multi-Shop Sync Worker (one-shot mode)...")
    sync_all()
    logger.info("Sync complete. Exiting.")

