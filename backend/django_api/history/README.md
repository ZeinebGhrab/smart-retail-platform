# `history/` — App métier principale

L'app `history` regroupe toutes les fonctionnalités data/métier de la plateforme Anavid Store 360 :  
analytics visiteurs, prédictions IA et chat en langage naturel.

---

## Sous-applications

| Dossier | Rôle | README |
|---|---|---|
| `chatbot/` | Chat IA en langage naturel (RAG + Llama 3.2 via Ollama) | [→ README](chatbot/README.md) |
| `visitors/` | Données d'affluence issues du CSV (historique, flux horaire, prévisions) | [→ README](visitors/README.md) |
| `n8n_predictions/` | Rapports N8N, SSE temps réel, notifications push FCM | [→ README](n8n_predictions/README.md) |

---

## Fichiers racine

| Fichier | Rôle |
|---|---|
| `urls.py` | Routeur principal — assemble tous les sous-namespaces et alias frontend |
| `utils.py` | Helper `get_pagination_params()` — partagé par toutes les sous-apps |

---

## Routage

Toutes les URLs sont montées sous `/api/` via `config/urls.py` :

```
/api/
├── chat/                          → chatbot/ (RAG)
├── history/                       → visitors/ (analytics)
├── notifications/                 → alias frontend n8n_predictions/
├── predictions/                   → n8n_predictions/ (prédictions)
└── prediction/stream/             → alias frontend SSE
```

---

## Pagination centralisée

Toutes les vues de liste utilisent `get_pagination_params()` depuis `utils.py` :

```python
from ..utils import get_pagination_params

limit, offset = get_pagination_params(request.query_params)
total = queryset.count()
page  = queryset[offset:offset + limit]
```

| Paramètre | Défaut | Max | Comportement si invalide |
|---|---|---|---|
| `limit` | `50` | `200` | Remplacé par défaut |
| `offset` | `0` | — | Remplacé par `0` |

---

## Authentification

Les endpoints `history/` sont **publics** (`AllowAny` par défaut dans `settings.py`).  
Aucun token JWT n'est requis pour accéder aux données visiteurs, alertes ou notifications.