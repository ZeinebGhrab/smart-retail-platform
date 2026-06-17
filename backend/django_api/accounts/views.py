# ============================================================
# accounts/views.py — API REST : authentification
#
# POST /api/auth/register/  → création de compte (Register.tsx)
# POST /api/auth/login/     → connexion (Login.tsx)
# POST /api/auth/refresh/   → renouvellement de l'access token (TokenRefreshView, voir urls.py)
# GET  /api/auth/me/        → profil de l'utilisateur connecté
# POST /api/auth/logout/    → invalidation du refresh token (blacklist)
#
# Auth par JWT (djangorestframework-simplejwt) : un access token
# (courte durée) + un refresh token (longue durée, "remember me").
# ============================================================

from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import LoginSerializer, RegisterSerializer, UserSerializer


def _tokens_for_user(user) -> dict:
    """Génère la paire access/refresh JWT pour un utilisateur donné."""
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


@extend_schema(
    tags=["Authentification"],
    summary="Inscription (créer un compte)",
    description=(
        "Crée un nouvel utilisateur ShopAnalytics. Champs alignés sur le "
        "formulaire Register.tsx : prénom, nom, nom du commerce, e-mail, "
        "mot de passe + confirmation.\n\n"
        "Retourne le profil créé ainsi qu'une paire de tokens JWT "
        "(access/refresh), au même format que /api/auth/login/."
    ),
    request=RegisterSerializer,
    examples=[
        OpenApiExample(
            "Inscription",
            value={
                "first_name": "Ali",
                "last_name": "Ben Salem",
                "store_name": "Boutique El Amal",
                "email": "ali@example.com",
                "password": "motdepasse123",
                "confirm": "motdepasse123",
            },
            request_only=True,
        ),
    ],
)
@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    user = serializer.save()
    return Response(
        {"user": UserSerializer(user).data, **_tokens_for_user(user)},
        status=201,
    )


@extend_schema(
    tags=["Authentification"],
    summary="Connexion",
    description=(
        "Authentifie un utilisateur par e-mail + mot de passe (Login.tsx) "
        "et retourne son profil ainsi qu'une paire de tokens JWT."
    ),
    request=LoginSerializer,
    examples=[
        OpenApiExample(
            "Connexion",
            value={"email": "ali@example.com", "password": "motdepasse123"},
            request_only=True,
        ),
    ],
)
@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data, context={"request": request})
    if not serializer.is_valid():
        # Message unique, générique — cohérent avec l'alerte globale affichée
        # par Login.tsx (pas de détail champ par champ pour rester sobre/sûr).
        return Response({"detail": "Identifiants incorrects. Vérifiez votre e-mail et mot de passe."}, status=400)

    user = serializer.validated_data["user"]
    return Response({"user": UserSerializer(user).data, **_tokens_for_user(user)})


@extend_schema(tags=["Authentification"], summary="Profil de l'utilisateur connecté")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)


@extend_schema(
    tags=["Authentification"],
    summary="Déconnexion (invalide le refresh token)",
    description="Met le refresh token fourni en liste noire ; l'access token reste valide jusqu'à son expiration naturelle (courte durée).",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    refresh = request.data.get("refresh")
    if not refresh:
        return Response({"error": "Champ 'refresh' manquant."}, status=400)
    try:
        RefreshToken(refresh).blacklist()
    except TokenError:
        return Response({"error": "Token invalide ou déjà expiré."}, status=400)
    return Response({"detail": "Déconnexion réussie."})