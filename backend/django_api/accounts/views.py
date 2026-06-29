# ============================================================
# accounts/views.py — API REST : authentification
#
# Stratégie cookie HttpOnly :
#   • login / register  → posent access + refresh dans des cookies HttpOnly
#   • refresh           → lit le cookie refresh, renvoie un nouveau cookie access
#   • logout            → blackliste le refresh + supprime les deux cookies
#   • me                → authentifié via CookieJWTAuthentication (authentication.py)
#
# CookieJWTAuthentication est dans accounts/authentication.py (pas ici)
# pour éviter l'import circulaire avec DRF.
# ============================================================

from datetime import timedelta

from django.conf import settings as django_settings
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, PasswordResetToken
from .serializers import (
    LoginSerializer, RegisterSerializer, UserSerializer,
    PasswordResetRequestSerializer, PasswordResetVerifySerializer,
    PasswordResetConfirmSerializer,
)


# ── Helpers ──────────────────────────────────────────────────

def _cookie_settings(lifetime: timedelta, secure: bool = None) -> dict:
    secure = django_settings.JWT_AUTH_COOKIE_SECURE if secure is None else secure
    return {
        "httponly": django_settings.JWT_AUTH_COOKIE_HTTP_ONLY,
        "samesite": django_settings.JWT_AUTH_COOKIE_SAMESITE,
        "secure":   secure,
        "max_age":  int(lifetime.total_seconds()),
        "path":     "/",
    }


def _set_auth_cookies(response: Response, user) -> Response:
    refresh = RefreshToken.for_user(user)
    jwt_cfg = django_settings.SIMPLE_JWT
    response.set_cookie(
        django_settings.JWT_AUTH_COOKIE,
        str(refresh.access_token),
        **_cookie_settings(jwt_cfg["ACCESS_TOKEN_LIFETIME"]),
    )
    response.set_cookie(
        django_settings.JWT_AUTH_REFRESH_COOKIE,
        str(refresh),
        **_cookie_settings(jwt_cfg["REFRESH_TOKEN_LIFETIME"]),
    )
    return response


def _clear_auth_cookies(response: Response) -> Response:
    response.delete_cookie(django_settings.JWT_AUTH_COOKIE, path="/")
    response.delete_cookie(django_settings.JWT_AUTH_REFRESH_COOKIE, path="/")
    return response


# ── Endpoints ────────────────────────────────────────────────

@extend_schema(
    tags=["Authentification"],
    summary="Inscription (créer un compte)",
    request=RegisterSerializer,
    examples=[OpenApiExample("Inscription", value={
        "first_name": "Ali", "last_name": "Ben Salem",
        "store_name": "Boutique El Amal",
        "email": "ali@example.com",
        "password": "motdepasse123", "confirm": "motdepasse123",
    }, request_only=True)],
)
@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)
    user = serializer.save()
    response = Response({"user": UserSerializer(user).data}, status=201)
    return _set_auth_cookies(response, user)


@extend_schema(
    tags=["Authentification"],
    summary="Connexion",
    request=LoginSerializer,
    examples=[OpenApiExample("Connexion", value={
        "email": "ali@example.com", "password": "motdepasse123",
    }, request_only=True)],
)
@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data, context={"request": request})
    if not serializer.is_valid():
        return Response(
            {"detail": "Identifiants incorrects. Vérifiez votre e-mail et mot de passe."},
            status=400,
        )
    user = serializer.validated_data["user"]
    response = Response({"user": UserSerializer(user).data})
    return _set_auth_cookies(response, user)


@extend_schema(
    tags=["Authentification"],
    summary="Renouvellement de l'access token (via cookie refresh)",
)
@api_view(["POST"])
@permission_classes([AllowAny])
def token_refresh(request):
    refresh_token = request.COOKIES.get(django_settings.JWT_AUTH_REFRESH_COOKIE)
    if not refresh_token:
        return Response({"detail": "Cookie refresh absent."}, status=401)

    try:
        refresh = RefreshToken(refresh_token)
        new_access = str(refresh.access_token)
        jwt_cfg = django_settings.SIMPLE_JWT
        response = Response({"detail": "Token renouvelé."})
        response.set_cookie(
            django_settings.JWT_AUTH_COOKIE,
            new_access,
            **_cookie_settings(jwt_cfg["ACCESS_TOKEN_LIFETIME"]),
        )
        if jwt_cfg.get("ROTATE_REFRESH_TOKENS"):
            refresh.set_jti()
            refresh.set_exp()
            new_refresh = str(refresh)
            if jwt_cfg.get("BLACKLIST_AFTER_ROTATION"):
                try:
                    refresh.blacklist()
                except AttributeError:
                    pass
            response.set_cookie(
                django_settings.JWT_AUTH_REFRESH_COOKIE,
                new_refresh,
                **_cookie_settings(jwt_cfg["REFRESH_TOKEN_LIFETIME"]),
            )
        return response
    except TokenError as e:
        return Response({"detail": str(e)}, status=401)


@extend_schema(tags=["Authentification"], summary="Profil de l'utilisateur connecté")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)


@extend_schema(
    tags=["Authentification"],
    summary="Déconnexion — invalide le refresh token et supprime les cookies",
)
@api_view(["POST"])
@permission_classes([AllowAny])
def logout(request):
    refresh_token = request.COOKIES.get(django_settings.JWT_AUTH_REFRESH_COOKIE)
    if refresh_token:
        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            pass
    response = Response({"detail": "Déconnexion réussie."})
    return _clear_auth_cookies(response)


# ── Mot de passe oublié ──────────────────────────────────────

@extend_schema(tags=["Authentification"], summary="Demande de réinitialisation — envoie un OTP par e-mail")
@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_request(request):
    import logging
    from django.core.mail import EmailMultiAlternatives

    serializer = PasswordResetRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    email = serializer.validated_data["email"].strip().lower()

    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return Response({"detail": "Aucun compte n'est associé à cette adresse e-mail."}, status=404)

    PasswordResetToken.objects.filter(user=user, used=False).update(used=True)
    token = PasswordResetToken.objects.create(user=user)
    prenom = user.first_name or user.email
    code = token.code

    plain_message = (
        f"Bonjour {prenom},\n\n"
        f"Votre code de réinitialisation : {code}\n\n"
        f"Valable 15 minutes.\n— Anavid Store 360"
    )

    try:
        msg = EmailMultiAlternatives(
            subject="🔐 Votre code de réinitialisation — Anavid Store 360",
            body=plain_message,
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        msg.send(fail_silently=False)
    except Exception as exc:
        logging.getLogger(__name__).error("Erreur envoi mail reset: %s", exc)
        return Response({"detail": "Impossible d'envoyer l'e-mail. Vérifiez la configuration SMTP."}, status=500)

    return Response({"detail": "Si cette adresse correspond à un compte, un code vous a été envoyé par e-mail."})


@extend_schema(tags=["Authentification"], summary="Vérification du code OTP")
@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_verify(request):
    serializer = PasswordResetVerifySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    email = serializer.validated_data["email"].strip().lower()
    code  = serializer.validated_data["code"]

    try:
        user  = User.objects.get(email__iexact=email)
        token = PasswordResetToken.objects.filter(user=user, code=code, used=False).latest("created_at")
    except (User.DoesNotExist, PasswordResetToken.DoesNotExist):
        return Response({"detail": "Code invalide ou expiré."}, status=400)

    if not token.is_valid():
        return Response({"detail": "Ce code a expiré."}, status=400)

    return Response({"detail": "Code valide."})


@extend_schema(tags=["Authentification"], summary="Confirmation — change le mot de passe")
@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    serializer = PasswordResetConfirmSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    email    = serializer.validated_data["email"].strip().lower()
    code     = serializer.validated_data["code"]
    password = serializer.validated_data["password"]

    try:
        user  = User.objects.get(email__iexact=email)
        token = PasswordResetToken.objects.filter(user=user, code=code, used=False).latest("created_at")
    except (User.DoesNotExist, PasswordResetToken.DoesNotExist):
        return Response({"detail": "Code invalide ou expiré."}, status=400)

    if not token.is_valid():
        return Response({"detail": "Ce code a expiré."}, status=400)

    user.set_password(password)
    user.save()
    token.consume()

    return Response({"detail": "Mot de passe mis à jour avec succès."})