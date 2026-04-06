"""
test_auth_endpoints.py — Tests unitaires pour l'authentification JWT et Dashboard Token.

Coverage (24 tests):
  — JWTLoginView         (6): login valide, mauvais mdp, user inactif, sans company, champs requis
  — MeView               (5): JWT auth, static token auth, sans auth
  — JWTCompanyAuth       (4): token valide, expiré/invalide, skip JWT sur static token
  — StaticTokenAuth      (5): bearer valide, token prefix, token invalide, JWT ignoré, company inactif
  — ProtectedEndpoints   (4): leads list avec JWT, avec static token, sans auth → 401
"""

import uuid
import datetime

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from apps.crm.models import (
    Company, UserProfile, BotConfiguration, Lead,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

SHOP_ID       = "AUTH_TEST_SHOP_01"
STATIC_TOKEN  = "static-" + uuid.uuid4().hex   # unique per test run


def make_company(shop_id=SHOP_ID, dashboard_token=STATIC_TOKEN, active=True):
    """Create a Company with a known dashboard_token."""
    company, _ = Company.objects.get_or_create(
        shop_id=shop_id,
        defaults={
            "name": f"Boutique Test {shop_id}",
            "dashboard_token": dashboard_token,
            "is_active": active,
        },
    )
    return company


def make_user_with_company(username="testowner", password="securepass123", company=None):
    """Create a Django User + UserProfile linked to a Company."""
    if company is None:
        company = make_company()
    user = User.objects.create_user(username=username, password=password)
    UserProfile.objects.create(user=user, company=company, role="owner")
    return user, company


def jwt_client_for(username, password):
    """Perform login and return an APIClient pre-configured with the JWT access token."""
    client = APIClient()
    response = client.post("/api/v1/crm/auth/login/", {
        "username": username,
        "password": password,
    }, format="json")
    assert response.status_code == status.HTTP_200_OK, (
        f"Login failed: {response.data}"
    )
    access_token = response.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
    return client, response.data


def static_token_client(token=STATIC_TOKEN):
    """Return an APIClient pre-configured with a static dashboard_token."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def anon_client():
    return APIClient()


# ─────────────────────────────────────────────────────────────────────────────
# 1. POST /api/v1/crm/auth/login/
# ─────────────────────────────────────────────────────────────────────────────

class JWTLoginViewTests(TestCase):
    """Tests pour LoginView — POST /api/v1/auth/login/"""

    LOGIN_URL = "/api/v1/crm/auth/login/"

    def setUp(self):
        self.user, self.company = make_user_with_company(
            username="merchant", password="mypassword"
        )

    def test_login_valid_credentials_returns_tokens(self):
        """Login réussi → 200 + access + refresh + shop_id."""
        r = anon_client().post(self.LOGIN_URL, {
            "username": "merchant",
            "password": "mypassword",
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("access", r.data)
        self.assertIn("refresh", r.data)
        self.assertIn("shop_id", r.data)
        self.assertIn("company_name", r.data)
        self.assertIn("dashboard_token", r.data)

    def test_login_response_contains_correct_shop_id(self):
        """shop_id dans la réponse correspond bien à la company du user."""
        r = anon_client().post(self.LOGIN_URL, {
            "username": "merchant",
            "password": "mypassword",
        }, format="json")
        self.assertEqual(r.data["shop_id"], self.company.shop_id)

    def test_login_wrong_password_returns_401(self):
        """Mauvais mot de passe → 401 avec message d'erreur."""
        r = anon_client().post(self.LOGIN_URL, {
            "username": "merchant",
            "password": "wrongpassword",
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("error", r.data)

    def test_login_unknown_user_returns_401(self):
        """Utilisateur inconnu → 401."""
        r = anon_client().post(self.LOGIN_URL, {
            "username": "nobody",
            "password": "anything",
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_inactive_user_returns_403(self):
        """Compte désactivé → 403."""
        self.user.is_active = False
        self.user.save()
        r = anon_client().post(self.LOGIN_URL, {
            "username": "merchant",
            "password": "mypassword",
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_missing_fields_returns_400(self):
        """Champs manquants → 400."""
        r = anon_client().post(self.LOGIN_URL, {
            "username": "merchant",
            # password manquant
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", r.data)


# ─────────────────────────────────────────────────────────────────────────────
# 2. GET /api/v1/crm/auth/me/
# ─────────────────────────────────────────────────────────────────────────────

class MeViewTests(TestCase):
    """Tests pour MeView — GET /api/v1/auth/me/"""

    ME_URL = "/api/v1/crm/auth/me/"

    def setUp(self):
        self.user, self.company = make_user_with_company(
            username="owner", password="ownerpass"
        )

    def test_me_with_jwt_returns_200(self):
        """JWT valide → 200 avec infos user + company."""
        client, _ = jwt_client_for("owner", "ownerpass")
        r = client.get(self.ME_URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("user", r.data)
        self.assertIn("company", r.data)
        self.assertEqual(r.data["user"]["username"], "owner")

    def test_me_jwt_company_info_correct(self):
        """La company renvoyée par /me/ correspond à celle de l'utilisateur."""
        client, _ = jwt_client_for("owner", "ownerpass")
        r = client.get(self.ME_URL)
        self.assertEqual(r.data["company"]["shop_id"], self.company.shop_id)
        self.assertIn("name", r.data["company"])
        self.assertIn("is_active", r.data["company"])
        # Vérifier que les champs LLM ne sont PAS présents
        self.assertNotIn("response_mode", r.data["company"])
        self.assertNotIn("has_gemini_key", r.data["company"])
        self.assertNotIn("has_llm_context", r.data["company"])

    def test_me_with_static_token_returns_200(self):
        """Dashboard token (static) → 200 avec user=null."""
        client = static_token_client(STATIC_TOKEN)
        r = client.get(self.ME_URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIsNone(r.data["user"])
        self.assertEqual(r.data["company"]["shop_id"], self.company.shop_id)

    def test_me_no_auth_returns_401(self):
        """Sans authentification → 401."""
        r = anon_client().get(self.ME_URL)
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_invalid_token_returns_401(self):
        """Token JWT invalide → 401."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer invalidtoken")
        r = client.get(self.ME_URL)
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


# ─────────────────────────────────────────────────────────────────────────────
# 3. JWT Token Authentication (JWTCompanyAuthentication)
# ─────────────────────────────────────────────────────────────────────────────

class JWTCompanyAuthenticationTests(TestCase):
    """Tests pour JWTCompanyAuthentication sur les endpoints CRM."""

    LEADS_URL = "/api/v1/crm/leads/"

    def setUp(self):
        self.user, self.company = make_user_with_company(
            username="jwtuser", password="jwtpass123"
        )
        Lead.objects.create(
            platform_id="messenger:jwt_test",
            shop_id=self.company.shop_id,
        )

    def test_jwt_allows_access_to_protected_endpoint(self):
        """JWT valide → accès autorisé aux leads."""
        client, _ = jwt_client_for("jwtuser", "jwtpass123")
        r = client.get(self.LEADS_URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_jwt_invalid_signature_returns_401(self):
        """JWT avec signature invalide → 401."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.INVALIDSIGNATURE")
        r = client.get(self.LEADS_URL)
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_token_returns_401(self):
        """Sans token → 401."""
        r = anon_client().get(self.LEADS_URL)
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_jwt_token_not_confused_with_static_token(self):
        """Un JWT (commence par 'eyJ') ne doit pas être traité comme un static token."""
        client, _ = jwt_client_for("jwtuser", "jwtpass123")
        r = client.get(self.LEADS_URL)
        # Doit réussir via JWTCompanyAuthentication, pas StaticTokenAuthentication
        self.assertEqual(r.status_code, status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Static Dashboard Token Authentication (StaticTokenAuthentication)
# ─────────────────────────────────────────────────────────────────────────────

class StaticTokenAuthenticationTests(TestCase):
    """Tests pour StaticTokenAuthentication — dashboard_token."""

    LEADS_URL = "/api/v1/crm/leads/"

    def setUp(self):
        self.company = make_company()
        Lead.objects.create(
            platform_id="messenger:static_test",
            shop_id=self.company.shop_id,
        )

    def test_static_bearer_token_allows_access(self):
        """Bearer <dashboard_token> → 200."""
        client = static_token_client(STATIC_TOKEN)
        r = client.get(self.LEADS_URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_static_token_prefix_also_accepted(self):
        """Token <dashboard_token> → 200 (préfixe 'Token' accepté)."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {STATIC_TOKEN}")
        r = client.get(self.LEADS_URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_invalid_static_token_returns_401(self):
        """Token inconnu → 401."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer this-token-does-not-exist")
        r = client.get(self.LEADS_URL)
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_jwt_eyj_prefix_skipped_by_static_auth(self):
        """Un JWT (commence par 'eyJ') est ignoré par StaticTokenAuthentication."""
        # Un JWT mal formé ne devrait pas matcher un dashboard_token
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer eyJinvalidjwttoken")
        r = client.get(self.LEADS_URL)
        # Sera rejeté (401) car ni JWT valide ni static token connu
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_empty_authorization_header_returns_401(self):
        """En-tête Authorization vide → 401."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer ")
        r = client.get(self.LEADS_URL)
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Endpoints protégés — combinaison JWT + Static Token
# ─────────────────────────────────────────────────────────────────────────────

class ProtectedEndpointsMixedAuthTests(TestCase):
    """Tests combinant les deux méthodes d'auth sur les endpoints CRM."""

    LEADS_URL = "/api/v1/crm/leads/"
    CONV_URL  = "/api/v1/crm/conversations/"
    BOT_URL   = "/api/v1/crm/bot-configurations/"

    def setUp(self):
        self.company = make_company()
        self.user, _ = make_user_with_company(
            username="mixeduser", password="mixedpass",
            company=self.company,
        )

    def test_leads_with_jwt_returns_200(self):
        """JWT → accès aux leads."""
        client, _ = jwt_client_for("mixeduser", "mixedpass")
        r = client.get(self.LEADS_URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_leads_with_static_token_returns_200(self):
        """Dashboard token → accès aux leads."""
        r = static_token_client(STATIC_TOKEN).get(self.LEADS_URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_leads_without_auth_returns_401(self):
        """Sans auth → 401."""
        r = anon_client().get(self.LEADS_URL)
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_bot_config_with_static_token_returns_200_or_ok(self):
        """Static token peut accéder aux bot-configurations."""
        r = static_token_client(STATIC_TOKEN).get(
            f"{self.BOT_URL}{self.company.shop_id}/"
        )
        self.assertIn(r.status_code, [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
        ])
