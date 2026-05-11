"""
sync_views.py — Product Sync Endpoints

Provides REST endpoints to trigger product synchronization:
  - POST /api/v1/gateway/sync/trigger       → Sync all active companies
  - POST /api/v1/gateway/sync/trigger/{shop_id} → Sync specific shop
  - GET  /api/v1/gateway/sync/status        → Get last sync status
"""
import time
import logging
import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.crm.models import Company

logger = logging.getLogger(__name__)

# Configuration
TIKTAK_API_BASE_URL = getattr(settings, 'TIKTAK_API_BASE_URL', 'https://api.tiktakpro.com')
VISION_SERVICE_URL = getattr(settings, 'VISION_SERVICE_URL', 'http://vision-service:8002')
VISION_VECTORIZE_PATH = '/vectorize'


def fetch_products(shop_id: str) -> list:
    """
    Fetch all products for a shop with pagination.
    TikTak API is public (no authentication required).
    
    Args:
        shop_id: Company shop_id
        
    Returns:
        List of product dictionaries
    """
    url = f"{TIKTAK_API_BASE_URL}/api/v1/products-read/"
    all_results = []
    params = {"company": shop_id}
    page_count = 0

    while url and page_count < 10:  # Max 10 pages safety
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
            logger.error(f"[SYNC] Error fetching page {page_count}: {e}")
            break

    return all_results


def vectorize_image(image_url: str, product_id: str, shop_id: str, variation_id: str) -> bool:
    """
    Send image to vision-service for vectorization.
    
    Args:
        image_url: URL of the product image
        product_id: Product UUID
        shop_id: Company shop_id
        variation_id: Variation UUID (same as product_id if no variations)
        
    Returns:
        True if successful, False otherwise
    """
    payload = {
        "image_url": image_url,
        "product_id": str(product_id),
        "variation_id": str(variation_id),
        "shop_id": str(shop_id),
        "store_image_url": image_url,
    }
    try:
        vectorize_url = f"{VISION_SERVICE_URL}{VISION_VECTORIZE_PATH}"
        response = requests.post(vectorize_url, json=payload, timeout=30)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"[SYNC] Vectorization failed: {e}")
        return False


def sync_shop(company: Company) -> dict:
    """
    Sync a single shop's catalog.
    
    Args:
        company: Company model instance
        
    Returns:
        Dict with sync statistics: {success, failed, skipped, shop_name, shop_id}
    """
    shop_id = company.shop_id
    shop_name = company.name

    logger.info(f"[SYNC] Starting sync for [{shop_name}] (shop_id={shop_id})")

    raw_results = fetch_products(shop_id)
    if not raw_results:
        logger.warning(f"[SYNC] No products found for {shop_name}")
        return {
            "shop_id": shop_id,
            "shop_name": shop_name,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "error": "No products found"
        }

    success_count = 0
    failure_count = 0
    skipped_count = 0
    seen_images = set()

    for product in raw_results:
        # Skip child products (variations are handled via parent)
        if product.get("parent") is not None:
            continue

        product_id = product.get("id")

        # Products with variations
        for decl in product.get("declinaisons", []):
            image_url = decl.get("photo")
            variation_id = decl.get("id")

            if not image_url:
                skipped_count += 1
                continue

            dedup_key = (str(product_id), image_url)
            if dedup_key in seen_images:
                skipped_count += 1
                continue

            seen_images.add(dedup_key)
            if vectorize_image(image_url, product_id, shop_id, variation_id):
                success_count += 1
            else:
                failure_count += 1
            time.sleep(0.5)  # Rate limiting

        # Simple product (no variations)
        if not product.get("declinaisons") and product.get("photo"):
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
        f"[SYNC] [{shop_name}] Complete: "
        f"vectorized={success_count} | failed={failure_count} | skipped={skipped_count}"
    )
    
    return {
        "shop_id": shop_id,
        "shop_name": shop_name,
        "success": success_count,
        "failed": failure_count,
        "skipped": skipped_count,
    }


class SyncTriggerView(APIView):
    """
    Trigger product synchronization for all active companies.
    
    POST /api/v1/gateway/sync/trigger
    
    Auth: JWT or Static Token (requires IsAuthenticated)
    
    Returns:
        {
            "status": "success",
            "companies_synced": 3,
            "total_vectorized": 150,
            "total_failed": 2,
            "total_skipped": 10,
            "details": [
                {
                    "shop_id": "1LXybpj",
                    "shop_name": "My Shop",
                    "success": 50,
                    "failed": 1,
                    "skipped": 5
                },
                ...
            ]
        }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        companies = Company.objects.filter(is_active=True)
        
        if not companies.exists():
            return Response(
                {
                    "status": "error",
                    "message": "No active companies found"
                },
                status=status.HTTP_404_NOT_FOUND
            )

        results = []
        total_success = 0
        total_failed = 0
        total_skipped = 0

        for company in companies:
            sync_result = sync_shop(company)
            results.append(sync_result)
            total_success += sync_result["success"]
            total_failed += sync_result["failed"]
            total_skipped += sync_result["skipped"]

        return Response({
            "status": "success",
            "companies_synced": len(results),
            "total_vectorized": total_success,
            "total_failed": total_failed,
            "total_skipped": total_skipped,
            "details": results,
        })


class SyncTriggerShopView(APIView):
    """
    Trigger product synchronization for a specific shop.
    
    POST /api/v1/gateway/sync/trigger/{shop_id}
    
    Auth: JWT or Static Token (requires IsAuthenticated)
    
    Returns:
        {
            "status": "success",
            "shop_id": "1LXybpj",
            "shop_name": "My Shop",
            "success": 50,
            "failed": 1,
            "skipped": 5
        }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, shop_id):
        try:
            company = Company.objects.get(shop_id=shop_id, is_active=True)
        except Company.DoesNotExist:
            return Response(
                {
                    "status": "error",
                    "message": f"Company with shop_id={shop_id} not found or inactive"
                },
                status=status.HTTP_404_NOT_FOUND
            )

        result = sync_shop(company)
        
        if "error" in result:
            return Response(
                {"status": "error", **result},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            "status": "success",
            **result
        })


class SyncStatusView(APIView):
    """
    Get sync status information.
    
    GET /api/v1/gateway/sync/status
    
    Auth: JWT or Static Token (requires IsAuthenticated)
    
    Returns:
        {
            "status": "ok",
            "vision_service": "http://vision-service:8002",
            "tiktak_api": "https://api.tiktakpro.com",
            "active_companies": 3
        }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        active_count = Company.objects.filter(is_active=True).count()

        return Response({
            "status": "ok",
            "vision_service": VISION_SERVICE_URL,
            "tiktak_api": TIKTAK_API_BASE_URL,
            "active_companies": active_count,
        })
