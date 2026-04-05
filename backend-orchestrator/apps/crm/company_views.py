"""
company_views.py — Company LLM settings API endpoint.

GET  /api/v1/crm/company/{shop_id}/  → Retrieve LLM settings
PATCH /api/v1/crm/company/{shop_id}/ → Update response_mode, gemini_api_key, llm_context
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Company
from .serializers import CompanySettingsSerializer
from .authentication import JWTCompanyAuthentication, TikTakTokenAuthentication


class CompanySettingsView(APIView):
    """
    Retrieve and update Company LLM settings.

    Guards:
    - Cannot switch to LLM mode if llm_context is empty
    - Cannot switch to LLM mode if gemini_api_key is missing
    - llm_context max 10,000 characters
    """
    authentication_classes = [JWTCompanyAuthentication, TikTakTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, shop_id):
        company = get_object_or_404(Company, shop_id=shop_id, is_active=True)
        serializer = CompanySettingsSerializer(company)
        return Response(serializer.data)

    def patch(self, request, shop_id):
        company = get_object_or_404(Company, shop_id=shop_id, is_active=True)
        serializer = CompanySettingsSerializer(company, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
