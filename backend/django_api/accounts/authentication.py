# ============================================================
# accounts/authentication.py
# Isolé de views.py pour éviter l'import circulaire avec DRF.
# DRF charge DEFAULT_AUTHENTICATION_CLASSES très tôt au démarrage,
# avant que rest_framework.views soit complètement initialisé.
# Ce fichier n'importe que rest_framework_simplejwt, ce qui est safe.
# ============================================================

from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """
    Lit le JWT d'abord dans le header Authorization (Bearer …),
    puis dans le cookie HttpOnly si le header est absent.
    Compatible Swagger/Postman (header) + app web (cookie).
    """

    def authenticate(self, request):
        # 1. Essai standard (header Authorization: Bearer …)
        result = super().authenticate(request)
        if result is not None:
            return result

        # 2. Fallback : cookie HttpOnly
        raw_token = request.COOKIES.get(settings.JWT_AUTH_COOKIE)
        if raw_token is None:
            return None

        validated = self.get_validated_token(raw_token.encode())
        return self.get_user(validated), validated