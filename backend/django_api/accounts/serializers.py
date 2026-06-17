# ============================================================
# accounts/serializers.py — Sérialiseurs auth (register / login / user)
#
# Champs strictement alignés sur les formulaires du frontend :
#   - Register.tsx → firstName, lastName, storeName, email, password, confirm
#   - Login.tsx    → email, password
# ============================================================

from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Représentation publique de l'utilisateur (jamais le mot de passe)."""

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "store_name", "date_joined"]
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    """
    Inscription — reproduit exactement les champs du formulaire Register.tsx.
    `confirm` n'existe pas sur le modèle : il sert uniquement à la
    validation croisée avec `password` (même règle que côté frontend).
    """

    confirm = serializers.CharField(write_only=True, trim_whitespace=False)
    email = serializers.EmailField(validators=[])  # unicité gérée manuellement (message FR personnalisé)
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        min_length=6,
        error_messages={"min_length": "Minimum 6 caractères"},
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "store_name", "email", "password", "confirm"]
        extra_kwargs = {
            "first_name": {"required": True, "allow_blank": False, "error_messages": {"blank": "Prénom requis"}},
            "last_name":  {"required": True, "allow_blank": False, "error_messages": {"blank": "Nom requis"}},
            "store_name": {"required": True, "allow_blank": False,
                            "error_messages": {"blank": "Nom du commerce requis"}},
        }

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Un compte existe déjà avec cette adresse e-mail.")
        return value

    def validate(self, attrs):
        if attrs.get("password") != attrs.pop("confirm", None):
            raise serializers.ValidationError({"confirm": "Les mots de passe ne correspondent pas."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    """Connexion — champs alignés sur Login.tsx (email, password)."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    default_error_messages = {
        "invalid_credentials": "Identifiants incorrects. Vérifiez votre e-mail et mot de passe.",
        "inactive": "Ce compte a été désactivé.",
    }

    def validate(self, attrs):
        email = attrs["email"].strip().lower()
        password = attrs["password"]
        user = authenticate(
            self.context.get("request"), email=email, password=password
        )
        if user is None:
            self.fail("invalid_credentials")
        if not user.is_active:
            self.fail("inactive")
        attrs["user"] = user
        return attrs

# ── Mot de passe oublié ──────────────────────────────────────

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code  = serializers.CharField(min_length=6, max_length=6)


class PasswordResetConfirmSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    code     = serializers.CharField(min_length=6, max_length=6)
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        min_length=6,
        error_messages={"min_length": "Minimum 6 caractères"},
    )
    confirm  = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm"]:
            raise serializers.ValidationError({"confirm": "Les mots de passe ne correspondent pas."})
        return attrs