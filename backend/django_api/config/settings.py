"""
Django settings for ShopAnalytics History API.

Données visiteurs lues depuis : backend/data/shoppingclub_2025_2026.csv
(via pandas, voir history/visitor_data.py)

Base de données :
  - Par défaut : SQLite (db.sqlite3) — utilisée seulement pour l'admin/
    le framework Django (pas pour les données visiteurs, qui restent en CSV).
  - Optionnel  : mysql — définir la variable d'environnement
    DB_ENGINE=mysql ainsi que DB_NAME, DB_USER, DB_PASSWORD,
    DB_HOST, DB_PORT pour basculer.
"""
import pymysql
pymysql.install_as_MySQLdb()
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
if os.environ.get("DB_ENGINE", "").lower() == "mysql":
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get("DB_NAME"),
            'USER': os.environ.get("DB_USER"),
            'PASSWORD': os.environ.get("DB_PASSWORD"),
            'HOST': os.environ.get("DB_HOST"),
            'PORT': os.environ.get("DB_PORT"),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
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
# CORS
# withCredentials: true côté frontend exige une liste explicite
# d'origines (CORS_ALLOW_ALL_ORIGINS est incompatible avec les cookies).
# ------------------------------------------------------------
CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:8100,http://localhost",
).split(",")

CORS_ALLOW_CREDENTIALS = True   # indispensable pour que les cookies voyagent

CSRF_TRUSTED_ORIGINS = os.environ.get(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost:5173,http://localhost:8100,http://localhost",
).split(",")

# ------------------------------------------------------------
# Django REST Framework
# ------------------------------------------------------------
REST_FRAMEWORK = {
    # Permission par défaut : ouverte (endpoints history/ non protégés).
    # Les vues qui le nécessitent déclarent explicitement IsAuthenticated.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    # CookieJWTAuthentication lit d'abord le header Authorization (Bearer),
    # puis le cookie HttpOnly "anavid_access" en fallback.
    # Isolé dans accounts/authentication.py pour éviter l'import circulaire
    # qui survenait quand DRF chargeait accounts.views trop tôt.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "accounts.authentication.CookieJWTAuthentication",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# ------------------------------------------------------------
# JWT (djangorestframework-simplejwt)
# ------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":  timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS":  True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ------------------------------------------------------------
# Cookies JWT HttpOnly
# Les tokens ne transitent plus dans le body JSON mais dans des
# cookies HttpOnly posés/lus par accounts/views.py.
#
# En développement (HTTP) :
#   JWT_AUTH_COOKIE_SECURE   = False
#   JWT_AUTH_COOKIE_SAMESITE = "Lax"
#
# En production (HTTPS, domaine unique) :
#   JWT_AUTH_COOKIE_SECURE   = True
#   JWT_AUTH_COOKIE_SAMESITE = "Lax"   (même domaine)  ou
#   JWT_AUTH_COOKIE_SAMESITE = "None"  (cross-site strict)
# ------------------------------------------------------------
JWT_AUTH_COOKIE           = "anavid_access"
JWT_AUTH_REFRESH_COOKIE   = "anavid_refresh"
JWT_AUTH_COOKIE_SECURE    = os.environ.get("JWT_COOKIE_SECURE", "false").lower() == "true"
JWT_AUTH_COOKIE_SAMESITE  = os.environ.get("JWT_COOKIE_SAMESITE", "Lax")
JWT_AUTH_COOKIE_HTTP_ONLY = True

# ------------------------------------------------------------
# Documentation API — Swagger / OpenAPI (drf-spectacular)
# ------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "Anavid Store 360 — API",
    "DESCRIPTION": (
        "API REST de la plateforme **Anavid Smart Retail Platform** (ShoppingClub Sfax).\n\n"
        "## Services disponibles\n\n"
        "| Service | URL | Description |\n"
        "|---|---|---|\n"
        "| **Django API** (ce Swagger) | `http://localhost:8000/api/` | Auth JWT, historique visiteurs, chat IA RAG |\n"
        "| **Ollama LLM** | `http://localhost:11434` | LLM local — génération et embeddings |\n"
        "| **Ollama `/api/generate`** | `http://localhost:11434/api/generate` | Génération de texte (llama3.2:3b-instruct-q4_K_M) |\n"
        "| **Ollama `/api/embeddings`** | `http://localhost:11434/api/embeddings` | Embeddings sémantiques (pipeline RAG) |\n"
        "| **Modèle ML — XGBoost** | `http://localhost:8001` | Prédiction visiteurs par heure/caméra/profil |\n"
        "| **ML `/predict`** | `http://localhost:8001/predict?date=YYYY-MM-DD` | Prédictions pour une date donnée |\n"
        "| **ML `/health`** | `http://localhost:8001/health` | Statut du microservice ML |\n"
        "| **ML Swagger** | `http://localhost:8001/docs` | Documentation interactive du modèle ML |\n\n"
        "## Authentification\n\n"
        "Les endpoints protégés utilisent **JWT via cookie HttpOnly** (`anavid_access`). "
        "Pour Swagger, obtenez un token via `POST /api/auth/login/`, puis cliquez sur **Authorize** "
        "et saisissez : `Bearer <votre_token>`.\n\n"
        "## Communication interne Docker\n\n"
        "Depuis les conteneurs, remplacer `localhost` par les noms de service Docker :\n"
        "`django_api` → `ollama:11434` · `django_api` → `visitor_ml_api:8000`"
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "CONTACT": {
        "name": "Anavid Smart Retail Platform",
    },
    "EXTERNAL_DOCS": {
        "description": "Documentation Modèle ML (XGBoost)",
        "url": "http://localhost:8001/docs",
    },
    "SERVERS": [
        {
            "url": "http://localhost:8000",
            "description": "Django API — développement local",
        },
        {
            "url": "http://localhost:8001",
            "description": "Visitor ML API — XGBoost (microservice)",
        },
        {
            "url": "http://localhost:11434",
            "description": "Ollama LLM — génération & embeddings",
        },
    ],
}

# ------------------------------------------------------------
# Données visiteurs (CSV)
# ------------------------------------------------------------
VISITOR_DATA_CSV = os.environ.get(
    "VISITOR_DATA_CSV",
    str(BACKEND_DIR / "data" / "shoppingclub_2025_2026.csv"),
)

# ------------------------------------------------------------
# Email — Gmail SMTP
# ------------------------------------------------------------
EMAIL_BACKEND       = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST          = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT          = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_USE_TLS       = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_HOST_USER     = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL  = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)