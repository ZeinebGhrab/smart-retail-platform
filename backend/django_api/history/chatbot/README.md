# `history/chatbot/` — Chat IA (RAG + Llama 3.2)

Sous-application dédiée au chat en langage naturel.  
L'utilisateur pose une question en français ; le pipeline RAG construit un contexte à partir des données visiteurs (CSV) et de la base de connaissance (JSON), puis délègue la génération à **Llama 3.2 3B via Ollama**.

---

## Architecture

```
Frontend
   │
   │  POST /api/chat/
   ▼
views.py  ──────────────────────────────►  rag_pipeline.run_rag_pipeline()
                                                │
                              ┌─────────────────┼─────────────────┐
                              ▼                 ▼                 ▼
                     _build_csv_context()  _retrieve_kb()   _build_prompt()
                     (CSV visiteurs)       (KB JSON via          │
                                           Ollama embeddings)    ▼
                                                          _call_ollama()
                                                          /api/generate
                                                          Llama 3.2 3B
```

---

## Endpoint

| Méthode | URL | Auth | Description |
|---|---|---|---|
| `POST` | `/api/chat/` | Non | Question en langage naturel |

**Corps de la requête :**
```json
{
  "question": "Nombre de visiteurs le 2026-05-30 ?",
  "history": [
    { "role": "user",      "content": "Et la semaine dernière ?" },
    { "role": "assistant", "content": "La semaine dernière : 1 240 visiteurs." }
  ]
}
```

> `history` est optionnel. Il permet de gérer les questions de suivi elliptiques  
> (ex : « Et hier ? » après « Combien de visiteurs aujourd'hui ? »).  
> Seuls les 6 derniers échanges sont injectés dans le prompt pour rester dans le `num_ctx`.

**Réponse :**
```json
{
  "answer": "📊 Le 2026-05-30 : 218 visiteurs — Porte_nord : 120, Porte_sud : 98.",
  "model": "llama3.2:3b-instruct-q4_K_M",
  "sources": {
    "csv":        "/app/data/shoppingclub_2025_2026.csv",
    "kb":         "/app/dataset/knowledge_base.json",
    "embeddings": "http://ollama:11434/api/embeddings"
  }
}
```

---

## Pipeline RAG — `rag_pipeline.py`

### Étape 1 — Retrieval CSV (`_build_csv_context`)

Lit le CSV visiteurs (chargé en cache, rechargé si le fichier change) et extrait :

| Détection dans la question | Données extraites |
|---|---|
| Date précise (`2026-05-30`, `30/05/2026`) | Total, par caméra, par genre, par tranche d'âge, top 5 heures de pointe |
| `hier` / `aujourd'hui` | Calculé par rapport à la **dernière date disponible** dans le CSV |
| `historique` / `derniers N jours` / `semaine` / `mois` | Tableau journalier + moyenne |
| `résumé` / `bilan` / `global` | Total toutes périodes, répartition genre et âge |
| Caméra (`nord`, `sud`) | Filtrage automatique sur `Porte_nord` / `Porte_sud` |

### Étape 2 — Retrieval KB (`_retrieve_kb`)

Recherche sémantique sur `knowledge_base.json` (8 documents FAQ).  
Embeddings calculés via `Ollama /api/embeddings` — **pas de `torch`** (trop lourd, 532 MB).  
Similarité cosine en Python pur. Seuil minimal : `0.45`.

**Fallback automatique** si Ollama est indisponible → recherche par mots-clés.

> La KB est **désactivée** pour les questions purement data (date précise, bilan global)  
> car elle n'apporterait que du bruit. Elle reste active pour les questions FAQ  
> (`politique`, `procédure`, `définition`, `conversion`, etc.).

### Étape 3 — Construction du prompt (`_build_prompt`)

```
[SYSTEM] Tu es l'assistant analytique d'Anavid Store 360...
=== DONNÉES VISITEURS (CSV) ===
...
=== BASE DE CONNAISSANCE (FAQ) ===   ← omis si non pertinent
...
=== HISTORIQUE DE LA CONVERSATION === ← omis si history vide
...
=== QUESTION ===
...
=== RÉPONSE ===
```

### Étape 4 — Génération (`_call_ollama`)

Appelle `Ollama /api/generate` avec les paramètres :

| Paramètre | Valeur |
|---|---|
| `temperature` | `0.1` (réponses déterministes) |
| `top_p` | `0.9` |
| `num_ctx` | `4096` tokens |
| `num_predict` | `1024` tokens max |
| `seed` | `42` |
| Timeout | `120 s` |

---

## Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://ollama:11434` | URL du service Ollama |
| `OLLAMA_MODEL` | `llama3.2:3b-instruct-q4_K_M` | Modèle à utiliser |
| `VISITOR_DATA_CSV` | `/app/data/shoppingclub_2025_2026.csv` | Chemin vers le CSV visiteurs |

---

## Gestion des erreurs Ollama

| Erreur | Message retourné |
|---|---|
| `ConnectionError` | Ollama non joignable — commande `docker compose up ollama` |
| `Timeout` | Timeout — modèle trop lent |
| HTTP 500 | Modèle non chargé — commande `ollama pull <model>` |

---

## Fichiers

| Fichier | Rôle |
|---|---|
| `views.py` | Endpoint `POST /api/chat/` — validation et délégation |
| `rag_pipeline.py` | Pipeline complet : CSV retrieval, KB retrieval, prompt, Ollama |
| `urls.py` | Route `chat/` (namespace `chatbot`) |
| `__init__.py` | Package Python |