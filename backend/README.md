# Backend — Anavid Store 360

API REST Django pour la plateforme d'analytics retail **Anavid Store 360**.  
Elle centralise l'authentification, les données visiteurs, les alertes vidéo et les prédictions IA reçues de N8N.

---

## Stack technique

| Composant | Technologie |
|---|---|
| Framework | Django 4.x + Django REST Framework |
| Auth | JWT via `djangorestframework-simplejwt` |
| Base de données | MySQL (prod) · SQLite (dev local) |
| Documentation API | Swagger UI (`drf-spectacular`) |
| Streaming temps réel | Server-Sent Events (SSE) |
| Notifications push | Firebase Cloud Messaging (FCM) |
| Chat IA | RAG + Llama 3.2 3B via Ollama + ChromaDB |

---

## Structure du projet

```
backend/django_api/
├── config/                  # Paramètres Django (settings, urls racine, wsgi)
├── accounts/                # Authentification JWT (register, login, logout, reset mdp)
└── history/                 # Données métier — voir ci-dessous
    ├── utils.py             # Helper pagination partagé
    ├── urls.py              # Routeur principal de l'app history
    ├── chat_view.py         # Endpoint Chat IA (RAG)
    ├── rag_pipeline.py      # Pipeline RAG (ChromaDB + Ollama)
    ├── visitors/            # Analytics visiteurs (CSV)
    ├── video_alerts/        # Alertes vidéo détection vol
    └── n8n_predictions/     # Prédictions et notifications N8N
```

---

## Installation rapide

```bash
cd backend/django_api
pip install -r requirements.txt

# Copier et renseigner les variables d'environnement
cp .env.example .env

python manage.py migrate
python manage.py runserver
```

### Variables d'environnement clés

| Variable | Description |
|---|---|
| `DJANGO_DEBUG` | `true` (dev) / `false` (prod) |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Connexion MySQL (prod) |
| `DJANGO_SECRET_KEY` | Clé secrète Django |
| `DEFAULT_FROM_EMAIL` | Adresse expéditrice pour les e-mails |

> En développement sans MySQL, Django bascule automatiquement sur SQLite.

---

## Documentation API

| URL | Description |
|---|---|
| `GET /api/docs/` | Swagger UI interactif |
| `GET /api/redoc/` | ReDoc |
| `GET /api/schema/` | Schéma OpenAPI 3 (JSON) |

---

## Apps et endpoints principaux

### `accounts/` — Authentification

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register/` | Création de compte |
| `POST` | `/api/auth/login/` | Connexion — retourne access + refresh JWT |
| `POST` | `/api/auth/refresh/` | Renouvellement de l'access token |
| `GET` | `/api/auth/me/` | Profil utilisateur connecté |
| `POST` | `/api/auth/logout/` | Invalidation du refresh token |
| `POST` | `/api/auth/password-reset/request/` | Envoi OTP par e-mail |
| `POST` | `/api/auth/password-reset/verify/` | Vérification du code OTP |
| `POST` | `/api/auth/password-reset/confirm/` | Changement de mot de passe |

Toutes les requêtes protégées nécessitent le header :
```
Authorization: Bearer <access_token>
```

---

### `history/` — Données métier

Voir les READMEs dédiés dans chaque sous-dossier :

| Sous-app | Rôle | README |
|---|---|---|
| `visitors/` | Analytics visiteurs (flux horaire, prévisions, historique) | [→ README](history/visitors/README.md) |
| `video_alerts/` | Alertes vidéo détection de vol, qualification manuelle | [→ README](history/video_alerts/README.md) |
| `n8n_predictions/` | Prédictions N8N, SSE temps réel, FCM push, chat IA | [→ README](history/n8n_predictions/README.md) |

---

## Pagination

Tous les endpoints retournant des listes supportent la pagination via `limit` / `offset` :

```
GET /api/videos/all/?limit=20&offset=0
```

**Réponse standard :**
```json
{
  "count": 150,
  "limit": 20,
  "offset": 0,
  "results": [...]
}
```

| Paramètre | Défaut | Max |
|---|---|---|
| `limit` | `50` | `200` |
| `offset` | `0` | — |

La validation est centralisée dans `history/utils.py` (`get_pagination_params`).  
Les valeurs invalides (ex: `limit=abc`) sont remplacées par les valeurs par défaut sans erreur.

---

## Authentification JWT

- **Access token** : durée de vie 60 minutes
- **Refresh token** : durée de vie 14 jours, rotation automatique, blacklist à l'usage
- Les endpoints `history/` sont publics par défaut (`AllowAny`)
- Les endpoints `accounts/` sensibles déclarent explicitement `IsAuthenticated`