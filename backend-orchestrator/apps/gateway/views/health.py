import time
import logging
import os
import redis
import requests
from django.conf import settings
from django.db import connection
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser

from core.celery import app as celery_app
from apps.crm.models import PipelineLog

logger = logging.getLogger(__name__)

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
    Enhanced Health check for Postgres, Redis, Vision service, and Celery workers.
    Only accessible to logged-in Django admin users (staff/superadmin) using Session Cookies.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request):
        t_start = time.monotonic()
        
        # 1. Ping Postgres DB
        db_status, db_latency, db_err = "down", None, None
        try:
            t0 = time.monotonic()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            db_latency = round((time.monotonic() - t0) * 1000, 1)
            db_status = "ok"
        except Exception as e:
            db_err = str(e)
            logger.error(f"[HEALTH] postgres DOWN: {e}")

        # 2. Ping Redis
        redis_status, redis_latency, redis_err = "down", None, None
        try:
            t0 = time.monotonic()
            r = redis.Redis(
                host=os.getenv("REDIS_HOST", "redis"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                password=os.getenv("REDIS_PASSWORD", "") or None,
                socket_timeout=2
            )
            r.ping()
            redis_latency = round((time.monotonic() - t0) * 1000, 1)
            redis_status = "ok"
        except Exception as e:
            redis_err = str(e)
            logger.error(f"[HEALTH] redis DOWN: {e}")

        # 3. Ping Vision Service
        vision_res = _ping(VISION_URL, "vision-service")

        # 4. Ping Celery Worker status
        celery_status, celery_latency, celery_err, active_workers = "down", None, None, []
        try:
            t0 = time.monotonic()
            inspect = celery_app.control.inspect(timeout=1.5)
            ping_res = inspect.ping()
            celery_latency = round((time.monotonic() - t0) * 1000, 1)
            if ping_res:
                celery_status = "ok"
                active_workers = list(ping_res.keys())
                logger.info(f"[HEALTH] celery-worker OK — {celery_latency}ms. Active: {active_workers}")
            else:
                celery_status = "degraded"
                celery_err = "No active workers detected"
                logger.warning("[HEALTH] celery-worker degraded — no active workers responding")
        except Exception as e:
            celery_err = str(e)
            logger.error(f"[HEALTH] celery-worker DOWN: {e}")

        # 5. Fetch 5 most recent PipelineLog entries for simple activity tracking
        recent_logs = []
        try:
            logs = PipelineLog.objects.order_by('-created_at')[:5]
            for log in logs:
                recent_logs.append({
                    "timestamp": log.created_at.isoformat(),
                    "sender_id": log.sender_id,
                    "intent": log.detected_intent,
                    "state_before": log.state_before,
                    "state_after": log.state_after,
                    "duration_ms": log.duration_ms,
                    "has_error": log.has_error,
                })
        except Exception as e:
            logger.warning(f"[HEALTH] Failed to fetch PipelineLog activity: {e}")

        # Compile overall system status
        services_status = [
            {"service": "postgres", "status": db_status, "latency_ms": db_latency, "error": db_err},
            {"service": "redis", "status": redis_status, "latency_ms": redis_latency, "error": redis_err},
            vision_res,
            {"service": "celery-worker", "status": celery_status, "latency_ms": celery_latency, "error": celery_err, "active_workers": active_workers}
        ]
        
        all_ok = all(s["status"] == "ok" for s in services_status)
        any_down = any(s["status"] == "down" for s in services_status)
        overall = "ok" if all_ok else ("down" if any_down else "degraded")
        
        http_status = 200 if all_ok else (503 if any_down else 207)
        total_duration = round((time.monotonic() - t_start) * 1000, 1)

        return Response(
            {
                "overall": overall,
                "timestamp": timezone.now().isoformat(),
                "duration_total_ms": total_duration,
                "services": services_status,
                "recent_activity": recent_logs
            },
            status=http_status
        )
