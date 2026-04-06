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
            company = Company.objects.get(dashboard_token=token)
            return (_TikTakUser(), company)
        except Company.DoesNotExist:
            raise AuthenticationFailed('Token invalide ou boutique introuvable.')

    def authenticate_header(self, request):
        return 'Bearer realm="tiktak-ai"'


class JWTCompanyAuthentication(BaseAuthentication):
    """
    JWT-based authentication for dashboard users.

    Validates a JWT (via simplejwt), then resolves UserProfile → Company.
    Returns (user, company) so request.auth is always a Company instance,
    matching the same interface as TikTakTokenAuthentication.

    Usage in views:
        authentication_classes = [JWTCompanyAuthentication, TikTakTokenAuthentication]
        permission_classes     = [IsAuthenticated]
    """

    def authenticate(self, request):
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

        jwt_auth = JWTAuthentication()
        try:
            validated = jwt_auth.authenticate(request)
        except (InvalidToken, TokenError):
            return None  # Not a valid JWT — fall through to next authenticator
        except Exception:
            return None

        if validated is None:
            return None

        user, token = validated

        # Resolve UserProfile → Company
        try:
            profile = user.profile  # OneToOneField reverse
            return (user, profile.company)
        except Exception:
            raise AuthenticationFailed(
                'Utilisateur authentifié mais aucun profil/company associé.'
            )

    def authenticate_header(self, request):
        return 'Bearer realm="tiktak-ai-jwt"'


class DashboardTokenAuthentication(BaseAuthentication):
    """
    Static token authentication for dashboard access.

    Validates Authorization: Token <dashboard_token> against Company.dashboard_token.
    Used by TikTak PRO platform to integrate with the dashboard API
    without requiring JWT login flow.

    Usage in views:
        authentication_classes = [JWTCompanyAuthentication, DashboardTokenAuthentication, TikTakTokenAuthentication]
    """

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Token '):
            return None  # Not our scheme

        token = auth_header[len('Token '):].strip()
        if not token:
            raise AuthenticationFailed('Token manquant après "Token".')

        try:
            from apps.crm.models import Company
            company = Company.objects.get(dashboard_token=token)
            return (_TikTakUser(), company)
        except Company.DoesNotExist:
            raise AuthenticationFailed('Dashboard token invalide.')

    def authenticate_header(self, request):
        return 'Token realm="tiktak-ai-dashboard"'

