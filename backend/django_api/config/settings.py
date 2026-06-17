"""
Django settings for ShopAnalytics History API.

Données visiteurs lues depuis : backend/data/shoppingclub_2025_2026.csv
(via pandas, voir history/visitor_data.py)

Base de données :
  - Par défaut : SQLite (db.sqlite3) — utilisée seulement pour l'admin/
    le framework Django (pas pour les données visiteurs, qui restent en CSV).
  - Optionnel  : PostgreSQL — définir la variable d'environnement
    DB_ENGINE=postgresql ainsi que DB_NAME, DB_USER, DB_PASSWORD,
    DB_HOST, DB_PORT pour basculer.
"""

from datetime import timedelta
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
# Racine du projet "backend" (contient data/shoppingclub_2025_2026.csv)
BACKEND_DIR = BASE_DIR.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-key-change-me")

DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "corsheaders",
    "accounts",
    "history",
]

# ------------------------------------------------------------
# Authentification — modèle utilisateur personnalisé (e-mail)
# ------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ------------------------------------------------------------
# Base de données
# ------------------------------------------------------------
if os.environ.get("DB_ENGINE", "").lower() == "postgresql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "shopanalytics"),
            "USER": os.environ.get("DB_USER", "postgres"),
            "PASSWORD": os.environ.get("DB_PASSWORD", "postgres"),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Tunis"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ------------------------------------------------------------
# CORS — toutes origines autorisées (dev). L'authentification se fait
# via JWT (header Authorization), pas via cookies/sessions — CORS
# ouvert n'expose donc pas de session à voler.
# ------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = True

# ------------------------------------------------------------
# Django REST Framework
# ------------------------------------------------------------
REST_FRAMEWORK = {
    # Permission par défaut : ouverte (endpoints history/ non protégés).
    # Les vues accounts/ qui le nécessitent (ex: /api/auth/me/) déclarent
    # explicitement IsAuthenticated via @permission_classes.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# ------------------------------------------------------------
# JWT (djangorestframework-simplejwt) — voir accounts/views.py
# ------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ------------------------------------------------------------
# Documentation API — Swagger / OpenAPI (drf-spectacular)
# Accessible sur /api/docs/ (Swagger UI) et /api/schema/ (OpenAPI JSON)
# ------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "ShopAnalytics — API Historique Visiteurs",
    "DESCRIPTION": (
        "API REST exposant l'historique des visiteurs / données analytics "
        "issues du fichier shoppingclub_2025_2026.csv (Anavid Smart Retail Platform)."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ------------------------------------------------------------
# Données visiteurs (CSV)
# ------------------------------------------------------------
VISITOR_DATA_CSV = os.environ.get(
    "VISITOR_DATA_CSV",
    str(BACKEND_DIR / "data" / "shoppingclub_2025_2026.csv"),
)
# ------------------------------------------------------------
# Email — Gmail SMTP (variables lues depuis .env via docker-compose)
# ------------------------------------------------------------
EMAIL_BACKEND       = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST          = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT          = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_USE_TLS       = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_HOST_USER     = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL  = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)