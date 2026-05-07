"""
apps/crm/views/auth.py — JWT authentication endpoints for the merchant dashboard.

Endpoints:
    POST /api/v1/auth/login/           → Authenticate & return JWT tokens + company info
    POST /api/v1/auth/refresh/         → Refresh an expired access token
    GET  /api/v1/auth/me/              → Return current user + company info
    POST /api/v1/auth/change-password/ → Change authenticated user's password
"""
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken


class LoginView(APIView):
    """
    POST /api/v1/auth/login/

    Body: { "username": "...", "password": "..." }
    Returns: { "access", "refresh", "shop_id", "company_name", "user": {...} }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')

        if not username or not password:
            return Response(
                {'error': 'Les champs "username" et "password" sont requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response(
                {'error': 'Identifiants invalides.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {'error': 'Ce compte est désactivé.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Resolve UserProfile → Company
        try:
            profile = user.profile
            company = profile.company
        except Exception:
            return Response(
                {'error': 'Aucun profil associé à cet utilisateur.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not company and profile.role != 'admin':
            return Response(
                {'error': 'Aucune entreprise associée.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            },
            'role': profile.role,
            'shop_id': company.shop_id if company else None,
            'company_name': company.name if company else 'TikTak AI (Admin)',
            'dashboard_token': company.dashboard_token if company else None,
        })


class MeView(APIView):
    """
    GET /api/v1/auth/me/

    Returns the authenticated user info + company details.
    Works with both JWT and static token authentication.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        company = request.auth  # Company instance

        # Static token auth → user is _TikTakUser (no Django User)
        if not hasattr(user, 'profile'):
            return Response({
                'user': None,
                'company': {
                    'shop_id': company.shop_id,
                    'name': company.name,
                    'is_active': company.is_active,
                },
                'role': 'owner',
            })

        # JWT auth → full user info
        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            },
            'company': {
                'shop_id': company.shop_id,
                'name': company.name,
                'is_active': company.is_active,
            } if company else None,
            'role': user.profile.role,
        })


class ChangePasswordView(APIView):
    """
    POST /api/v1/auth/change-password/

    Body: { "current_password": "...", "new_password": "...", "confirm_password": "..." }
    Changes the authenticated user's password.
    Only available to JWT-authenticated users (not static token).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # Static token auth has no real Django user
        if not hasattr(user, 'profile'):
            return Response(
                {'error': 'Opération non disponible pour ce type d\'authentification.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        current_password = request.data.get('current_password', '')
        new_password     = request.data.get('new_password', '')
        confirm_password = request.data.get('confirm_password', '')

        if not current_password or not new_password or not confirm_password:
            return Response(
                {'error': 'Les trois champs sont requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_password != confirm_password:
            return Response(
                {'error': 'Les deux nouveaux mots de passe ne correspondent pas.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(new_password) < 8:
            return Response(
                {'error': 'Le nouveau mot de passe doit contenir au moins 8 caractères.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.check_password(current_password):
            return Response(
                {'error': 'Le mot de passe actuel est incorrect.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=['password'])

        return Response({'message': 'Mot de passe modifié avec succès.'}, status=status.HTTP_200_OK)
