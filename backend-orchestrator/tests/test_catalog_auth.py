"""
test_catalog_auth.py — Access control of the catalog endpoints.

Creates two temporary shops, checks the status code of each catalog route for
anonymous, invalid-token, cross-shop and own-shop callers, then deletes them.
No external service (Azure, Vision) is reached: every authorized call stops at
request validation.

Run: docker exec rebbah-ai-backend python tests/test_catalog_auth.py
"""
import os
import sys
from typing import Dict, List, Tuple

import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

from rest_framework.test import APIClient

from apps.crm.models import Company

SHOP_A = "test-catalog-shop-a"
SHOP_B = "test-catalog-shop-b"

# (method, url, payload sent for an owner, expected status for the owner)
ROUTES: List[Tuple[str, str, Dict[str, str], int]] = [
    ("post", "/api/v1/gateway/catalog/upload", {"item_id": "x"}, 400),
    ("patch", "/api/v1/gateway/catalog/update-metadata", {"item_id": "missing"}, 404),
    ("post", "/api/v1/gateway/catalog/import-csv", {}, 400),
]


def _call(client: APIClient, method: str, url: str, payload: Dict[str, str], token: str = "") -> int:
    extra = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
    return getattr(client, method)(url, payload, format="multipart", **extra).status_code


def _check(label: str, got: int, expected: int, failures: List[str]) -> None:
    ok = got == expected
    print(f"  [{'OK' if ok else 'FAIL'}] {label}: HTTP {got} (attendu {expected})")
    if not ok:
        failures.append(label)


def run_test() -> int:
    Company.objects.filter(shop_id__in=[SHOP_A, SHOP_B]).delete()
    shop_a = Company.objects.create(name="Test Shop A", shop_id=SHOP_A)
    shop_b = Company.objects.create(name="Test Shop B", shop_id=SHOP_B)
    client = APIClient(SERVER_NAME="localhost")
    failures: List[str] = []

    try:
        for method, url, payload, owner_status in ROUTES:
            name = url.rsplit("/", 1)[-1]
            print(f"{method.upper()} {url}")
            _check(f"{name} sans authentification", _call(client, method, url, {**payload, "shop_id": SHOP_A}), 401, failures)
            _check(f"{name} avec token invalide", _call(client, method, url, {**payload, "shop_id": SHOP_A}, "invalid"), 401, failures)
            _check(f"{name} boutique A sur boutique B", _call(client, method, url, {**payload, "shop_id": SHOP_B}, shop_a.dashboard_token), 403, failures)
            _check(f"{name} boutique B sur boutique A", _call(client, method, url, {**payload, "shop_id": SHOP_A}, shop_b.dashboard_token), 403, failures)
            _check(f"{name} boutique A sur sa boutique", _call(client, method, url, {**payload, "shop_id": SHOP_A}, shop_a.dashboard_token), owner_status, failures)
            _check(f"{name} sans shop_id (validation de la vue)", _call(client, method, url, payload, shop_a.dashboard_token), 400, failures)

        shop_a.is_active = False
        shop_a.save(update_fields=["is_active"])
        _check("upload avec boutique désactivée", _call(client, "post", ROUTES[0][1], {"shop_id": SHOP_A, "item_id": "x"}, shop_a.dashboard_token), 403, failures)
    finally:
        Company.objects.filter(shop_id__in=[SHOP_A, SHOP_B]).delete()

    if failures:
        print(f"\nECHEC : {len(failures)} vérification(s) en erreur.")
        return 1
    print("\nTOUS LES CONTROLES D'ACCES DU CATALOGUE SONT VALIDES.")
    return 0


if __name__ == "__main__":
    sys.exit(run_test())
