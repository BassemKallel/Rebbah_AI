"""
permissions.py — DRF permissions shared by the gateway and CRM APIs.
"""
from typing import Any, Optional

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.crm.models import Company


class IsAuthenticatedShop(BasePermission):
    """
    Restricts an endpoint to the shop that owns the request.

    The caller must be authenticated as an active Company, either with a
    dashboard JWT or with the shop's static dashboard token (see
    apps.crm.services.authentication). When the request names a ``shop_id``
    (body or query string), it must be the authenticated company's own shop.

    Anonymous callers get a 401; an authenticated caller targeting another
    shop gets a 403. A request without ``shop_id`` passes this check so the
    view can answer with its own validation error.
    """

    message = "Accès refusé : cette boutique n'est pas la vôtre."

    def has_permission(self, request: Request, view: APIView) -> bool:
        company: Any = request.auth
        if not isinstance(company, Company) or not company.is_active:
            return False

        requested_shop_id: Optional[str] = self._requested_shop_id(request)
        return requested_shop_id is None or requested_shop_id == company.shop_id

    @staticmethod
    def _requested_shop_id(request: Request) -> Optional[str]:
        body: Any = request.data
        raw: Any = body.get("shop_id") if hasattr(body, "get") else None
        if raw in (None, ""):
            raw = request.query_params.get("shop_id")
        return str(raw) if raw not in (None, "") else None
