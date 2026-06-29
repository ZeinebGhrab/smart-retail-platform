# ============================================================
# accounts/openapi.py
# Enregistre CookieJWTAuthentication auprès de drf-spectacular
# pour supprimer les warnings "could not resolve authenticator".
# Importé automatiquement via SPECTACULAR_SETTINGS ou AppConfig.
# ============================================================

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CookieJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "accounts.authentication.CookieJWTAuthentication"
    name = "cookieJWT"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "JWT transmis via cookie HttpOnly `anavid_access`. "
                "Pour Swagger, utilisez le header Authorization: Bearer <token>."
            ),
        }