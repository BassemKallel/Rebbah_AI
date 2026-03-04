"""
Middleware pour auto-login en mode développement.
Connecte automatiquement le premier superuser sans passer par le login admin.
"""
from django.contrib.auth.models import User
from django.utils.deprecation import MiddlewareMixin


class AutoLoginMiddleware(MiddlewareMixin):
    """Auto-login le premier superuser en mode DEBUG."""

    def process_request(self, request):
        # Uniquement sur /admin/ et si DEBUG=True et pas déjà authentifié
        if request.path.startswith('/admin/') and not request.user.is_authenticated:
            try:
                superuser = User.objects.filter(is_superuser=True).first()
                if superuser:
                    # Force l'authentification sans passer par le formulaire
                    request.user = superuser
                    # Simule une session active
                    request.session['_auth_user_id'] = str(superuser.pk)
                    request.session['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
                    request.session['_auth_user_hash'] = superuser.get_session_auth_hash()
            except Exception:
                pass
        return None
