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

from .models import User, PasswordResetToken
from .serializers import (
    LoginSerializer, RegisterSerializer, UserSerializer,
    PasswordResetRequestSerializer, PasswordResetVerifySerializer, PasswordResetConfirmSerializer,
)


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

# ── Mot de passe oublié — 3 étapes ──────────────────────────────────────────
#
# Étape 1 : POST /api/auth/password-reset/request/
#   → reçoit { email }, génère un OTP, le retourne dans la réponse.
#   NOTE : en production, remplacer le retour du code par un envoi SMTP
#          (django.core.mail.send_mail). On le retourne ici pour éviter
#          toute dépendance à un serveur mail en dev/demo.
#
# Étape 2 : POST /api/auth/password-reset/verify/
#   → reçoit { email, code }, vérifie que le token est valide (sans le consommer).
#
# Étape 3 : POST /api/auth/password-reset/confirm/
#   → reçoit { email, code, password, confirm }, change le mot de passe.
# ────────────────────────────────────────────────────────────────────────────

@extend_schema(
    tags=["Authentification"],
    summary="Demande de réinitialisation — envoie un OTP par e-mail",
    description=(
        "Reçoit une adresse e-mail. Si elle correspond à un compte existant, "
        "génère un code OTP à 6 chiffres valable 15 minutes et l'envoie par e-mail "
        "via Gmail SMTP."
    ),
)
@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_request(request):
    import logging
    from django.core.mail import send_mail
    from django.conf import settings as django_settings

    serializer = PasswordResetRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    email = serializer.validated_data["email"].strip().lower()

    # Réponse identique qu'un compte existe ou non (sécurité — pas d'énumération)
    generic_response = {"detail": "Si cette adresse correspond à un compte, un code vous a été envoyé par e-mail."}

    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return Response(generic_response)

    # Invalider les anciens tokens non utilisés pour cet utilisateur
    PasswordResetToken.objects.filter(user=user, used=False).update(used=True)

    token = PasswordResetToken.objects.create(user=user)

    prenom = user.first_name or user.email
    code   = token.code

    html_message = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Réinitialisation de mot de passe</title>
</head>
<body style="margin:0;padding:0;background:#f3f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f5f9;padding:40px 16px;">
    <tr>
      <td align="center">
        <table width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;">

          <!-- HEADER LOGO -->
          <tr>
            <td align="center" style="padding-bottom:28px;">
              <table cellpadding="0" cellspacing="0">
                <tr>
                  <td style="background:#2563eb;border-radius:16px;padding:14px 20px;display:inline-block;">
                    <span style="font-size:22px;font-weight:700;color:#ffffff;letter-spacing:-0.5px;">Anavid</span>
                    <span style="font-size:12px;color:rgba(255,255,255,0.75);margin-left:6px;">Store 360</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- CARD -->
          <tr>
            <td style="background:#ffffff;border-radius:16px;border:1px solid #e2e6f0;padding:40px 36px;box-shadow:0 2px 12px rgba(17,24,39,0.06);">

              <!-- Icône cadenas -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding-bottom:24px;">
                    <div style="width:60px;height:60px;background:rgba(37,99,235,0.10);border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:28px;line-height:60px;text-align:center;">
                      🔐
                    </div>
                  </td>
                </tr>

                <!-- Titre -->
                <tr>
                  <td align="center" style="padding-bottom:8px;">
                    <h1 style="margin:0;font-size:22px;font-weight:700;color:#111827;letter-spacing:-0.3px;">
                      Réinitialisation de mot de passe
                    </h1>
                  </td>
                </tr>

                <!-- Sous-titre -->
                <tr>
                  <td align="center" style="padding-bottom:32px;">
                    <p style="margin:0;font-size:14px;color:#6b7280;line-height:1.6;">
                      Bonjour <strong style="color:#111827;">{prenom}</strong>,<br/>
                      Voici votre code de vérification à usage unique.
                    </p>
                  </td>
                </tr>

                <!-- Code OTP -->
                <tr>
                  <td align="center" style="padding-bottom:32px;">
                    <div style="display:inline-block;background:#f3f5f9;border:2px dashed #2563eb;border-radius:14px;padding:20px 40px;">
                      <span style="font-size:38px;font-weight:800;letter-spacing:0.18em;color:#2563eb;font-family:'Courier New',monospace;">
                        {code}
                      </span>
                    </div>
                  </td>
                </tr>

                <!-- Infos -->
                <tr>
                  <td>
                    <table width="100%" cellpadding="0" cellspacing="0" style="background:#fef9c3;border:1px solid #fde047;border-radius:10px;padding:14px 16px;margin-bottom:24px;">
                      <tr>
                        <td style="font-size:13px;color:#713f12;line-height:1.6;">
                          ⏱ &nbsp;Ce code est valable <strong>15 minutes</strong>.<br/>
                          🔒 &nbsp;N'entrez ce code que sur la page de réinitialisation Anavid.<br/>
                          ❌ &nbsp;Si vous n'avez pas fait cette demande, ignorez cet e-mail.
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>

                <!-- Divider -->
                <tr>
                  <td style="border-top:1px solid #e2e6f0;padding-top:20px;">
                    <p style="margin:0;font-size:12px;color:#9ca3af;text-align:center;line-height:1.6;">
                      Cet e-mail a été envoyé automatiquement par Anavid Store 360.<br/>
                      Merci de ne pas y répondre directement.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td align="center" style="padding-top:20px;">
              <p style="margin:0;font-size:11px;color:#9ca3af;">
                © 2026 Anavid Store 360 &nbsp;·&nbsp; Tous droits réservés
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    # Texte brut fallback
    plain_message = (
        f"Bonjour {prenom},\n\n"
        f"Votre code de réinitialisation de mot de passe est :\n\n"
        f"    {code}\n\n"
        f"Ce code est valable 15 minutes.\n"
        f"Si vous n'avez pas effectué cette demande, ignorez cet e-mail.\n\n"
        f"— L'équipe Anavid Store 360"
    )

    try:
        from django.core.mail import EmailMultiAlternatives
        msg = EmailMultiAlternatives(
            subject="🔐 Votre code de réinitialisation — Anavid Store 360",
            body=plain_message,
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send(fail_silently=False)
    except Exception as exc:
        logging.getLogger(__name__).error("Erreur envoi mail reset: %s", exc)
        return Response(
            {"detail": "Impossible d'envoyer l'e-mail. Vérifiez la configuration SMTP."},
            status=500,
        )

    return Response(generic_response)


@extend_schema(
    tags=["Authentification"],
    summary="Vérification du code OTP (sans consommer le token)",
)
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
        return Response({"detail": "Ce code a expiré. Veuillez en demander un nouveau."}, status=400)

    return Response({"detail": "Code valide."})


@extend_schema(
    tags=["Authentification"],
    summary="Confirmation — change le mot de passe",
)
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
        return Response({"detail": "Ce code a expiré. Veuillez en demander un nouveau."}, status=400)

    user.set_password(password)
    user.save()
    token.consume()

    return Response({"detail": "Mot de passe mis à jour avec succès."})