"""
authentication.py — Authentication backends for DRF endpoints.

Two authentication methods, tried in order:

1. JWT (dashboard login)      → Authorization: Bearer <jwt_access_token>
2. Static token (TikTak PRO)  → Authorization: Bearer <dashboard_token>
                                 Authorization: Token <dashboard_token>

Both resolve to (user, Company) so request.auth is always a Company instance.
"""
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class _TikTakUser:
    """Lightweight authenticated principal for static-token auth."""
    is_authenticated = True
    is_anonymous     = False
    is_active        = True

    def __str__(self):
        return "tiktak-api-client"


class JWTCompanyAuthentication(BaseAuthentication):
    """
    JWT-based authentication for dashboard users.

    Validates a JWT (via simplejwt), then resolves UserProfile → Company.
    Returns (user, company) so request.auth is always a Company instance.
    """

    def authenticate(self, request):
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

        jwt_auth = JWTAuthentication()
        try:
            validated = jwt_auth.authenticate(request)
        except (InvalidToken, TokenError):
            return None
        except Exception:
            return None

        if validated is None:
            return None

        user, token = validated

        # Resolve UserProfile → Company
        try:
            profile = user.profile
            return (user, profile.company)
        except Exception:
            raise AuthenticationFailed(
                'Utilisateur authentifié mais aucun profil/company associé.'
            )

    def authenticate_header(self, request):
        return 'Bearer realm="tiktak-ai-jwt"'


class StaticTokenAuthentication(BaseAuthentication):
    """
    Static token authentication against Company.dashboard_token.

    Accepts both prefixes:
        Authorization: Bearer <dashboard_token>
        Authorization: Token <dashboard_token>

    Used by TikTak PRO platform and webhook integrations.
    """

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')

        # Extract token from either prefix
        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()
        elif auth_header.startswith('Token '):
            token = auth_header[6:].strip()
        else:
            return None

        if not token:
            return None

        # Skip JWTs (they start with "eyJ")
        if token.startswith('eyJ'):
            return None

        try:
            from apps.crm.models import Company
            company = Company.objects.get(dashboard_token=token)
            return (_TikTakUser(), company)
        except Company.DoesNotExist:
            raise AuthenticationFailed('Token invalide ou boutique introuvable.')

    def authenticate_header(self, request):
        return 'Bearer realm="tiktak-ai"'
