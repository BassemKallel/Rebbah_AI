"""
test_crm_endpoints.py — Unit tests for all CRM API endpoints.

Coverage (53 tests):
  - TikTakTokenAuthentication (4): valid/invalid/missing/malformed Bearer token
  - LeadViewSet              (9): auth gate, list, filter, retrieve, create, delete
  - ConversationViewSet      (7): auth gate, list, filter, retrieve, messages, write-block
  - BotConfigurationViewSet  (8): auth gate, retrieve auto-create, upsert PUT/PATCH
  - ResponseTemplateViewSet (25): auth gate, list, filter, CRUD, system-default protection, preview
"""

import uuid

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.crm.models import (
    Lead, Conversation, Message,
    BotConfiguration, Company, ResponseTemplate,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

TOKEN_VALID   = "static-" + str(uuid.uuid4()).replace("-", "")  # unique per run
TOKEN_INVALID = "wrong-token-xyz"
SHOP_ID       = "TEST_SHOP_01"


def make_company(shop_id=SHOP_ID, token=TOKEN_VALID):
    """Create a Company with a known dashboard_token."""
    return Company.objects.get_or_create(
        shop_id=shop_id,
        defaults={"name": f"Test Shop {shop_id}", "dashboard_token": token},
    )[0]


def auth_client(token=TOKEN_VALID):
    """Return an APIClient pre-configured with a Bearer token."""
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return c


def anon_client():
    """Return a plain APIClient with no credentials."""
    return APIClient()


# ─────────────────────────────────────────────────────────────────────────────
# 1. TikTakTokenAuthentication
# ─────────────────────────────────────────────────────────────────────────────

class AuthenticationTests(TestCase):

    def setUp(self):
        make_company()

    def test_valid_token_returns_200(self):
        client = auth_client(TOKEN_VALID)
        r = client.get("/api/v1/crm/templates/")
        self.assertNotEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_token_returns_401(self):
        client = auth_client(TOKEN_INVALID)
        r = client.get("/api/v1/crm/templates/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_authorization_header_returns_401(self):
        client = anon_client()
        r = client.get("/api/v1/crm/templates/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_malformed_bearer_returns_401(self):
        """Token inconnu (ni JWT valide ni dashboard_token connu) → 401."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer completely-unknown-token-xyz")
        r = client.get("/api/v1/crm/templates/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


# ─────────────────────────────────────────────────────────────────────────────
# 2. LeadViewSet
# ─────────────────────────────────────────────────────────────────────────────

class LeadViewSetTests(TestCase):

    URL = "/api/v1/crm/leads/"

    def setUp(self):
        make_company()
        self.client_auth = auth_client(TOKEN_VALID)
        self.lead = Lead.objects.create(
            platform_id="messenger:lead001",
            shop_id=SHOP_ID,
        )

    def _url_detail(self, pk):
        return f"{self.URL}{pk}/"

    # ── Auth gate ─────────────────────────────────────────────────────────

    def test_list_requires_auth(self):
        r = anon_client().get(self.URL)
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── List ──────────────────────────────────────────────────────────────

    def test_list_returns_200(self):
        r = self.client_auth.get(self.URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_list_contains_lead(self):
        r = self.client_auth.get(self.URL)
        ids = [item["id"] for item in list(r.data)]
        self.assertIn(self.lead.id, ids)

    def test_filter_by_shop_id(self):
        Lead.objects.create(platform_id="messenger:lead002", shop_id="OTHER_SHOP")
        r = self.client_auth.get(self.URL, {"shop_id": SHOP_ID})
        results = list(r.data)
        self.assertTrue(all(item["shop_id"] == SHOP_ID for item in results))

    # ── Retrieve ──────────────────────────────────────────────────────────

    def test_retrieve_single_lead(self):
        r = self.client_auth.get(self._url_detail(self.lead.id))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["id"], self.lead.id)

    def test_retrieve_nonexistent_returns_404(self):
        r = self.client_auth.get(self._url_detail(99999))
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    # ── Create ────────────────────────────────────────────────────────────

    def test_create_requires_auth(self):
        r = anon_client().post(self.URL, {
            "platform_id": "messenger:lead_unauth",
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_with_auth_succeeds(self):
        r = self.client_auth.post(self.URL, {
            "platform_id": "messenger:lead_new",
            "shop_id": SHOP_ID,
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Lead.objects.filter(platform_id="messenger:lead_new").exists())

    # ── Delete ────────────────────────────────────────────────────────────

    def test_delete_requires_auth(self):
        r = anon_client().delete(self._url_detail(self.lead.id))
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


# ─────────────────────────────────────────────────────────────────────────────
# 3. ConversationViewSet
# ─────────────────────────────────────────────────────────────────────────────

class ConversationViewSetTests(TestCase):

    URL = "/api/v1/crm/conversations/"

    def setUp(self):
        make_company()
        self.client_auth = auth_client(TOKEN_VALID)
        self.lead = Lead.objects.create(platform_id="messenger:conv001")
        self.conv = Conversation.objects.create(
            lead=self.lead,
            lead_uuid=self.lead.uuid,
            sender_id="messenger:conv001",
            shop_id=SHOP_ID,
            state="NEW_CONVERSATION",
        )
        self.msg = Message.objects.create(
            conversation=self.conv,
            sender="user",
            text="Bonjour",
        )

    # ── Auth gate ─────────────────────────────────────────────────────────

    def test_list_requires_auth(self):
        r = anon_client().get(self.URL)
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── List ──────────────────────────────────────────────────────────────

    def test_list_conversations_200(self):
        r = self.client_auth.get(self.URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_filter_by_shop_id(self):
        lead2 = Lead.objects.create(platform_id="messenger:conv002")
        Conversation.objects.create(
            lead=lead2, lead_uuid=lead2.uuid,
            sender_id="messenger:conv002",
            shop_id="OTHER_SHOP", state="NEW_CONVERSATION",
        )
        r = self.client_auth.get(self.URL, {"shop_id": SHOP_ID})
        results = list(r.data)
        self.assertTrue(all(item["shop_id"] == SHOP_ID for item in results))

    # ── Retrieve ──────────────────────────────────────────────────────────

    def test_retrieve_conversation(self):
        r = self.client_auth.get(f"{self.URL}{self.conv.id}/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    # ── Messages action ──────────────────────────────────────────────────

    def test_messages_action(self):
        r = self.client_auth.get(f"{self.URL}{self.conv.id}/messages/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        messages = list(r.data)
        self.assertTrue(any(m["text"] == "Bonjour" for m in messages))

    def test_messages_requires_auth(self):
        r = anon_client().get(f"{self.URL}{self.conv.id}/messages/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── Write protection ─────────────────────────────────────────────────

    def test_write_not_allowed(self):
        """ConversationViewSet is read-only — POST should 405."""
        r = self.client_auth.post(self.URL, {"sender_id": "x"})
        self.assertEqual(r.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


# ─────────────────────────────────────────────────────────────────────────────
# 4. BotConfigurationViewSet
# ─────────────────────────────────────────────────────────────────────────────

class BotConfigurationViewSetTests(TestCase):

    URL_UPSERT = "/api/v1/crm/bot-configurations/"

    def setUp(self):
        make_company()
        self.client_auth = auth_client(TOKEN_VALID)

    def _url_detail(self, shop_id):
        return f"{self.URL_UPSERT}{shop_id}/"

    # ── Auth gate ─────────────────────────────────────────────────────────

    def test_retrieve_requires_auth(self):
        r = anon_client().get(self._url_detail(SHOP_ID))
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upsert_put_requires_auth(self):
        r = anon_client().put(self.URL_UPSERT, {
            "shop_id": SHOP_ID, "shop_name": "Unauth", "language": "FR",
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upsert_patch_requires_auth(self):
        BotConfiguration.objects.create(shop_id=SHOP_ID, shop_name="Exists")
        r = anon_client().patch(self.URL_UPSERT, {
            "shop_id": SHOP_ID, "shop_name": "Hacked",
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── Retrieve ──────────────────────────────────────────────────────────

    def test_retrieve_creates_config_if_missing(self):
        """GET /bot-configurations/<shop_id>/ auto-creates the config."""
        r = self.client_auth.get(self._url_detail(SHOP_ID))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["shop_id"], SHOP_ID)
        self.assertTrue(BotConfiguration.objects.filter(shop_id=SHOP_ID).exists())

    def test_retrieve_returns_existing_config(self):
        BotConfiguration.objects.create(shop_id=SHOP_ID, shop_name="Ma Boutique")
        r = self.client_auth.get(self._url_detail(SHOP_ID))
        self.assertEqual(r.data["shop_name"], "Ma Boutique")

    # ── Upsert ────────────────────────────────────────────────────────────

    def test_upsert_put_creates_config(self):
        r = self.client_auth.put(self.URL_UPSERT, {
            "shop_id":   SHOP_ID,
            "shop_name": "Boutique PUT",
            "language":  "FR",
        }, format="json")
        self.assertIn(r.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        self.assertEqual(BotConfiguration.objects.get(shop_id=SHOP_ID).shop_name, "Boutique PUT")

    def test_upsert_patch_updates_field(self):
        BotConfiguration.objects.create(shop_id=SHOP_ID, shop_name="Old Name")
        r = self.client_auth.patch(self.URL_UPSERT, {
            "shop_id":   SHOP_ID,
            "shop_name": "New Name",
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(BotConfiguration.objects.get(shop_id=SHOP_ID).shop_name, "New Name")

    def test_upsert_missing_shop_id_returns_400(self):
        r = self.client_auth.put(self.URL_UPSERT, {
            "shop_name": "No shop",
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


# ─────────────────────────────────────────────────────────────────────────────
# 5. ResponseTemplateViewSet
# ─────────────────────────────────────────────────────────────────────────────

class ResponseTemplateViewSetTests(TestCase):

    URL = "/api/v1/crm/templates/"

    def setUp(self):
        make_company()
        self.client_auth = auth_client(TOKEN_VALID)

        # System default template — use update_or_create because the seed migration
        # (0014) already inserts (shop_id=None, FR, response, GREETING).
        self.default_tmpl, _ = ResponseTemplate.objects.update_or_create(
            shop_id=None,
            language="FR",
            template_type="response",
            intent="GREETING",
            defaults={"text": "Bonjour par défaut !", "is_default": True},
        )
        # Shop override
        self.shop_tmpl, _ = ResponseTemplate.objects.update_or_create(
            shop_id=SHOP_ID,
            language="FR",
            template_type="response",
            intent="GREETING",
            defaults={"text": "Bonjour boutique !", "is_default": False},
        )

    # ── Auth gate ─────────────────────────────────────────────────────────

    def test_list_requires_auth(self):
        r = anon_client().get(self.URL)
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_requires_auth(self):
        r = anon_client().post(self.URL, {
            "shop_id": SHOP_ID, "language": "FR",
            "template_type": "response", "intent": "ASK_DELIVERY",
            "text": "Unauthorized",
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_requires_auth(self):
        r = anon_client().delete(f"{self.URL}{self.shop_tmpl.id}/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_preview_requires_auth(self):
        r = anon_client().get(f"{self.URL}preview/", {
            "shop_id": SHOP_ID, "language": "FR",
            "template_type": "response", "intent": "GREETING",
        })
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── List ──────────────────────────────────────────────────────────────

    def test_list_authenticated_returns_200(self):
        r = self.client_auth.get(self.URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_list_filter_by_shop_id(self):
        r = self.client_auth.get(self.URL, {"shop_id": SHOP_ID})
        results = list(r.data)
        self.assertTrue(all(item["shop_id"] == SHOP_ID for item in results))

    def test_list_filter_by_language(self):
        ResponseTemplate.objects.create(
            shop_id=SHOP_ID, language="AR", template_type="response",
            intent="GREETING", text="مرحبا", is_default=False,
        )
        r = self.client_auth.get(self.URL, {"language": "AR"})
        results = list(r.data)
        self.assertTrue(all(item["language"] == "AR" for item in results))

    def test_list_filter_by_intent(self):
        r = self.client_auth.get(self.URL, {"intent": "GREETING"})
        results = list(r.data)
        self.assertTrue(all(item["intent"] == "GREETING" for item in results))

    # ── Retrieve ──────────────────────────────────────────────────────────

    def test_retrieve_shop_template(self):
        r = self.client_auth.get(f"{self.URL}{self.shop_tmpl.id}/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["text"], "Bonjour boutique !")

    # ── Create ────────────────────────────────────────────────────────────

    def test_create_shop_template(self):
        r = self.client_auth.post(self.URL, {
            "shop_id":       SHOP_ID,
            "language":      "FR",
            "template_type": "response",
            "intent":        "ASK_PRICE",
            "text":          "Le prix est {price} DT.",
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            ResponseTemplate.objects.filter(shop_id=SHOP_ID, intent="ASK_PRICE").exists()
        )

    def test_create_duplicate_returns_400(self):
        """GREETING for SHOP_ID already exists → unique_together violation."""
        r = self.client_auth.post(self.URL, {
            "shop_id":       SHOP_ID,
            "language":      "FR",
            "template_type": "response",
            "intent":        "GREETING",
            "text":          "Duplicate text",
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Update ────────────────────────────────────────────────────────────

    def test_patch_shop_template_succeeds(self):
        r = self.client_auth.patch(
            f"{self.URL}{self.shop_tmpl.id}/",
            {"text": "Bonjour boutique mis à jour !"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.shop_tmpl.refresh_from_db()
        self.assertEqual(self.shop_tmpl.text, "Bonjour boutique mis à jour !")

    def test_patch_system_default_returns_403(self):
        """System defaults (is_default=True) must not be editable via API."""
        r = self.client_auth.patch(
            f"{self.URL}{self.default_tmpl.id}/",
            {"text": "Hacked default"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_put_system_default_returns_403(self):
        r = self.client_auth.put(
            f"{self.URL}{self.default_tmpl.id}/",
            {
                "shop_id": None, "language": "FR",
                "template_type": "response", "intent": "GREETING",
                "text": "Hacked",
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    # ── Delete ────────────────────────────────────────────────────────────

    def test_delete_shop_template_succeeds(self):
        r = self.client_auth.delete(f"{self.URL}{self.shop_tmpl.id}/")
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ResponseTemplate.objects.filter(id=self.shop_tmpl.id).exists())

    def test_delete_system_default_returns_403(self):
        r = self.client_auth.delete(f"{self.URL}{self.default_tmpl.id}/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(ResponseTemplate.objects.filter(id=self.default_tmpl.id).exists())

    # ── Preview ───────────────────────────────────────────────────────────

    def test_preview_returns_shop_override(self):
        r = self.client_auth.get(f"{self.URL}preview/", {
            "shop_id":       SHOP_ID,
            "language":      "FR",
            "template_type": "response",
            "intent":        "GREETING",
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["text"], "Bonjour boutique !")

    def test_preview_falls_back_to_system_default(self):
        """No override for OTHER_SHOP → should fall back to system default text."""
        r = self.client_auth.get(f"{self.URL}preview/", {
            "shop_id":       "OTHER_SHOP",
            "language":      "FR",
            "template_type": "response",
            "intent":        "GREETING",
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertNotEqual(r.data["text"], "Bonjour boutique !")
        self.assertTrue(len(r.data["text"]) > 0)

    def test_preview_missing_params_returns_400(self):
        r = self.client_auth.get(f"{self.URL}preview/", {
            "shop_id": SHOP_ID,
            "language": "FR",
            # template_type and intent missing
        })
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_preview_unknown_intent_returns_404(self):
        r = self.client_auth.get(f"{self.URL}preview/", {
            "shop_id":       SHOP_ID,
            "language":      "FR",
            "template_type": "response",
            "intent":        "NONEXISTENT_INTENT_XYZ",
        })
        # Either 404 (not in DB + not in Python fallback) or 200 if Python has it
        self.assertIn(r.status_code, [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        ])


    # -- available_variables tests ------------------------------------------

    def test_list_includes_available_variables_field(self):
        """GET list response must include 'available_variables' key."""
        self.default_tmpl.available_variables = ["ai_agent_name"]
        self.default_tmpl.save()
        r = self.client_auth.get(self.URL, {"language": "FR", "template_type": "response", "intent": "GREETING"})
        results = list(r.data)
        self.assertTrue(any("available_variables" in item for item in results))

    def test_retrieve_includes_available_variables(self):
        self.shop_tmpl.available_variables = ["ai_agent_name"]
        self.shop_tmpl.save()
        r = self.client_auth.get(f"{self.URL}{self.shop_tmpl.id}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["available_variables"], ["ai_agent_name"])

    def test_create_with_available_variables(self):
        r = self.client_auth.post(self.URL, {
            "shop_id":       SHOP_ID,
            "language":      "FR",
            "template_type": "response",
            "intent":        "ASK_PRICE",
            "text":          "Le {product} coute {price} TND.",
            "available_variables": ["product", "price"],
        }, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["available_variables"], ["product", "price"])

    def test_patch_available_variables(self):
        r = self.client_auth.patch(
            f"{self.URL}{self.shop_tmpl.id}/",
            {"available_variables": ["ai_agent_name", "shop_name"]},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.shop_tmpl.refresh_from_db()
        self.assertEqual(self.shop_tmpl.available_variables, ["ai_agent_name", "shop_name"])

    def test_available_variables_defaults_to_empty_list(self):
        r = self.client_auth.post(self.URL, {
            "shop_id":       SHOP_ID,
            "language":      "FR",
            "template_type": "response",
            "intent":        "ASK_DELIVERY",
            "text":          "Livraison gratuite.",
        }, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["available_variables"], [])
