import os
import time
import requests
import logging

# Configuration
TIKTAK_API_BASE_URL = os.getenv("TIKTAK_API_BASE_URL",  "https://api.tiktakpro.com")
TIKTAK_API_TOKEN    = os.getenv("TIKTAK_API_TOKEN",      "")
COMPANY_SLUG        = os.getenv("COMPANY_SLUG",          "1LXybpj")
VISION_SERVICE_URL  = os.getenv("VISION_SERVICE_URL",    "http://vision-service:8002/vectorize")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_products():
    """Fetch tous les produits avec pagination."""
    url = f"{TIKTAK_API_BASE_URL}/api/v1/products-read/"
    headers = {"Authorization": f"Bearer {TIKTAK_API_TOKEN}"}
    all_results = []
    params = {"company": COMPANY_SLUG}
    page_count = 0

    logger.info(f"Fetching products pour company={COMPANY_SLUG}")

    while url and page_count < 10:
        try:
            if page_count == 0:
                resp = requests.get(url, headers=headers, params=params, timeout=10)
            else:
                resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            all_results.extend(data.get("results", []))
            url = data.get("next")
            page_count += 1
            logger.info(f"Page {page_count}: {len(data.get('results', []))} produits")
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur page {page_count}: {e}")
            break

    logger.info(f"Total brut: {len(all_results)} entrées")
    return all_results

def vectorize_image(image_url, product_id, shop_id, variation_id):
    """Envoie l'image au vision-service pour vectorisation."""
    payload = {
        "image_url":       image_url,
        "product_id":      str(product_id),
        "variation_id":    str(variation_id),
        "shop_id":         str(shop_id),
        "store_image_url": image_url
    }
    
    try:
        logger.info(f"Vectorizing {variation_id} pour produit {product_id}")
        response = requests.post(VISION_SERVICE_URL, json=payload, timeout=30)
        response.raise_for_status()
        logger.info(f"Success: {response.json().get('status')}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed: {e}")
        return False

def sync_catalog():
    """
    Sync avec déduplication d'images.
    
    Logique: une même image (sweatshirt_bleu.webp) peut être partagée
    par plusieurs tailles (S/M/L/XL). CLIP ne voit pas la taille
    → vectoriser 1 fois par (product_id, image_url) unique.
    """
    logger.info(f"Démarrage sync company={COMPANY_SLUG}")

    raw_results = fetch_products()
    if not raw_results:
        logger.warning("Aucun produit récupéré")
        return

    success_count = 0
    failure_count = 0
    skipped_count = 0
    seen_images   = set()  # déduplication

    for product in raw_results:
        if product.get("parent") is not None:
            continue

        product_id = product.get("id")

        # Produits avec déclinaisons
        for decl in product.get("declinaisons", []):
            image_url    = decl.get("photo")
            variation_id = decl.get("id")

            if not image_url:
                skipped_count += 1
                continue

            dedup_key = (str(product_id), image_url)
            if dedup_key in seen_images:
                logger.debug(f"Image déjà vectorisée: {image_url}")
                skipped_count += 1
                continue

            seen_images.add(dedup_key)
            success = vectorize_image(image_url, product_id, COMPANY_SLUG, variation_id)
            if success:
                success_count += 1
            else:
                failure_count += 1
            time.sleep(0.5)

        # Produit simple (sans déclinaisons)
        if not product.get("declinaisons") and product.get("photo"):
            image_url = product["photo"]
            dedup_key = (str(product_id), image_url)
            if dedup_key not in seen_images:
                seen_images.add(dedup_key)
                success = vectorize_image(image_url, product_id, COMPANY_SLUG, product_id)
                if success:
                    success_count += 1
                else:
                    failure_count += 1
                time.sleep(0.5)

    logger.info(
        f"Sync terminé. "
        f"Vectorisés: {success_count} | "
        f"Échoués: {failure_count} | "
        f"Skippés: {skipped_count}"
    )

if __name__ == "__main__":
    logger.info("Initializing Sync Worker...")
    sync_catalog()
