# `django_api/` — API REST Django (production)

Ce dossier contient le **serveur API HTTP de ShopAnalytics**, exposé aux clients (frontend Ionic, intégrations tierces). Basé sur **Django 5 + Django REST Framework**, il fournit les endpoints analytiques visiteurs ainsi qu'un endpoint de chat RAG alimenté par Ollama.

Contrairement à l'agent standalone `app/`, ce conteneur est **léger** : il délègue les embeddings directement à Ollama via HTTP (pas de `torch`, pas de `chromadb`, pas de `sentence-transformers`).

---

## Structure

```
django_api/
├── config/                  # Configuration Django globale
│   ├── settings.py          # Paramètres (DB, apps, CORS, env vars)
│   ├── urls.py              # Routage racine + Swagger
│   ├── wsgi.py / asgi.py    # Points d'entrée WSGI/ASGI
│   └── __init__.py
├── history/                 # Application Django principale
│   ├── views.py             # Endpoints REST analytics visiteurs
│   ├── chat_view.py         # Endpoint POST /api/chat/
│   ├── rag_pipeline.py      # Pipeline RAG (Ollama HTTP)
│   ├── visitor_data.py      # Couche données CSV (identique à app/)
│   ├── urls.py              # Routage de l'app history
│   └── apps.py
├── manage.py                # CLI Django
├── requirements.txt         # Dépendances (sans torch/chromadb)
├── Dockerfile               # Image légère python:3.11-slim
└── db.sqlite3               # Base SQLite (sessions admin, dev)
```

---

## Endpoints exposés

Base URL : `http://localhost:8000/api/`

| Méthode | URL | Description |
|---|---|---|
| `GET` | `/api/history/visitors/` | Historique journalier avec ventilation genre/âge |
| `GET` | `/api/history/visitors/count/` | Comptage pour une date donnée |
| `GET` | `/api/history/visitors/hourly/` | Flux horaire + heure de pointe |
| `GET` | `/api/history/visitors/forecast/` | Prévision J+1 (régression linéaire) |
| `GET` | `/api/history/summary/` | KPIs globaux (période, total, répartition) |
| `GET` | `/api/history/cameras/` | Liste des caméras disponibles |
| `POST` | `/api/chat/` | Chat RAG en langage naturel (Ollama) |
| `GET` | `/api/docs/` | Swagger UI (drf-spectacular) |
| `GET` | `/api/redoc/` | ReDoc |

**Paramètres communs (query string) :**
- `date` — format `YYYY-MM-DD` (défaut : dernière date disponible)
- `start_date` / `end_date` — plage de dates
- `camera` — `Porte_nord` ou `Porte_sud` (défaut : toutes)

---

## Application `history/`

### `views.py`
Vues DRF décorées avec `@extend_schema` (OpenAPI). Chaque vue délègue le calcul à `visitor_data.py` et retourne un `Response` DRF. Les vues sont documentées automatiquement dans Swagger.

### `visitor_data.py`
Copie fonctionnelle de `app/visitor_data.py`, adaptée au contexte Docker (chemin CSV via variable d'environnement `VISITOR_DATA_CSV`). Inclut un **cache en mémoire** avec invalidation par `mtime` : le CSV est rechargé uniquement si le fichier a changé sur disque.

### `rag_pipeline.py`
Pipeline RAG sans dépendances lourdes :

1. `_build_csv_context()` — extrait les métriques clés du CSV (KPIs du jour, flux horaire, top caméra) pour les injecter dans le prompt
2. `_retrieve_kb()` — calcule la similarité cosinus entre la question et les 8 documents de `dataset/knowledge_base.json` via `Ollama /api/embeddings` (pas de ChromaDB)
3. `_build_prompt()` — assemble le contexte CSV + les documents KB pertinents + la question utilisateur
4. `_call_ollama()` — envoie le prompt à `Ollama /api/generate` et retourne la réponse en streaming ou bloc

**Architecture réseau dans Docker :**
```
[frontend] → [django_api:8000] → [ollama:11434]
                  ↑
          lit /app/data/*.csv  (volume partagé)
```

### `chat_view.py`
Vue `POST /api/chat/` qui orchestre `rag_pipeline.py`. Accepte `{ "message": "...", "history": [...] }` et retourne `{ "response": "..." }`.

---

## Configuration (`config/`)

### `settings.py`
| Paramètre | Valeur / Source |
|---|---|
| `ALLOWED_HOSTS` | `DJANGO_ALLOWED_HOSTS` (env) ou `*` |
| `CORS_ALLOW_ALL_ORIGINS` | `True` (dev rapide, sans auth) |
| `DATABASES` | SQLite (`db.sqlite3`) — sessions admin uniquement |
| `INSTALLED_APPS` | `history`, `rest_framework`, `corsheaders`, `drf_spectacular` |

### `urls.py`
Routage racine : monte `history.urls` sous `/api/`, et les vues Swagger/ReDoc sous `/api/docs/` et `/api/redoc/`.

---

## Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://ollama:11434` | URL du service Ollama |
| `OLLAMA_MODEL` | `llama3.2:3b-instruct-q4_K_M` | Modèle LLM utilisé |
| `VISITOR_DATA_CSV` | `/app/data/shoppingclub_2025_2026.csv` | Chemin vers le CSV visiteurs |
| `DJANGO_ALLOWED_HOSTS` | `*` | Hosts autorisés |

---

## Dépendances notables

```
Django>=5.0          # framework web
djangorestframework  # API REST
django-cors-headers  # CORS (frontend cross-origin)
drf-spectacular      # génération OpenAPI / Swagger
pandas, numpy        # traitement données CSV
requests             # appels HTTP vers Ollama
# ⚠️ PAS de torch / chromadb / sentence-transformers
```

> L'absence de `torch` réduit l'image Docker de ~800 Mo à ~200 Mo et élimine les dépendances CUDA.