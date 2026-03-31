"""
authentication.py — TikTak per-shop token authentication for DRF endpoints.

Expected header:
    Authorization: Bearer <tiktak_api_token>

The token must match Company.tiktak_api_token stored in the DB.
This is the same token the shop owner receives when logging into the TikTak dashboard.

If valid   → request.user = _TikTakUser(), request.auth = Company instance
If invalid → 401 AuthenticationFailed
"""
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class _TikTakUser:
    """Lightweight authenticated principal representing a TikTak shop owner."""
    is_authenticated = True
    is_anonymous     = False
    is_active        = True

    def __str__(self):
        return "tiktak-api-client"


class TikTakTokenAuthentication(BaseAuthentication):
    """
    Validates Authorization: Bearer <tiktak_api_token> against Company.tiktak_api_token.

    Usage in views:
        authentication_classes = [TikTakTokenAuthentication]
        permission_classes     = [IsAuthenticated]
    """

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return None  # Not our scheme — DRF will return 401 via permission check

        token = auth_header[len('Bearer '):].strip()
        if not token:
            raise AuthenticationFailed('Token manquant après "Bearer".')

        # Lookup company by token — the only valid source of truth
        try:
            from apps.crm.models import Company
            company = Company.objects.get(tiktak_api_token=token)
            return (_TikTakUser(), company)
        except Company.DoesNotExist:
            raise AuthenticationFailed('Token TikTak invalide ou boutique introuvable.')

    def authenticate_header(self, request):
        return 'Bearer realm="tiktak-ai"'

