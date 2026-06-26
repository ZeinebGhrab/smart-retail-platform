# `history/` — App métier principale

L'app `history` regroupe toutes les fonctionnalités data/métier de la plateforme Anavid Store 360 :  
analytics visiteurs, alertes vidéo, prédictions IA et chat en langage naturel.

---

## Sous-applications

| Dossier | Rôle | README |
|---|---|---|
| `visitors/` | Données d'affluence issues du CSV (historique, flux horaire, prévisions) | [→ README](visitors/README.md) |
| `video_alerts/` | Alertes vidéo de détection de vol, qualification manuelle | [→ README](video_alerts/README.md) |
| `n8n_predictions/` | Rapports N8N, SSE temps réel, notifications push FCM | [→ README](n8n_predictions/README.md) |

---

## Fichiers racine

| Fichier | Rôle |
|---|---|
| `urls.py` | Routeur principal — assemble tous les sous-namespaces et alias frontend |
| `chat_view.py` | Endpoint `POST /api/chat/` — question en langage naturel |
| `rag_pipeline.py` | Pipeline RAG : ChromaDB + Ollama (Llama 3.2 3B) |
| `utils.py` | Helper `get_pagination_params()` — partagé par toutes les sous-apps |

---

## Routage

Toutes les URLs sont montées sous `/api/` via `config/urls.py` :

```
/api/
├── chat/                          → chat_view.chat
├── history/                       → visitors/ (analytics)
├── video-alerts/                  → video_alerts/ (alertes)
├── videos/                        → alias frontend video_alerts/
├── notifications/                 → alias frontend n8n_predictions/
├── predictions/                   → n8n_predictions/ (prédictions)
└── prediction/stream/             → alias frontend SSE
```

---

## Chat IA — `POST /api/chat/`

Endpoint RAG qui répond à des questions en français sur les données du magasin.

**Corps de la requête :**
```json
{
  "question": "Nombre de visiteurs le 2026-05-30 ?",
  "history": [
    { "role": "user", "content": "Et la semaine dernière ?" },
    { "role": "assistant", "content": "La semaine dernière il y a eu 1 240 visiteurs." }
  ]
}
```

**Réponse :**
```json
{
  "answer": "Le 2026-05-30, 218 visiteurs ont été enregistrés (Porte_nord : 120, Porte_sud : 98).",
  "model": "llama3.2:3b-instruct-q4_K_M",
  "sources": { ... }
}
```

Le champ `history` est optionnel et permet de gérer les questions de suivi  
(ex: "Et hier ?" après une première question sur une date).

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