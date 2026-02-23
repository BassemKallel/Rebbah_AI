import os
import time
import requests
import logging

# Configuration
MOCK_API_BASE_URL = os.getenv("MOCK_API_URL", "http://host.docker.internal:8003/api/v1")
VISION_SERVICE_URL = os.getenv("VISION_SERVICE_URL", "http://vision-service:8002/vectorize")

# A test store ID (fallback if not provided in env)
STORE_ID = os.getenv("STORE_ID", "123e4567-e89b-12d3-a456-426614174000")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_products():
    """Fetch all products from the mock API."""
    url = f"{MOCK_API_BASE_URL}/products/"
    headers = {"X-Store-ID": STORE_ID}
    
    try:
        logger.info(f"Fetching products from {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch products: {e}")
        return []

def vectorize_image(image_url, product_id, shop_id, variation_id):
    """Send image URL to the vision service to extract and store embeddings."""
    payload = {
        "image_url": image_url,
        "product_id": str(product_id),
        "shop_id": str(shop_id)
    }
    
    try:
        logger.info(f"Vectorizing variation {variation_id} for product {product_id}")
        response = requests.post(VISION_SERVICE_URL, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        logger.info(f"Success: {result.get('status')}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to vectorize image {image_url}: {e}")
        return False

def sync_catalog():
    """Main synchronization loop."""
    logger.info(f"Starting catalog synchronization for Store ID: {STORE_ID}")
    
    products = fetch_products()
    if not products:
        logger.warning("No products found or failed to fetch.")
        return

    success_count = 0
    failure_count = 0
    skipped_count = 0

    for product in products:
        product_id = product.get("id")
        shop_id = product.get("store_id") # Note: Mock API uses store_id integer, we'll cast to str
        variations = product.get("variations", [])
        
        for variation in variations:
            image_url = variation.get("image")
            variation_id = variation.get("id")
            
            if not image_url:
                logger.debug(f"Skipping variation {variation_id} (no image)")
                skipped_count += 1
                continue
                
            # Send to vision service
            success = vectorize_image(image_url, product_id, shop_id, variation_id)
            if success:
                success_count += 1
            else:
                failure_count += 1
                
            # Rate limiting to avoid overwhelming the vision service (which downloads images and runs neural nets)
            time.sleep(1)

    logger.info(f"Sync complete. Success: {success_count}, Failed: {failure_count}, Skipped: {skipped_count}")

if __name__ == "__main__":
    # For the POC, we just run it once.
    # In a real app, you might schedule this or connect it to webhooks from Shopify/MockAPI
    logger.info("Initializing Sync Worker...")
    sync_catalog()
