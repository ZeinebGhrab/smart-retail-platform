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
    "corsheaders",
    "history",
]

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
# CORS — APIs ouvertes (pas d'authentification, dev rapide)
# ------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = True

# ------------------------------------------------------------
# Django REST Framework
# ------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

# ------------------------------------------------------------
# Données visiteurs (CSV)
# ------------------------------------------------------------
VISITOR_DATA_CSV = os.environ.get(
    "VISITOR_DATA_CSV",
    str(BACKEND_DIR / "data" / "shoppingclub_2025_2026.csv"),
)
