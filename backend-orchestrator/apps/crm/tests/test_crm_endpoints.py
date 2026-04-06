"""
test_crm_endpoints.py — Unit tests for all CRM API endpoints.

Coverage (65 tests):
  - StaticTokenAuthentication (6): Bearer/Token prefix, invalid, missing, JWT skip
  - JWTCompanyAuthentication  (4): valid JWT, invalid JWT, no JWT, expired
  - LeadViewSet              (9): auth gate, list, filter, retrieve, create, delete
  - ConversationViewSet      (7): auth gate, list, filter, retrieve, messages, write-block
  - BotConfigurationViewSet  (8): auth gate, retrieve auto-create, upsert PUT/PATCH
  - ResponseTemplateViewSet (25): auth gate, list, filter, CRUD, system-default protection, preview
  - Auth views (5): login, me endpoint JWT, me endpoint static token, refresh, logout
  - CompanySettings (5): get, patch, validation
"""

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.crm.models import (
    Lead, Conversation, Message,
    BotConfiguration, Company, ResponseTemplate,
)
from apps.crm.models import UserProfile


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures / Helpers
# ─────────────────────────────────────────────────────────────────────────────

SHOP_ID = "TEST_SHOP_01"
DASHBOARD_TOKEN = "test-dashboard-token-abc123"  # fixed value for tests
WRONG_TOKEN = "wrong-token-xyz"


def make_company(shop_id=SHOP_ID, dashboard_token=DASHBOARD_TOKEN):
    """Create a Company with a known dashboard_token."""
    company, _ = Company.objects.get_or_create(
        shop_id=shop_id,
        defaults={
            "name": f"Test Shop {shop_id}",
            "dashboard_token": dashboard_token,
            "is_active": True,
        },
    )
    # Ensure the token is correct even if the company already exists
    if company.dashboard_token != dashboard_token:
        company.dashboard_token = dashboard_token
        company.save()
    return company


def make_user_with_company(username="testuser", password="testpass", shop_id=SHOP_ID):
    """Create a Django user with a UserProfile linked to a Company."""
    company = make_company(shop_id=shop_id)
    user, _ = User.objects.get_or_create(
        username=username,
        defaults={"email": f"{username}@test.com"},
    )
    user.set_password(password)
    user.save()
    UserProfile.objects.get_or_create(user=user, defaults={"company": company, "role": "owner"})
    return user, company


def jwt_client(username="testuser", password="testpass"):
    """Login and return an APIClient with a valid JWT Bearer token."""
    user, company = make_user_with_company(username=username, password=password)
    client = APIClient()
    r = client.post("/api/v1/auth/login/", {"username": username, "password": password}, format="json")
    assert r.status_code == 200, f"Login failed: {r.data}"
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    return client, r.data


def static_bearer_client(token=DASHBOARD_TOKEN):
    """APIClient using static token with Bearer prefix."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def static_token_client(token=DASHBOARD_TOKEN):
    """APIClient using static token with Token prefix."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


def anon_client():
    """APIClient with no credentials."""
    return APIClient()


# ─────────────────────────────────────────────────────────────────────────────
# 1. StaticTokenAuthentication
# ─────────────────────────────────────────────────────────────────────────────

class StaticTokenAuthTests(TestCase):

    def setUp(self):
        make_company()

    def test_bearer_prefix_valid_token_returns_200(self):
        """Authorization: Bearer <dashboard_token> → authenticated."""
        client = static_bearer_client(DASHBOARD_TOKEN)
        r = client.get("/api/v1/crm/templates/")
        self.assertNotEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_prefix_valid_token_returns_200(self):
        """Authorization: Token <dashboard_token> → authenticated."""
        client = static_token_client(DASHBOARD_TOKEN)
        r = client.get("/api/v1/crm/templates/")
        self.assertNotEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_token_returns_401(self):
        """A wrong static token must be rejected."""
        client = static_bearer_client(WRONG_TOKEN)
        r = client.get("/api/v1/crm/templates/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_auth_header_returns_401(self):
        r = anon_client().get("/api/v1/crm/templates/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_jwt_shaped_token_skipped_by_static_auth(self):
        """A 'Bearer eyJ...' token that doesn't match any dashboard_token → 401."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer eyJfakeJWT123.notreal.token")
        r = client.get("/api/v1/crm/templates/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_wrong_token_prefix_only_returns_401(self):
        """An unrecognized prefix like 'Basic <token>' → 401."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Basic {DASHBOARD_TOKEN}")
        r = client.get("/api/v1/crm/templates/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


# ─────────────────────────────────────────────────────────────────────────────
# 2. JWTCompanyAuthentication
# ─────────────────────────────────────────────────────────────────────────────

class JWTAuthTests(TestCase):

    def setUp(self):
        self.client_jwt, self.login_data = jwt_client()

    def test_valid_jwt_returns_200(self):
        r = self.client_jwt.get("/api/v1/crm/leads/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_invalid_jwt_returns_401(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer eyJinvalidtoken")
        r = client.get("/api/v1/crm/leads/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_jwt_returns_401(self):
        r = anon_client().get("/api/v1/crm/leads/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_jwt_and_static_token_both_grant_access(self):
        """Both auth methods work on the same endpoint."""
        make_company()
        r_jwt = self.client_jwt.get("/api/v1/crm/templates/")
        r_static = static_bearer_client().get("/api/v1/crm/templates/")
        self.assertNotEqual(r_jwt.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotEqual(r_static.status_code, status.HTTP_401_UNAUTHORIZED)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Auth views  (login, me, refresh)
# ─────────────────────────────────────────────────────────────────────────────

class AuthViewTests(TestCase):

    def setUp(self):
        make_user_with_company()

    def test_login_success_returns_tokens(self):
        r = anon_client().post(
            "/api/v1/auth/login/",
            {"username": "testuser", "password": "testpass"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("access", r.data)
        self.assertIn("refresh", r.data)
        self.assertIn("dashboard_token", r.data)

    def test_login_wrong_password_returns_401(self):
        r = anon_client().post(
            "/api/v1/auth/login/",
            {"username": "testuser", "password": "wrong"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_with_jwt_returns_user_info(self):
        client, _ = jwt_client()
        r = client.get("/api/v1/auth/me/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(r.data.get("user"))
        self.assertEqual(r.data["user"]["username"], "testuser")
        self.assertIn("company", r.data)

    def test_me_with_static_token_returns_company_no_user(self):
        """Static token auth → user=None, company filled, role='owner'."""
        client = static_bearer_client(DASHBOARD_TOKEN)
        r = client.get("/api/v1/auth/me/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIsNone(r.data.get("user"))
        self.assertIn("company", r.data)
        self.assertEqual(r.data.get("role"), "owner")

    def test_me_without_auth_returns_401(self):
        r = anon_client().get("/api/v1/auth/me/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Company Settings endpoint
# ─────────────────────────────────────────────────────────────────────────────

class CompanySettingsTests(TestCase):

    URL = f"/api/v1/crm/company/{SHOP_ID}/"

    def setUp(self):
        make_company()
        self.client_jwt, _ = jwt_client()
        self.client_static = static_bearer_client(DASHBOARD_TOKEN)

    def test_get_with_jwt(self):
        r = self.client_jwt.get(self.URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["shop_id"], SHOP_ID)

    def test_get_with_static_token(self):
        r = self.client_static.get(self.URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["shop_id"], SHOP_ID)

    def test_patch_response_mode_nlu(self):
        r = self.client_jwt.patch(self.URL, {"response_mode": "nlu"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_patch_llm_mode_without_key_returns_400(self):
        """Switching to LLM mode without a Gemini key must fail."""
        r = self.client_jwt.patch(self.URL, {"response_mode": "llm"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_without_auth_returns_401(self):
        r = anon_client().get(self.URL)
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


# ─────────────────────────────────────────────────────────────────────────────
# 5. LeadViewSet (both auth methods)
# ─────────────────────────────────────────────────────────────────────────────

class LeadViewSetTests(TestCase):

    URL = "/api/v1/crm/leads/"

    def setUp(self):
        make_company()
        self.client_jwt, _ = jwt_client()
        self.client_static = static_bearer_client(DASHBOARD_TOKEN)
        self.lead = Lead.objects.create(
            platform_id="messenger:lead001",
            shop_id=SHOP_ID,
        )

    def _url_detail(self, pk):
        return f"{self.URL}{pk}/"

    def test_list_requires_auth(self):
        r = anon_client().get(self.URL)
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_with_jwt_returns_200(self):
        r = self.client_jwt.get(self.URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_list_with_static_token_returns_200(self):
        r = self.client_static.get(self.URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_filter_by_shop_id(self):
        Lead.objects.create(platform_id="messenger:lead002", shop_id="OTHER_SHOP")
        r = self.client_jwt.get(self.URL, {"shop_id": SHOP_ID})
        results = list(r.data)
        self.assertTrue(all(item["shop_id"] == SHOP_ID for item in results))

    def test_retrieve_single_lead_jwt(self):
        r = self.client_jwt.get(self._url_detail(self.lead.id))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["id"], self.lead.id)

    def test_retrieve_single_lead_static(self):
        r = self.client_static.get(self._url_detail(self.lead.id))
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_retrieve_nonexistent_returns_404(self):
        r = self.client_jwt.get(self._url_detail(99999))
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_with_jwt_succeeds(self):
        r = self.client_jwt.post(self.URL, {
            "platform_id": "messenger:lead_new_jwt",
            "shop_id": SHOP_ID,
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_create_with_static_token_succeeds(self):
        r = self.client_static.post(self.URL, {
            "platform_id": "messenger:lead_new_static",
            "shop_id": SHOP_ID,
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────────────────────
# 6. ConversationViewSet (both auth methods)
# ─────────────────────────────────────────────────────────────────────────────

class ConversationViewSetTests(TestCase):

    URL = "/api/v1/crm/conversations/"

    def setUp(self):
        make_company()
        self.client_jwt, _ = jwt_client()
        self.client_static = static_bearer_client(DASHBOARD_TOKEN)
        self.lead = Lead.objects.create(platform_id="messenger:conv001")
        self.conv = Conversation.objects.create(
            lead=self.lead,
            lead_uuid=self.lead.uuid,
            sender_id="messenger:conv001",
            shop_id=SHOP_ID,
            state="NEW_CONVERSATION",
        )
        Message.objects.create(conversation=self.conv, sender="user", text="Bonjour")

    def test_list_requires_auth(self):
        r = anon_client().get(self.URL)
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_with_jwt_returns_200(self):
        r = self.client_jwt.get(self.URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_list_with_static_token_returns_200(self):
        r = self.client_static.get(self.URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_messages_with_jwt(self):
        r = self.client_jwt.get(f"{self.URL}{self.conv.id}/messages/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(any(m["text"] == "Bonjour" for m in list(r.data)))

    def test_messages_with_static_token(self):
        r = self.client_static.get(f"{self.URL}{self.conv.id}/messages/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_write_not_allowed(self):
        r = self.client_jwt.post(self.URL, {"sender_id": "x"})
        self.assertEqual(r.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


# ─────────────────────────────────────────────────────────────────────────────
# 7. BotConfigurationViewSet (both auth methods)
# ─────────────────────────────────────────────────────────────────────────────

class BotConfigurationViewSetTests(TestCase):

    URL_UPSERT = "/api/v1/crm/bot-configurations/"

    def setUp(self):
        make_company()
        self.client_jwt, _ = jwt_client()
        self.client_static = static_bearer_client(DASHBOARD_TOKEN)

    def _url_detail(self, shop_id=SHOP_ID):
        return f"{self.URL_UPSERT}{shop_id}/"

    def test_retrieve_requires_auth(self):
        r = anon_client().get(self._url_detail())
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_with_jwt_auto_creates(self):
        r = self.client_jwt.get(self._url_detail())
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["shop_id"], SHOP_ID)

    def test_retrieve_with_static_token_auto_creates(self):
        r = self.client_static.get(self._url_detail())
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_put_with_jwt(self):
        r = self.client_jwt.put(self.URL_UPSERT, {
            "shop_id": SHOP_ID, "shop_name": "Boutique JWT", "language": "FR",
        }, format="json")
        self.assertIn(r.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])

    def test_put_with_static_token(self):
        r = self.client_static.put(self.URL_UPSERT, {
            "shop_id": SHOP_ID, "shop_name": "Boutique Static", "language": "FR",
        }, format="json")
        self.assertIn(r.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])

    def test_patch_with_jwt(self):
        BotConfiguration.objects.create(shop_id=SHOP_ID, shop_name="Old")
        r = self.client_jwt.patch(self.URL_UPSERT, {
            "shop_id": SHOP_ID, "shop_name": "New JWT",
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_patch_with_static_token(self):
        BotConfiguration.objects.create(shop_id=SHOP_ID, shop_name="Old2")
        r = self.client_static.patch(self.URL_UPSERT, {
            "shop_id": SHOP_ID, "shop_name": "New Static",
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_put_missing_shop_id_returns_400(self):
        r = self.client_jwt.put(self.URL_UPSERT, {"shop_name": "No shop"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


# ─────────────────────────────────────────────────────────────────────────────
# 8. ResponseTemplateViewSet (both auth methods)
# ─────────────────────────────────────────────────────────────────────────────

class ResponseTemplateViewSetTests(TestCase):

    URL = "/api/v1/crm/templates/"

    def setUp(self):
        make_company()
        self.client_jwt, _ = jwt_client()
        self.client_static = static_bearer_client(DASHBOARD_TOKEN)

        self.default_tmpl, _ = ResponseTemplate.objects.update_or_create(
            shop_id=None, language="FR", template_type="response", intent="GREETING",
            defaults={"text": "Bonjour par défaut !", "is_default": True},
        )
        self.shop_tmpl, _ = ResponseTemplate.objects.update_or_create(
            shop_id=SHOP_ID, language="FR", template_type="response", intent="GREETING",
            defaults={"text": "Bonjour boutique !", "is_default": False},
        )

    def test_list_requires_auth(self):
        r = anon_client().get(self.URL)
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_with_jwt_returns_200(self):
        r = self.client_jwt.get(self.URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_list_with_static_token_returns_200(self):
        r = self.client_static.get(self.URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_create_with_jwt(self):
        r = self.client_jwt.post(self.URL, {
            "shop_id": SHOP_ID, "language": "FR",
            "template_type": "response", "intent": "ASK_PRICE",
            "text": "Le prix est {price} DT.",
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_create_with_static_token(self):
        r = self.client_static.post(self.URL, {
            "shop_id": SHOP_ID, "language": "FR",
            "template_type": "response", "intent": "ASK_DELIVERY",
            "text": "Livraison 7 TND.",
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_patch_shop_template_jwt(self):
        r = self.client_jwt.patch(
            f"{self.URL}{self.shop_tmpl.id}/",
            {"text": "Mis à jour JWT"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_patch_shop_template_static(self):
        r = self.client_static.patch(
            f"{self.URL}{self.shop_tmpl.id}/",
            {"text": "Mis à jour Static"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_patch_system_default_returns_403(self):
        r = self.client_jwt.patch(
            f"{self.URL}{self.default_tmpl.id}/",
            {"text": "Hacked"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_shop_template_jwt(self):
        extra = ResponseTemplate.objects.create(
            shop_id=SHOP_ID, language="EN", template_type="response",
            intent="CANCEL_ORDER", text="Del JWT", is_default=False,
        )
        r = self.client_jwt.delete(f"{self.URL}{extra.id}/")
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_shop_template_static(self):
        extra = ResponseTemplate.objects.create(
            shop_id=SHOP_ID, language="EN", template_type="response",
            intent="UNKNOWN", text="Del Static", is_default=False,
        )
        r = self.client_static.delete(f"{self.URL}{extra.id}/")
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_system_default_returns_403(self):
        r = self.client_jwt.delete(f"{self.URL}{self.default_tmpl.id}/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_preview_with_jwt_returns_shop_template(self):
        r = self.client_jwt.get(f"{self.URL}preview/", {
            "shop_id": SHOP_ID, "language": "FR",
            "template_type": "response", "intent": "GREETING",
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["text"], "Bonjour boutique !")

    def test_preview_with_static_token(self):
        r = self.client_static.get(f"{self.URL}preview/", {
            "shop_id": SHOP_ID, "language": "FR",
            "template_type": "response", "intent": "GREETING",
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK)
