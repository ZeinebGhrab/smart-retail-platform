# `history/` — Application Django : analytics, RAG et notifications

Application Django principale : expose les endpoints analytiques sur les données visiteurs, le chat RAG alimenté par Ollama, et le canal de notifications alimenté par le workflow N8N (prévisions quotidiennes via SSE).

---

## Fichiers

| Fichier | Rôle |
|---|---|
| `views.py` | Endpoints REST analytics + notifications N8N + flux SSE |
| `visitor_data.py` | Lecture/cache du CSV visiteurs + fonctions de calcul analytique |
| `rag_pipeline.py` | Pipeline RAG (retrieval CSV + KB, appel Ollama) |
| `chat_view.py` | Endpoint `POST /api/chat/`, orchestre `rag_pipeline.py` |
| `urls.py` | Routage de tous les endpoints `history/`, `notifications/`, `prediction/`, `daily-report/` et `chat/` |
| `apps.py` | Configuration de l'app (`AppConfig`) |

---

## Endpoints

Base : `http://localhost:8000/api/`

### Analytics visiteurs

| Méthode | URL | Description |
|---|---|---|
| `GET` | `history/visitors/` | Historique journalier (genre/âge) |
| `GET` | `history/visitors/count/` | Comptage pour une date donnée |
| `GET` | `history/visitors/hourly/` | Flux horaire + heure de pointe |
| `GET` | `history/visitors/forecast/` | Prévision J+1 (régression linéaire) |
| `GET` | `history/summary/` | KPIs globaux (période, total, répartition) |
| `GET` | `history/cameras/` | Liste des caméras disponibles |

Paramètres communs (query string) : `date` (`YYYY-MM-DD`), `start_date` / `end_date`, `camera` (`Porte_nord` / `Porte_sud`).

### Chat RAG

| Méthode | URL | Description |
|---|---|---|
| `POST` | `chat/` | Question en langage naturel → réponse générée par Ollama, enrichie du contexte CSV + base de connaissances |

### Notifications & rapport quotidien (N8N)

| Méthode | URL | Vue | Description |
|---|---|---|---|
| `GET` | `notifications/latest/` | `latest_notification` | Dernière notification reçue |
| `GET` | `notifications/history/` | `notifications_history` | Historique complet (jusqu'à 100 entrées), tableau JSON brut |
| `GET` | `prediction/stream/` | `sse_stream` (alias `prediction_stream`) | Connexion SSE longue durée |
| `POST` | `daily-report/` | `daily_report` | Reçoit le payload prédictif depuis N8N et le diffuse en SSE |

---

## Flux de notifications temps réel

```
N8N (cron 6h00) ──POST──► /api/daily-report/ ──┬──► persistance JSON (history/notifications.json, 100 derniers)
                                                 └──► broadcast SSE ──► tous les clients connectés à /api/prediction/stream/
```

- `daily_report` valide la présence des champs requis (`type`, `date`, `message`, `prediction`), persiste le payload via `_append_notification()`, puis le diffuse immédiatement (`queue.put_nowait`) à tous les clients SSE actifs (`_sse_clients`).
- `sse_stream` ouvre une `StreamingHttpResponse` (`text/event-stream`) : émet un événement `connected` à l'ouverture, puis un événement nommé **`llm_report`** à chaque nouveau payload, avec un keepalive toutes les 30 secondes en l'absence d'activité.
- Le frontend (`hooks/useSSEPrediction.ts`) écoute spécifiquement l'événement `llm_report` (et non l'événement par défaut `message`).

**Format du payload attendu :**
```json
{
  "type": "llm_report",
  "date": "2026-06-16",
  "generated_at": "2026-06-16T06:00:00Z",
  "message": "...",
  "prediction": {
    "visiteurs_prevus": 412,
    "profil_dominant": "Familles",
    "niveau_affluence": "Élevé",
    "heure_pointe": "14:00 - 18:00"
  }
}
```

---

## Pipeline RAG (`rag_pipeline.py` + `chat_view.py`)

```
Question utilisateur
      │
      ├─► _build_csv_context()   — KPIs du jour extraits du CSV
      ├─► _retrieve_kb()         — similarité cosinus sur knowledge_base.json (embeddings Ollama)
      ▼
_build_prompt()                  — assemble contexte CSV + docs KB + question
      ▼
_call_ollama()                   — POST /api/generate sur Ollama
      ▼
{ "answer": "...", "model": "...", "sources": {...} }
```

Sans dépendance lourde (pas de ChromaDB ni `sentence-transformers`) : les embeddings sont délégués à Ollama via HTTP, le modèle étant déjà chargé en mémoire. Détail complet (frameworks RAG, paramètres d'inférence) dans `django_api/README.md`.

---

## `visitor_data.py`

Charge le CSV `data/shoppingclub_2025_2026.csv` en mémoire avec un **cache invalidé par `mtime`** : aucune recharge inutile si le fichier n'a pas changé sur disque. Le chemin du fichier est configurable via la variable d'environnement `VISITOR_DATA_CSV`.
