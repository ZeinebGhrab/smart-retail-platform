# `config/` — Configuration globale du projet Django

Module de configuration standard Django (créé par `django-admin startproject`), qui centralise les paramètres lus par les deux applications du projet (`accounts/` et `history/`).

## Fichiers

| Fichier | Rôle |
|---|---|
| `settings.py` | Paramètres globaux : base de données, apps installées, CORS, JWT, e-mail SMTP, REST Framework, Swagger. Toutes les valeurs sensibles ou variables d'un environnement à l'autre sont lues via `os.environ.get(...)`, jamais codées en dur |
| `urls.py` | Routage racine — monte `accounts.urls` et `history.urls` sous `/api/`, l'admin Django sous `/admin/`, et la documentation Swagger/ReDoc sous `/api/docs/` et `/api/redoc/` |
| `wsgi.py` | Point d'entrée WSGI (serveurs synchrones — utilisé par défaut) |
| `asgi.py` | Point d'entrée ASGI (serveurs asynchrones — disponible si besoin, non utilisé par le `Dockerfile` actuel) |

## Paramètres clés de `settings.py`

| Paramètre | Source | Notes |
|---|---|---|
| `SECRET_KEY` | `DJANGO_SECRET_KEY` (env) ou valeur de repli `dev-secret-key-change-me` | ⚠️ à définir explicitement en production |
| `DEBUG` | `DJANGO_DEBUG` (env), `true` par défaut | À mettre à `false` en production |
| `ALLOWED_HOSTS` | `DJANGO_ALLOWED_HOSTS` (env), `*` par défaut | |
| `AUTH_USER_MODEL` | `accounts.User` | Authentification par e-mail, voir `accounts/README.md` |
| `DATABASES` | SQLite par défaut ; bascule vers PostgreSQL si `DB_ENGINE=postgresql` (+ `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`) | Le CSV visiteurs ne passe **pas** par cette base — uniquement les comptes utilisateurs et l'admin |
| `CORS_ALLOW_ALL_ORIGINS` | `True` | Sans risque ici : l'authentification se fait par JWT (header `Authorization`), pas par cookies/sessions |
| `SIMPLE_JWT` | — | Access token 60 min, refresh token 14 jours, rotation + blacklist activées |
| `EMAIL_*` | `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` (env) | **Secrets** — voir note ci-dessous |
| `VISITOR_DATA_CSV` | `VISITOR_DATA_CSV` (env) ou chemin par défaut | Chemin vers le CSV lu par `history/visitor_data.py` |
| `SPECTACULAR_SETTINGS` | — | Génération du schéma OpenAPI / Swagger (`drf-spectacular`) |

> 🔒 **Confidentialité** — `EMAIL_HOST_USER` et `EMAIL_HOST_PASSWORD` ne sont jamais écrits en dur dans ce dossier ni dans `docker-compose.yml`. Ils sont injectés au runtime depuis le fichier `.env` à la racine du repo (non versionné, voir `.gitignore`). Voir le `README.md` racine, section 9, pour la procédure complète.

## Postgres (optionnel)

Par défaut, le projet utilise SQLite (suffisant pour les comptes utilisateurs et l'admin). Pour basculer vers PostgreSQL, définir dans `.env` :

```
DB_ENGINE=postgresql
DB_NAME=...
DB_USER=...
DB_PASSWORD=...
DB_HOST=...
DB_PORT=5432
```

puis ajouter ces variables au service `django_api` dans `docker-compose.yml` (non fait par défaut — la base SQLite suffit pour ce projet).
