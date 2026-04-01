"""
health.py — Health check endpoint for external AI services.

GET /api/v1/gateway/health/
Returns the status of NLU and Vision services with response times.
Secured by TikTak token authentication (same as CRM API).
"""
import time
import logging
import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser

logger = logging.getLogger(__name__)

NLU_URL    = settings.NLU_SERVICE_URL.rstrip('/')
VISION_URL = settings.VISION_SERVICE_URL.rstrip('/')
TIMEOUT    = 5  # seconds — fast ping, not a full predict call


def _ping(url: str, label: str) -> dict:
    """
    Ping a service by calling its /health or root endpoint.
    Returns a status dict with latency and error info.
    """
    result = {"service": label, "url": url, "status": "unknown", "latency_ms": None, "error": None}
    try:
        t0 = time.monotonic()
        res = requests.get(f"{url}/health", timeout=TIMEOUT)
        latency = round((time.monotonic() - t0) * 1000, 1)
        result["latency_ms"] = latency
        if res.status_code < 500:
            result["status"] = "ok"
            logger.info(f"[HEALTH] {label} OK — {latency}ms (HTTP {res.status_code})")
        else:
            result["status"] = "degraded"
            result["error"] = f"HTTP {res.status_code}"
            logger.warning(f"[HEALTH] {label} degraded — HTTP {res.status_code}")
    except requests.ConnectionError as e:
        result["status"] = "down"
        result["error"] = "Connection refused"
        logger.error(f"[HEALTH] {label} DOWN — connection refused: {e}")
    except requests.Timeout:
        result["status"] = "down"
        result["error"] = f"Timeout after {TIMEOUT}s"
        logger.error(f"[HEALTH] {label} DOWN — timeout")
    except Exception as e:
        result["status"] = "down"
        result["error"] = str(e)
        logger.error(f"[HEALTH] {label} DOWN — {e}")
    return result


class ServicesHealthView(APIView):
    """
    Health check for NLU and Vision services.
    Only accessible to Django admin users (staff).
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        nlu    = _ping(NLU_URL,    "nlu-service")
        vision = _ping(VISION_URL, "vision-service")

        services = [nlu, vision]
        all_ok   = all(s["status"] == "ok" for s in services)
        any_down = any(s["status"] == "down" for s in services)

        overall = "ok" if all_ok else ("down" if any_down else "degraded")

        http_status = 200 if all_ok else (503 if any_down else 207)

        return Response(
            {
                "overall": overall,
                "gemini_fallback_enabled": settings.GEMINI_FALLBACK_ENABLED,
                "services": services,
            },
            status=http_status,
        )
