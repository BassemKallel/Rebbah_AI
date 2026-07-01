"""
apps/crm/views/dashboard.py

Six lightweight read-only endpoints that power the Dashboard frontend.

All endpoints require ?shop_id=<id> and IsAuthenticated.
"""
import logging
from datetime import date, timedelta, timezone as dt_tz
from typing import Any, Dict, List
from django.db.models import Count
from django.db.models.functions import TruncHour
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Conversation, Lead, Message, NLUFallbackLog

logger = logging.getLogger(__name__)


def _lead_extracted_data(lead: Lead) -> Dict[str, Any]:
    return lead.extracted_data or {}


def _lead_order_items_payload(lead: Lead) -> List[Dict[str, Any]]:
    db_items = list(lead.items.all())
    if db_items:
        return [
            {
                "product_id": item.product_id,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "price": float(item.price) if item.price is not None else None,
                "attributes": item.attributes or {},
            }
            for item in db_items
        ]

    raw_items = _lead_extracted_data(lead).get("items") or []
    return raw_items if isinstance(raw_items, list) else []


def _lead_product_label(lead: Lead) -> str:
    items = _lead_order_items_payload(lead)
    if items:
        return ", ".join(
            f"{item.get('quantity', 1)}x {item.get('product_name', 'Produit')}"
            for item in items
        )
    data = _lead_extracted_data(lead)
    return str(data.get("product") or data.get("service_type") or "")


def _require_shop(request):
    """Return shop_id or a 400 Response tuple."""
    shop_id = request.query_params.get("shop_id")
    if not shop_id:
        return None, Response({"error": "shop_id is required."}, status=400)
    return shop_id, None


def _sparkline(model, shop_id, field="created_at", days=7):
    """Return list of daily counts for the last `days` days."""
    today = timezone.now().date()
    result = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        kwargs = {f"{field}__date": d}
        if hasattr(model, "shop_id"):
            kwargs["shop_id"] = shop_id
        result.append(model.objects.filter(**kwargs).count())
    return result


def _conv_sparkline(shop_id, days=7):
    today = timezone.now().date()
    return [
        Conversation.objects.filter(shop_id=shop_id, created_at__date=today - timedelta(days=i)).count()
        for i in range(days - 1, -1, -1)
    ]


def _order_sparkline(shop_id, days=7):
    today = timezone.now().date()
    return [
        Lead.objects.filter(shop_id=shop_id, has_pending_order=True, created_at__date=today - timedelta(days=i)).count()
        for i in range(days - 1, -1, -1)
    ]


def _fallback_sparkline(shop_id, days=7):
    """Fallback count per day (joined through Message → Conversation)."""
    today = timezone.now().date()
    return [
        NLUFallbackLog.objects.filter(
            message__conversation__shop_id=shop_id,
            created_at__date=today - timedelta(days=i)
        ).count()
        for i in range(days - 1, -1, -1)
    ]


# ─── 1. KPIs ────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_kpis(request):
    """
    GET /api/crm/dashboard/kpis/?shop_id=xxx

    Returns the four KPI cards + automation stats.
    Main counts are for the last 7 days; delta compares to the previous 7 days.
    """
    shop_id, err = _require_shop(request)
    if err:
        return err

    today = timezone.now().date()
    week_start      = today - timedelta(days=6)   # last 7 days (inclusive)
    prev_week_start = today - timedelta(days=13)  # previous 7-day window
    prev_week_end   = today - timedelta(days=7)

    def _date_range(qs, start, end):
        return qs.filter(created_at__date__gte=start, created_at__date__lte=end)

    # ── Conversations (last 7 days vs previous 7 days) ──────────────────────
    conv_week      = _date_range(Conversation.objects.filter(shop_id=shop_id), week_start, today).count()
    conv_prev_week = _date_range(Conversation.objects.filter(shop_id=shop_id), prev_week_start, prev_week_end).count()

    # ── Orders (active pending orders + trend) ──────────────────────────────
    orders_week      = _date_range(Lead.objects.filter(shop_id=shop_id, has_pending_order=True), week_start, today).count()
    orders_prev_week = _date_range(Lead.objects.filter(shop_id=shop_id, has_pending_order=True), prev_week_start, prev_week_end).count()
    conversion_rate  = round((orders_week / conv_week * 100) if conv_week else 0)

    # ── Awaiting agent (current live count) ─────────────────────────────────
    awaiting_now        = Conversation.objects.filter(shop_id=shop_id, is_human_controlled=True).count()
    awaiting_prev_week  = _date_range(
        Conversation.objects.filter(shop_id=shop_id, is_human_controlled=True),
        prev_week_start, prev_week_end
    ).count()

    # ── Fallbacks (last 7 days) ──────────────────────────────────────────────
    fallbacks_week = NLUFallbackLog.objects.filter(
        message__conversation__shop_id=shop_id,
        created_at__date__gte=week_start,
        created_at__date__lte=today,
    ).count()
    fallbacks_prev_week = NLUFallbackLog.objects.filter(
        message__conversation__shop_id=shop_id,
        created_at__date__gte=prev_week_start,
        created_at__date__lte=prev_week_end,
    ).count()

    # ── Automation rate ──────────────────────────────────────────────────────
    automation_rate      = round((1 - fallbacks_week / conv_week) * 100)      if conv_week      else 100
    automation_rate_prev = round((1 - fallbacks_prev_week / conv_prev_week) * 100) if conv_prev_week else 100

    # ── Sparklines ───────────────────────────────────────────────────────────
    conv_spark    = _conv_sparkline(shop_id)
    order_spark   = _order_sparkline(shop_id)
    fallback_spark = _fallback_sparkline(shop_id)
    awaiting_spark = [
        Conversation.objects.filter(
            shop_id=shop_id, is_human_controlled=True,
            human_takeover_at__date=today - timedelta(days=i)
        ).count()
        for i in range(6, -1, -1)
    ]
    automation_spark = []
    for c, f in zip(_conv_sparkline(shop_id), fallback_spark):
        rate = round((1 - f / c) * 100) if c else 100
        automation_spark.append(rate)

    return Response({
        "conversations": {
            "today": conv_week,
            "delta": conv_week - conv_prev_week,
            "up": conv_week >= conv_prev_week,
            "sub": "7 derniers jours",
            "sparkline": conv_spark,
        },
        "orders": {
            "today": orders_week,
            "delta": orders_week - orders_prev_week,
            "up": orders_week >= orders_prev_week,
            "conversion_rate": conversion_rate,
            "sub": f"Taux : {conversion_rate}%",
            "sparkline": order_spark,
        },
        "awaiting_agent": {
            "count": awaiting_now,
            "delta": awaiting_now - awaiting_prev_week,
            "up": awaiting_now > awaiting_prev_week,
            "sub": "En attente maintenant",
            "sparkline": awaiting_spark,
        },
        "automation": {
            "rate": automation_rate,
            "delta": automation_rate - automation_rate_prev,
            "up": automation_rate >= automation_rate_prev,
            "fallbacks_today": fallbacks_week,
            "sub": f"{fallbacks_week} fallbacks (7j)",
            "sparkline": automation_spark,
        },
    })


# ─── 2. Hourly Volume ────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_hourly(request):
    """
    GET /api/crm/dashboard/hourly/?shop_id=xxx&date=2026-04-16

    Returns hourly conversation volume for a given date (default: today).
    """
    shop_id, err = _require_shop(request)
    if err:
        return err

    date_param = request.query_params.get("date")
    try:
        target_date = date.fromisoformat(date_param) if date_param else timezone.now().date()
    except ValueError:
        return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

    qs = (
        Conversation.objects
        .filter(shop_id=shop_id, created_at__date=target_date)
        .annotate(hour=TruncHour("created_at"))
        .values("hour")
        .annotate(v=Count("id"))
        .order_by("hour")
    )

    # Build full 07h–22h grid (fill zeros for missing hours)
    by_hour = {row["hour"].astimezone(dt_tz.utc).hour: row["v"] for row in qs}
    data = [
        {"h": f"{h:02d}h", "v": by_hour.get(h, 0)}
        for h in range(7, 23)
    ]
    return Response(data)


# ─── 3. Pending Orders ───────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_pending_orders(request):
    """
    GET /api/crm/dashboard/pending-orders/?shop_id=xxx

    Returns leads with agent_confirmation_pending=True.
    """
    shop_id, err = _require_shop(request)
    if err:
        return err

    leads = (
        Lead.objects
        .filter(shop_id=shop_id, agent_confirmation_pending=True)
        .prefetch_related("conversations")
        .order_by("-created_at")
    )

    data = []
    for lead in leads:
        # Derive platform from latest conversation
        latest_conv = lead.conversations.order_by("-created_at").first()
        platform = latest_conv.platform if latest_conv else "messenger"

        extracted_data = _lead_extracted_data(lead)

        data.append({
            "id": lead.id,
            "name": lead.name or lead.platform_id,
            "product": _lead_product_label(lead).strip(),
            "phone": extracted_data.get("phone_number", ""),
            "address": extracted_data.get("address", ""),
            "items": _lead_order_items_payload(lead),
            "platform": platform.capitalize(),
            "avatar": None,
            "pending_order_reference": lead.pending_order_reference,
        })

    return Response(data)


# ─── 4. Recent Activity ──────────────────────────────────────────────────────

_EVENT_TYPE_MAP = {
    "COMPLETED":     ("ORDER",    "bg-emerald-50 text-emerald-600", "bg-green-50 text-green-700"),
    "LLM_CANCELED":  ("CANCELED", "bg-rose-50 text-rose-500",       "bg-rose-50 text-rose-600"),
    "WAITING_USER_REPLY": ("WAITING", "bg-yellow-50 text-yellow-600", "bg-yellow-50 text-yellow-700"),
    "FALLBACK":      ("FALLBACK", "bg-red-50 text-red-500",        "bg-red-50 text-red-600"),
    "default":       ("INFO",     "bg-blue-50 text-blue-500",       "bg-blue-50 text-blue-700"),
}

def _state_to_event(state_after, is_fallback):
    if is_fallback:
        return _EVENT_TYPE_MAP["FALLBACK"]
    return _EVENT_TYPE_MAP.get(state_after, _EVENT_TYPE_MAP["default"])


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_recent_activity(request):
    """
    GET /api/crm/dashboard/recent-activity/?shop_id=xxx&limit=10
    """
    shop_id, err = _require_shop(request)
    if err:
        return err

    limit = min(int(request.query_params.get("limit", 10)), 50)

    messages = (
        Message.objects
        .filter(conversation__shop_id=shop_id, sender="BOT")
        .select_related("conversation__lead")
        .order_by("-created_at")[:limit]
    )

    now = timezone.now()
    data = []
    for msg in messages:
        lead = msg.conversation.lead
        name = (lead.name or lead.platform_id) if lead else msg.conversation.sender_id or "?"
        elapsed = now - msg.created_at
        minutes = int(elapsed.total_seconds() // 60)
        time_ago = f"{minutes} min" if minutes < 60 else f"{int(minutes // 60)}h"

        event_type, icon_cls, cls = _state_to_event(
            msg.conversation_state_after, msg.is_fallback
        )

        data.append({
            "id": msg.id,
            "text": f"{name} — {msg.text[:60]}",
            "time": time_ago,
            "state": msg.conversation_state_after or "UNKNOWN",
            "event_type": event_type,
            "icon_cls": icon_cls,
            "cls": cls,
        })

    return Response(data)


# ─── 5. Top Intents ──────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_top_intents(request):
    """
    GET /api/crm/dashboard/top-intents/?shop_id=xxx&date=today
    """
    shop_id, err = _require_shop(request)
    if err:
        return err

    today = timezone.now().date()
    week_start = today - timedelta(days=6)

    # Accept optional single-day filter; default to last 7 days
    date_param = request.query_params.get("date")
    if date_param:
        try:
            target_date = date.fromisoformat(date_param)
            date_filter = {"created_at__date": target_date}
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)
    else:
        date_filter = {"created_at__date__gte": week_start, "created_at__date__lte": today}

    qs = (
        Message.objects
        .filter(
            conversation__shop_id=shop_id,
            sender="USER",
            **date_filter,
        )
        .exclude(extracted_intent__isnull=True)
        .exclude(extracted_intent="")
        .values("extracted_intent")
        .annotate(count=Count("id"))
        .order_by("-count")[:6]
    )

    rows = list(qs)
    total = sum(r["count"] for r in rows)

    _INTENT_COLORS = [
        "bg-[#0f6885]", "bg-blue-400", "bg-violet-400",
        "bg-orange-400", "bg-emerald-400", "bg-rose-400",
    ]

    data = [
        {
            "intent": r["extracted_intent"],
            "count": r["count"],
            "pct": round(r["count"] / total * 100) if total else 0,
            "color": _INTENT_COLORS[i % len(_INTENT_COLORS)],
        }
        for i, r in enumerate(rows)
    ]
    return Response(data)


# ─── 6. Channels ────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_channels(request):
    """
    GET /api/crm/dashboard/channels/?shop_id=xxx
    """
    shop_id, err = _require_shop(request)
    if err:
        return err

    today = timezone.now().date()
    week_start = today - timedelta(days=6)

    qs = (
        Conversation.objects
        .filter(shop_id=shop_id, created_at__date__gte=week_start, created_at__date__lte=today)
        .values("platform")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    rows = list(qs)
    total = sum(r["count"] for r in rows)

    _CHANNEL_COLORS = {
        "messenger": "bg-blue-500",
        "instagram": "bg-purple-400",
        "poc":       "bg-gray-400",
    }
    _CHANNEL_LABELS = {
        "messenger": "Messenger",
        "instagram": "Instagram",
        "poc":       "POC / Test",
    }

    data = [
        {
            "name": _CHANNEL_LABELS.get(r["platform"], r["platform"].capitalize()),
            "count": r["count"],
            "pct": round(r["count"] / total * 100) if total else 0,
            "color": _CHANNEL_COLORS.get(r["platform"], "bg-gray-400"),
        }
        for r in rows
    ]
    return Response(data)


# ─── 7. Lead Funnel ─────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_lead_funnel(request):
    """
    GET /api/crm/dashboard/lead-funnel/?shop_id=xxx

    Funnel: Conversations → Engagés (lead créé) → Qualifiés (pré-commande)
    PROSPECT is excluded — leads are created lazily on purchase intent only.
    """
    shop_id, err = _require_shop(request)
    if err:
        return err

    total_conversations = Conversation.objects.filter(shop_id=shop_id).count()
    engaged   = Lead.objects.filter(shop_id=shop_id, lead_status="ENGAGED").count()
    qualified = Lead.objects.filter(shop_id=shop_id, lead_status="QUALIFIED").count()

    # "Engagés" = all leads (ENGAGED + QUALIFIED), since leads are only created on purchase intent
    total_leads = Lead.objects.filter(shop_id=shop_id).count()

    def _conv_sparkline(days=7):
        today = timezone.now().date()
        return [
            Conversation.objects.filter(shop_id=shop_id, created_at__date=today - timedelta(days=i)).count()
            for i in range(days - 1, -1, -1)
        ]

    def _lead_sparkline(days=7):
        today = timezone.now().date()
        return [
            Lead.objects.filter(shop_id=shop_id, created_at__date=today - timedelta(days=i)).count()
            for i in range(days - 1, -1, -1)
        ]

    def _qualified_sparkline(days=7):
        today = timezone.now().date()
        return [
            Lead.objects.filter(shop_id=shop_id, lead_status="QUALIFIED", created_at__date=today - timedelta(days=i)).count()
            for i in range(days - 1, -1, -1)
        ]

    conv_to_lead   = round(total_leads / total_conversations * 100) if total_conversations else 0
    lead_to_qualified = round(qualified / total_leads * 100) if total_leads else 0

    return Response({
        "stages": [
            {
                "key":       "CONVERSATIONS",
                "label":     "Conversations",
                "count":     total_conversations,
                "pct":       100,
                "color":     "bg-blue-400",
                "color_hex": "#60a5fa",
                "sparkline": _conv_sparkline(),
            },
            {
                "key":       "ENGAGED",
                "label":     "Intention d'achat",
                "count":     total_leads,
                "pct":       conv_to_lead,
                "color":     "bg-violet-400",
                "color_hex": "#a78bfa",
                "sparkline": _lead_sparkline(),
            },
            {
                "key":       "QUALIFIED",
                "label":     "Pré-commande créée",
                "count":     qualified,
                "pct":       lead_to_qualified,
                "color":     "bg-emerald-500",
                "color_hex": "#10b981",
                "sparkline": _qualified_sparkline(),
            },
        ],
        "conversion": {
            "conv_to_lead":       conv_to_lead,
            "lead_to_qualified":  lead_to_qualified,
        },
        "total": total_conversations,
    })
