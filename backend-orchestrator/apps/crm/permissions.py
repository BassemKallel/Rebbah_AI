"""
permissions.py — Permissions spécifiques TikTak AI
"""
from rest_framework.permissions import BasePermission

class IsAdminUser(BasePermission):
    """
    Autorise uniquement les utilisateurs avec role='admin' dans UserProfile.
    Utilisé pour tous les endpoints MLOps.
    """
    message = "Accès réservé aux administrateurs MLOps."

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            return request.user.profile.role == 'admin'
        except AttributeError:
            return False
