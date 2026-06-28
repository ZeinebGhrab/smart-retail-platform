# `history/chatbot/` — Chat IA (RAG + ML Prediction + Llama 3.2)

Sous-application dédiée au chat en langage naturel.  
L'utilisateur pose une question en français ; le pipeline détecte automatiquement si elle porte sur des **données passées** (RAG CSV) ou sur des **visiteurs futurs** (prédiction ML), puis génère la réponse via **Llama 3.2 3B via Ollama**.

---

## Architecture

```
Frontend
   │
   │  POST /api/chat/
   ▼
views.py  ──────────────────────────────►  rag_pipeline.run_rag_pipeline()
                                                │
                                    _is_future_prediction_query()
                                         │             │
                              ┌──────────┘             └──────────┐
                         PASSÉ (RAG)                   FUTUR (ML)
                              │                              │
                ┌─────────────┼──────────┐        ┌─────────┼──────────┐
                ▼             ▼          ▼         ▼         ▼          ▼
       _build_csv_context  _retrieve_kb  │  _fetch_weather  _fetch_    _retrieve_kb
       (CSV visiteurs)     (KB JSON via  │  (Open-Meteo     holidays_tn (KB JSON —
                           embeddings)   │   Sfax)          (Nager.Date) modèle ML)
                                         │         └────────────┘
                                         │               │
                                         │    _fetch_ml_prediction()
                                         │    POST /predict → LightGBM
                                         │               │
                                         └───── _build_ml_context()
                                                         │
                                              ┌──────────┘
                                              ▼
                                        _build_prompt()
                                              │
                                              ▼
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
  "question": "Combien de visiteurs demain ?",
  "history": [
    { "role": "user",      "content": "Et la semaine dernière ?" },
    { "role": "assistant", "content": "La semaine dernière : 1 240 visiteurs." }
  ]
}
```

> `history` est optionnel. Il permet de gérer les questions de suivi elliptiques  
> (ex : « Et demain ? » après une question sur aujourd'hui).  
> Seuls les 6 derniers échanges sont injectés dans le prompt pour rester dans le `num_ctx`.

**Réponse — mode RAG (données passées) :**
```json
{
  "answer": "📊 Le 2026-05-30 : 218 visiteurs — Porte_nord : 120, Porte_sud : 98.",
  "model": "llama3.2:3b-instruct-q4_K_M",
  "mode": "rag",
  "sources": {
    "csv":        "/app/data/shoppingclub_2025_2026.csv",
    "ml_api":     null,
    "kb":         "/app/dataset/knowledge_base.json",
    "embeddings": "http://ollama:11434/api/embeddings"
  }
}
```

**Réponse — mode ML Prediction (visiteurs futurs) :**
```json
{
  "answer": "🔮 Demain (2026-06-29) : environ 1 430 visiteurs attendus (jour normal, 34°C).",
  "model": "llama3.2:3b-instruct-q4_K_M",
  "mode": "ml_prediction",
  "sources": {
    "csv":        null,
    "ml_api":     "http://visitor-ml-api:8000/predict",
    "kb":         "/app/dataset/knowledge_base.json",
    "embeddings": "http://ollama:11434/api/embeddings"
  }
}
```

> Le champ `mode` (`"rag"` ou `"ml_prediction"`) indique la branche empruntée — utile pour le frontend et le débogage.

---

## Pipeline — `rag_pipeline.py`

### Étape 0 — Détection d'intention (`_is_future_prediction_query`)

Point d'entrée du routing. Deux niveaux de détection :

**Niveau 1 — date explicite (sans appel LLM) :**  
Si la question contient une date parseable (`2026-12-25`, `25/12/2026`), elle est comparée à la date du jour. Décision calendaire fiable à 100 %.

**Niveau 2 — classification sémantique (`_classify_intent_llm`) :**  
Pour toutes les autres formulations, un micro-appel Ollama est effectué avec un prompt minimaliste :

```
Réponds UNIQUEMENT par un seul mot : FUTUR ou PASSE.
La question porte-t-elle sur des visiteurs à venir ou des données déjà enregistrées ?
```

Paramètres : `temperature=0.0`, `num_predict=4`, timeout 10 s.  
Résistant aux fautes d'orthographe et aux formulations libres (ex : *"y'aura combien de monde la s'maine prochaine ?"*).  
Si Ollama est indisponible → défaut `PASSE` (comportement conservateur).

---

### Branche PASSÉ — RAG CSV

#### Étape 1 — Retrieval CSV (`_build_csv_context`)

Lit le CSV visiteurs (chargé en cache, rechargé si le fichier change) et extrait :

| Détection dans la question | Données extraites |
|---|---|
| Date précise (`2026-05-30`, `30/05/2026`) | Total, par caméra, par genre, par tranche d'âge, top 5 heures de pointe |
| `hier` / `aujourd'hui` | Calculé par rapport à la **dernière date disponible** dans le CSV |
| `historique` / `derniers N jours` / `semaine` / `mois` | Tableau journalier + moyenne |
| `résumé` / `bilan` / `global` | Total toutes périodes, répartition genre et âge |
| Caméra (`nord`, `sud`) | Filtrage automatique sur `Porte_nord` / `Porte_sud` |

#### Étape 2 — Retrieval KB (`_retrieve_kb`)

Recherche sémantique sur `knowledge_base.json` (8 documents FAQ).  
Embeddings calculés via `Ollama /api/embeddings` — **pas de `torch`** (532 MB évités).  
Similarité cosine en Python pur. Seuil minimal : `0.45`.

**Fallback automatique** si Ollama est indisponible → recherche par mots-clés.

> La KB est **désactivée** pour les questions purement data (date précise, bilan global)  
> car elle n'apporterait que du bruit. Elle reste active pour les questions FAQ  
> (`politique`, `procédure`, `définition`, `conversion`, etc.).

---

### Branche FUTUR — ML Prediction

#### Étape 1 — Extraction des dates futures (`_extract_future_dates`)

Détecte et normalise les références temporelles futures dans la question :

| Formulation | Dates générées |
|---|---|
| `2026-12-25` / `25/12/2026` (date future) | Cette date uniquement |
| `demain` | J+1 |
| `semaine prochaine` | Lundi → dimanche de la semaine suivante (7 dates) |
| `mois prochain` | 7 premiers jours du mois suivant |
| Aucune date détectée | J+1 par défaut |

Maximum 14 dates par requête pour limiter les appels API.

#### Étape 2 — Météo prévue (`_fetch_weather`)

Appelle **Open-Meteo** avec les coordonnées Sfax (`34.7406, 10.7603`) :

```
GET https://api.open-meteo.com/v1/forecast
    ?latitude=34.7406&longitude=10.7603
    &daily=temperature_2m_max,wind_speed_10m_max
    &timezone=Africa/Tunis
    &start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
```

Retourne `temperature_2m_max` (°C) et `wind_speed_10m_max` (km/h).  
Résultats mis en **cache par date** (un seul appel même si la date revient plusieurs fois).  
Fallback si hors horizon (>16 j) ou Open-Meteo indisponible : `32°C / 15 km/h` (valeurs typiques Sfax été).

#### Étape 3 — Statut jour férié (`_fetch_holidays_tn` + `_get_type_jour`)

Appelle **Nager.Date** pour récupérer les jours fériés tunisiens de l'année :

```
GET https://date.nager.at/api/v3/PublicHolidays/{year}/TN
```

Retourne un `set` de dates `YYYY-MM-DD` mis en **cache par année**.  
`_get_type_jour` retourne `"ferie"` ou `"normal"` (champ `type_jour` attendu par le modèle LightGBM).

#### Étape 4 — Prédiction ML (`_fetch_ml_prediction`)

Appelle le service **FastAPI LightGBM** (`visitor_ml_api`) avec les features enrichies :

```
POST http://visitor-ml-api:8000/predict
{
  "date":        "2026-07-25",
  "temperature": 36.2,
  "wind_speed":  12.0,
  "type_jour":   "ferie"
}
```

Le modèle retourne une liste de prédictions par heure × caméra. La fonction agrège les `total_visits` par heure pour obtenir le **total journalier**.

#### Étape 5 — Construction du contexte ML (`_build_ml_context`)

Formate toutes les prédictions en bloc texte injecté dans le prompt Ollama :

```
=== PRÉVISIONS ML (LightGBM — features météo + calendrier) ===
  2026-07-25 : 1847 visiteurs prévus
    └─ jour férié 🎉 | météo prévue : 36.2°C, vent 12.0 km/h
  2026-07-26 : 1203 visiteurs prévus
    └─ jour normal | météo prévue : 35.8°C, vent 14.5 km/h

Note : prévisions basées sur les données historiques, la météo Open-Meteo
et les jours fériés tunisiens (Nager.Date). Il s'agit d'estimations.
```

Le LLM peut ainsi contextualiser sa réponse (ex : affluence élevée car jour férié, ou réduite par la chaleur).

---

### Étape finale — Prompt et génération

#### Construction du prompt (`_build_prompt`)

```
[SYSTEM] Tu es l'assistant analytique d'Anavid Store 360...
         Quand des prévisions ML sont disponibles, précise toujours qu'il s'agit d'estimations.

=== PRÉVISIONS ML (LightGBM — features météo + calendrier) ===   ← mode ML uniquement
...

=== DONNÉES VISITEURS HISTORIQUES (CSV) ===                       ← mode RAG uniquement
...

=== BASE DE CONNAISSANCE (FAQ) ===                                ← si pertinent
...

=== HISTORIQUE DE LA CONVERSATION ===                             ← si history non vide
...

=== QUESTION ===
...
=== RÉPONSE ===
```

#### Génération (`_call_ollama`)

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
| `OLLAMA_MODEL` | `llama3.2:3b-instruct-q4_K_M` | Modèle Ollama |
| `VISITOR_DATA_CSV` | `/app/data/shoppingclub_2025_2026.csv` | Chemin vers le CSV visiteurs |
| `ML_API_HOST` | `http://visitor-ml-api:8000` | URL du service FastAPI LightGBM |

---

## APIs externes utilisées

| Service | URL | Usage | Fallback |
|---|---|---|---|
| **Open-Meteo** | `api.open-meteo.com/v1/forecast` | Météo prévue (temp, vent) pour Sfax | `32°C / 15 km/h` |
| **Nager.Date** | `date.nager.at/api/v3/PublicHolidays/{year}/TN` | Jours fériés tunisiens | `set()` vide (tous jours normaux) |
| **FastAPI ML** | `visitor-ml-api:8000/predict` | Prédiction visiteurs (LightGBM) | Erreur remontée au LLM |
| **Ollama** | `ollama:11434/api/generate` + `/api/embeddings` | Génération + embeddings KB | Messages d'erreur explicites |

---

## Gestion des erreurs

| Service | Erreur | Comportement |
|---|---|---|
| Ollama `/api/generate` | `ConnectionError` | Message utilisateur + commande `docker compose up ollama` |
| Ollama `/api/generate` | `Timeout` | Message utilisateur |
| Ollama HTTP 500 | Modèle non chargé | Message + commande `ollama pull <model>` |
| Ollama classification | Indisponible | Défaut `PASSE` → mode RAG CSV |
| Open-Meteo | Indisponible / hors horizon | Fallback valeurs Sfax été |
| Nager.Date | Indisponible | `set()` vide → tous les jours traités comme normaux |
| FastAPI ML | `ConnectionError` / `Timeout` / HTTP error | Erreur incluse dans le contexte LLM |

---

## Fichiers

| Fichier | Rôle |
|---|---|
| `views.py` | Endpoint `POST /api/chat/` — validation et délégation |
| `rag_pipeline.py` | Pipeline complet : routing, RAG CSV, ML prediction, prompt, Ollama |
| `urls.py` | Route `chat/` (namespace `chatbot`) |
| `__init__.py` | Package Python |