# Anavid Store 360 — Smart Retail Platform

## README détaillé

Plateforme d'analyse retail intelligente combinant un frontend Ionic/React, une API Django (analytics + chat IA RAG), un LLM local servi par Ollama, et une stack de benchmark/sélection automatique de modèle.

---

## Sommaire

1. [Présentation générale](#1-présentation-générale)
2. [Architecture globale](#2-architecture-globale)
3. [Pipeline RAG](#3-pipeline-rag)
4. [Agent RAG CLI](#4-agent-rag-cli)
5. [Frontend](#5-frontend)
6. [Backend Django — API REST](#6-backend-django--api-rest)
7. [Benchmark LLM](#7-benchmark-llm)
8. [Données](#8-données)
9. [Installation et lancement](#9-installation-et-lancement)
10. [Variables d'environnement](#10-variables-denvironnement)
11. [Structure complète du projet](#11-structure-complète-du-projet)
12. [Commandes Makefile / run.bat](#12-commandes-makefile--runbat)
13. [Dépannage (FAQ)](#13-dépannage-faq)

---

## 1. Présentation générale

Anavid Store 360 est une plateforme retail composée de cinq services orchestrés via Docker Compose :

| Service | Rôle |
|---|---|
| `frontend` | Application Ionic/React (Vite) — Chat IA et tableau de bord historique |
| `django_api` | API REST Django (analytics visiteurs + endpoint Chat RAG) |
| `ollama` | Serveur LLM local (génération + embeddings) |
| `agent` | Agent RAG CLI (tool calling + base vectorielle Chroma) |
| `benchmark` | Service one-shot de sélection automatique du modèle LLM |

L'objectif : permettre à un gérant de magasin de poser des questions en langage naturel (fréquentation, flux horaire, prévisions, définitions métier) et de consulter un tableau de bord analytique, tout en garantissant la **confidentialité totale des données** (LLM local, aucune donnée envoyée à un service cloud).

---

## 2. Architecture globale

```
┌─────────────────────────────────────────────────────────────────┐
│  docker-compose                                                  │
│                                                                  │
│  ┌──────────────┐     HTTP :5173     ┌───────────────────────┐  │
│  │   frontend   │ ◄────────────────► │   Utilisateur         │  │
│  │ Ionic/React  │                    └───────────────────────┘  │
│  │  ChatIA.tsx  │                                                │
│  │  Historique  │                                                │
│  └──────┬───────┘                                                │
│         │ POST /api/chat/, GET /api/history/*  (HTTP :8000)      │
│         ▼                                                        │
│  ┌──────────────┐                                                │
│  │  django_api  │  API REST historique visiteurs + Chat RAG      │
│  │   Django 5   │  Pipeline RAG :                                │
│  │              │   1. Retrieval CSV  (volume ./backend/data)    │
│  │  rag_        │   2. Retrieval KB   (volume ./backend/dataset) │
│  │  pipeline.py │   3. Prompt Builder                            │
│  └──────┬───────┘                                                │
│         │ HTTP :11434  (réseau Docker interne)                   │
│         ▼                                                        │
│  ┌──────────────┐                                                │
│  │    ollama    │  LLM local                                     │
│  │              │  Modèle retenu : llama3.2:3b-instruct-q4_K_M  │
│  │  /api/generate    (génération)                                │
│  │  /api/embeddings  (recherche sémantique KB)                   │
│  └──────────────┘                                                │
│                                                                  │
│  ┌──────────────┐  (optionnel)                                   │
│  │    agent     │  Agent RAG CLI (visitor_agent.py)              │
│  │              │  Tool calling + ChromaDB (SA-data.xlsx)        │
│  └──────────────┘                                                │
│                                                                  │
│  ┌──────────────┐  (one-shot)                                    │
│  │  benchmark   │  Sélection automatique du modèle               │
│  └──────────────┘                                                │
└─────────────────────────────────────────────────────────────────┘
```

### Communication interne Docker

```
frontend   ──► django_api  via http://localhost:8000  (depuis le navigateur)
django_api ──► ollama       via http://ollama:11434    (réseau Docker interne)
agent      ──► ollama       via http://ollama:11434    (réseau Docker interne)
```

---

## 3. Pipeline RAG

Implémenté dans `backend/django_api/history/rag_pipeline.py` et exposé via `chat_view.py` (`POST /api/chat/`).

### Pourquoi sans torch / ChromaDB dans `django_api` ?

- `torch` seul représente ~532 Mo téléchargés au build du conteneur.
- La base de connaissance (`knowledge_base.json`) ne contient que 8 documents : ChromaDB serait disproportionné.
- Ollama expose déjà `/api/embeddings` → réutilisé directement pour la recherche sémantique.

### Étapes du pipeline

```
Question utilisateur (langage naturel)
        │
        ├──► Retrieval CSV ──────────────────────────────────────────►┐
        │    shoppingclub_2025_2026.csv                                │
        │    Extrait : date, caméra, genre, âge, flux horaire          │
        │                                                              │
        ├──► Retrieval KB (8 docs) ─────────────────────────────────►┤
        │    knowledge_base.json                                       │
        │    Embeddings via Ollama /api/embeddings + cosine similarity │
        │    (pas de torch, pas de ChromaDB dans ce conteneur)         │
        │                                                              ▼
        └──► Prompt Builder ──────────────────────────────────────────►
                                                                       │
                                        ┌──────────────────────────── ▼
                                        │  Ollama /api/generate
                                        │  llama3.2:3b-instruct-q4_K_M
                                        │  temperature=0.1, num_ctx=4096
                                        └──────────────────────────── ▼
                                                              Réponse JSON
                                                         { answer, model, sources }
```

### Fonctions clés (`rag_pipeline.py`)

| Fonction | Rôle |
|---|---|
| `_load_csv()` | Charge et met en cache `shoppingclub_2025_2026.csv`, normalise dates/heures/caméras |
| `_build_csv_context(question)` | Extrait date, caméra et nombre de jours de la question ; construit un résumé chiffré (totaux, genre, âge, heures de pointe) |
| `_retrieve_kb(question)` | Recherche sémantique sur `knowledge_base.json` via embeddings Ollama + similarité cosinus |
| `_build_prompt(question, contexts)` | Assemble le contexte CSV + KB + question dans un prompt structuré |
| `_call_ollama(prompt)` | Appelle `/api/generate` avec `temperature=0.1`, `num_ctx=4096` |

### Exemple d'appel direct

```bash
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"question": "Nombre de visiteurs le 2026-05-30 ?"}'
```

Réponse :

```json
{
  "answer": "📊 Visiteurs du 2026-05-30 :\n  • Total : 7\n  • Cam porte1 : 5\n  • Cam_porte2 : 2",
  "model": "llama3.2:3b-instruct-q4_K_M",
  "sources": {
    "csv": "/app/data/shoppingclub_2025_2026.csv",
    "kb": "/app/dataset/knowledge_base.json",
    "embeddings": "http://ollama:11434/api/embeddings"
  }
}
```

### Exemples de questions supportées

```
Nombre de visiteurs le 2026-05-30 ?
Flux horaire hier Porte_nord
Historique des 7 derniers jours
Prévision pour demain
Résumé global de la période
Qu'est-ce que le taux de conversion ?
Quelles caméras sont installées ?
```

---

## 4. Agent RAG CLI

Implémenté dans `backend/app/` (conteneur `agent`), indépendant de `django_api`. Architecture en "équipe de 3 fichiers" :

### `visitor_data.py` — le comptable

Lit `data/SA-data.xlsx` (feuilles `Per_Day` / `Per_Hour`) et expose :

| Fonction | Usage |
|---|---|
| `get_visitor_count(date, camera)` | Total visiteurs + détail genre/âge pour une date donnée |
| `get_hourly_visitor_flow(date, camera)` | Flux horaire (avec `ffill()` pour gérer les cellules fusionnées Excel) |
| `forecast_visitors(target_date, camera)` | Prévision — régression linéaire + ajustement jour de semaine dès ≥ 7 jours d'historique ; sinon `model_status: "non_entraine"` avec repli sur la dernière valeur connue |

Toutes les fonctions normalisent `"null"`/`"none"`/`""` en `None` pour éviter les erreurs `pd.to_datetime`.

### `vector_store.py` — le bibliothécaire

- Indexe `dataset/knowledge_base.json` (8 fiches FAQ) dans **ChromaDB**, persisté dans `vector_db/`.
- Utilise `DefaultEmbeddingFunction()` (modèle ONNX intégré, sans torch/sentence-transformers/CUDA).
- `reindex()` : reconstruction complète de l'index.
- `semantic_search(query, n_results)` : recherche par sens (auto-reindex si collection vide).

### `visitor_agent.py` — le chef d'orchestre

Point d'entrée : `answer_query(question)`.

```
question utilisateur
   │
   ▼
1. Prompt = TOOLS_SPEC + question
   │
   ▼
2. Appel Ollama /api/generate (modèle lu dans results/eligible_models.json)
   │
   ▼
3. Le LLM répond en JSON pur : {"tool": "...", "parameters": {...}}
   │
   ▼
4. parse_tool_call() extrait le JSON
   │
   ├─ JSON valide ──► _clean_params() ──► run_tool()
   │                  exécute la fonction Python correspondante (SA-data.xlsx / Chroma)
   │
   └─ JSON invalide / Ollama down ──► FALLBACK PAR MOTS-CLÉS :
        - "prévi/prédi/demain" → forecast_visitors
        - "horaire/flux/heure" → get_hourly_visitor_flow
        - "visiteur/visite"    → get_visitor_count
        - sinon                → search_knowledge_base
```

#### Les 4 outils exposés au LLM

| Outil | Quand l'utiliser |
|---|---|
| `get_visitor_count` | "combien de visiteurs..." |
| `get_hourly_visitor_flow` | "flux horaire...", "heure de pointe" |
| `forecast_visitors` | "prévision", "demain", "prédire" |
| `search_knowledge_base` | questions générales / définitions (FAQ métier) |

#### Pourquoi ce double niveau (LLM + fallback) ?

Le benchmark mesure que Llama 3.2 3B produit du JSON valide ~94 % du temps. Le fallback par mots-clés garantit qu'une réponse pertinente sort toujours, même si le modèle local renvoie un JSON malformé ou si Ollama est éteint.

#### Pourquoi pas de RAG vectoriel sur `SA-data.xlsx` ?

- **Chiffres exacts** → recherche par filtre/agrégat exact (équivalent Ctrl+F), pour éviter des chiffres approximatifs.
- **Texte non structuré** (FAQ, définitions) → recherche sémantique (Chroma), utile quand l'utilisateur ne formule pas la question avec les mots exacts.

### Utilisation

```bash
# Linux/Mac
make reindex
make ask Q="Combien de visiteurs hier ?"
make ask Q="Quelle est la définition du taux de conversion ?"

# Windows
run.bat reindex
run.bat ask "Combien de visiteurs hier ?"
```

---

## 5. Frontend

Application **Ionic/React** (Vite, TypeScript).

### Structure

```
frontend/src/
├── App.tsx                  # Routing principal (IonReactRouter)
├── main.tsx                 # Point d'entrée React
├── components/
│   ├── TabBar.tsx            # Barre de navigation inférieure
│   └── TabBar.css
├── pages/
│   ├── ChatIA.tsx             # Interface de chat RAG (POST /api/chat/)
│   ├── ChatIA.css
│   ├── Historique.tsx         # Dashboard analytique (visiteurs, flux, prévisions)
│   └── Historique.css
├── services/
│   └── api.ts                 # Client HTTP centralisé vers Django (VITE_API_URL)
└── theme/
    └── variables.css          # Thème Ionic (couleurs, typographie)
```

### Routage (`App.tsx`)

| Route | Composant | Description |
|---|---|---|
| `/chat` | `ChatIA` | Chat IA — RAG |
| `/predictions` | `Historique` | Dashboard analytique / historique visiteurs |
| `/` | redirige vers `/chat` | — |

### Configuration

`frontend/.env` :

```
VITE_API_URL=http://localhost:8000/api
```

### Démarrage en développement

```bash
docker compose up frontend
# → http://localhost:5173, hot-reload activé (volume monté)
```

---

## 6. Backend Django — API REST

Dossier `backend/django_api/` (port 8000, conteneur `django_api`).

### Structure

```
backend/django_api/
├── manage.py
├── Dockerfile                  # Image légère ~400 MB (sans torch)
├── requirements.txt            # Django, DRF, pandas, requests, drf-spectacular
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
└── history/
    ├── views.py                 # Endpoints analytics
    ├── visitor_data.py           # Lecture CSV + calculs analytiques
    ├── rag_pipeline.py            # Pipeline RAG (cf. section 3)
    ├── chat_view.py               # Endpoint POST /api/chat/
    ├── urls.py                    # Routing
    └── apps.py
```

### Endpoints REST

Documentation Swagger interactive : `http://localhost:8000/api/docs/`

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat/` | Chat IA RAG — question en langage naturel |
| `GET` | `/api/history/visitors/` | Historique journalier (genre, âge) |
| `GET` | `/api/history/visitors/count/` | Nombre de visiteurs par date |
| `GET` | `/api/history/visitors/hourly/` | Flux horaire par date |
| `GET` | `/api/history/visitors/forecast/` | Prévision (régression linéaire + ajustement jour de semaine) |
| `GET` | `/api/history/summary/` | KPIs globaux |
| `GET` | `/api/history/cameras/` | Liste des caméras |

### Paramètres communs

| Paramètre | Format | Exemple |
|---|---|---|
| `date` | `YYYY-MM-DD` | `?date=2026-05-30` |
| `start_date` | `YYYY-MM-DD` | `?start_date=2026-05-01` |
| `end_date` | `YYYY-MM-DD` | `?end_date=2026-05-30` |
| `camera` | `Porte_nord` ou `Porte_sud` | `?camera=Porte_nord` |

### Exemples curl

```bash
curl http://localhost:8000/api/history/visitors/count/?date=2026-05-30
curl http://localhost:8000/api/history/visitors/hourly/?date=2026-05-30&camera=Porte_nord
curl http://localhost:8000/api/history/visitors/forecast/
curl http://localhost:8000/api/history/summary/
curl http://localhost:8000/api/history/cameras/
```

---

## 7. Benchmark LLM

Le service `benchmark` sélectionne automatiquement le meilleur modèle Ollama selon la VRAM disponible et 5 critères : TTFT, débit, fidélité JSON (tool calling), anti-hallucination, dégradation contexte long.

### Configuration (`backend/scripts/config.py`)

```python
VRAM_AVAILABLE_GB = 5.5   # ← Adapter à votre machine

CANDIDATE_MODELS = [
    {"id": "llama3.2:3b-instruct-q4_K_M", "params_b": 3, ...},
    {"id": "qwen2.5:7b-instruct-q4_K_M",  "params_b": 7, ...},
    {"id": "mistral:7b-instruct-v0.3-q4_K_M", "params_b": 7, ...},
]

THRESHOLDS = {
    "ttft_max_sec": 1.5,
    "throughput_min_tps": 20.0,
    "throughput_hard_min": 10.0,
    "json_success_min_pct": 95.0,
}

INFERENCE_OPTIONS = {
    "temperature": 0.1,
    "top_p": 0.9,
    "num_ctx": 4096,
    "num_predict": 256,
}

N_WARMUP = 1
N_RUNS   = 3
```

> Règle empirique pour la VRAM requise : `VRAM ≈ params_b × 0.7 + 2.0 Go` (quantification q4_K_M).

### Scoring

| Critère | Poids | Condition |
|---|---|---|
| TTFT | 25 pts | ≤ 1.5 s → 25 pts \| ≤ 3.0 s → 12 pts \| > 3 s → 0 pt |
| Throughput | 25 pts | ≥ 20 t/s → 25 pts \| ≥ 10 t/s → 12 pts \| < 10 → 0 pt |
| JSON Tool Calling | 35 pts | ≥ 95 % → 35 pts \| sinon proportionnel |
| Anti-Hallucination | 15 pts | Réponse fidèle → 15 pts \| invention → 0 pt |
| **Total** | **100 pts** | **✅ RECOMMANDÉ** si tous les seuils sont validés |

### Résultats du benchmark (06/2026)

| Critère | Valeur | Seuil |
|---|---|---|
| TTFT moyen | **0.246 s** | ≤ 1.5 s ✅ |
| Débit | **68.3 tokens/s** | ≥ 20 t/s ✅ |
| JSON valide (tool calling) | **90 %** | ≥ 95 % ⚠️ |
| Modèle retenu | `llama3.2:3b-instruct-q4_K_M` | — |

### Comparatif des modèles candidats

| Critère | Qwen 2.5 7B (q4_K_M) | Mistral 7B v0.3 (q4_K_M) | Llama 3.2 3B (q4_K_M) | GPT-3.5 / GPT-4 (référence cloud) |
|---|---|---|---|---|
| Architecture | Transformer decoder-only, open-source | Transformer decoder-only, open-source | Transformer decoder-only, open-source, léger | Transformer propriétaire (API cloud) |
| Déploiement | Local (Ollama/Docker) | Local (Ollama/Docker) | Local (Ollama/Docker) | Cloud API (payant, dépendance externe) |
| VRAM requise | 6.9 Go | 6.9 Go | 4.1 Go | N/A |
| Multilingue (FR/AR/EN) | Très bon | Bon (AR plus faible) | Correct (AR limité) | Excellent |
| Confidentialité | Totale | Totale | Totale | Données envoyées vers le cloud |
| Coût | Gratuit | Gratuit | Gratuit | Payant à l'usage |

**Recommandation** : Qwen 2.5 7B si VRAM ≥ 6.9 Go (meilleur FR/AR + tool calling) ; Mistral 7B comme alternative débit ; Llama 3.2 3B en repli sur matériel contraint (≤ 5.5 Go), choix retenu pour la configuration testée. La solution cloud n'est pas retenue pour des raisons de confidentialité des données retail.

### Lancer le benchmark

```bash
make bench
# ou
docker compose run --rm benchmark
```

Fichiers générés dans `backend/results/` :

| Fichier | Contenu |
|---|---|
| `eligible_models.json` | Modèles retenus après filtrage VRAM (lu par `django_api` et `agent`) |
| `result_<model_id>.json` | Rapport détaillé par modèle |
| `benchmark_report.json` | Rapport global comparatif |

---

## 8. Données

| Fichier | Description |
|---|---|
| `backend/data/shoppingclub_2025_2026.csv` | Historique visiteurs (~59 000 lignes) — utilisé par `django_api` (RAG + analytics) |
| `backend/data/SA-data.xlsx` | Historique visiteurs (feuilles `Per_Day` / `Per_Hour`) — utilisé par l'agent CLI (`backend/app/`) |
| `backend/dataset/knowledge_base.json` | 8 fiches FAQ métier (taux de conversion, horaires, politique de confidentialité, etc.), indexées par embeddings |
| `backend/dataset/tool_calling_queries.json` | 50 requêtes métier (FR + AR) pour le benchmark tool calling |
| `backend/vector_db/` | Index ChromaDB persistant (généré par l'agent) |
| `backend/results/` | Rapports de benchmark JSON |

### Mettre à jour les données

- **CSV visiteurs** : remplacer `backend/data/shoppingclub_2025_2026.csv` (même format) — cache invalidé automatiquement à la prochaine requête.
- **Base de connaissances** : éditer `backend/dataset/knowledge_base.json` (format `{ "id", "title", "content" }`) — embeddings recalculés au prochain démarrage de `django_api`, ou via `make reindex` pour l'agent.

---

## 9. Installation et lancement

### Prérequis

| Outil | Version minimale | Obligatoire |
|---|---|---|
| Docker Desktop | 24+ | ✅ |
| docker compose | v2 (`docker compose`) | ✅ |
| GPU NVIDIA + drivers | — | ⚠️ recommandé |
| nvidia-container-toolkit | — | si GPU |
| make | — | optionnel (Linux/Mac) |

> **Sans GPU** : Ollama tourne en CPU (~5-10 tokens/s pour le modèle 3B). Retirez le bloc `deploy.resources` dans `docker-compose.yml`.
> **VRAM requise** : Llama 3.2 3B q4_K_M ≈ 4.1 Go. Ajustez `VRAM_AVAILABLE_GB` dans `backend/scripts/config.py` si vous relancez le benchmark.

### Premier lancement

```bash
git clone <url-du-repo>
cd anavid-smart-retail-platform

docker compose up --build
```

Accès :
- Frontend → http://localhost:5173
- API → http://localhost:8000/api/
- Swagger → http://localhost:8000/api/docs/
- Ollama → http://localhost:11434

### Lancement par service

```bash
# Ollama seul (LLM)
docker compose up ollama

# API Django + Ollama
docker compose up --build django_api ollama

# Stack complète (sans benchmark)
docker compose up --build ollama django_api frontend

# Avec Make (Linux/Mac)
make up
```

### Rebuild après modification du code

```bash
docker compose build django_api
docker compose up django_api
```

> Le frontend utilise un volume monté avec hot-reload : pas besoin de rebuild après modification d'un fichier `.tsx`/`.css`.

---

## 10. Variables d'environnement

### `django_api` (définies dans `docker-compose.yml`)

| Variable | Valeur par défaut | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://ollama:11434` | URL du conteneur Ollama |
| `OLLAMA_MODEL` | `llama3.2:3b-instruct-q4_K_M` | Modèle LLM utilisé |
| `VISITOR_DATA_CSV` | `/app/data/shoppingclub_2025_2026.csv` | Chemin du CSV visiteurs |
| `DJANGO_DEBUG` | `true` | Mode debug Django |

### `agent` (définies dans `docker-compose.yml`)

| Variable | Valeur par défaut | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://ollama:11434` | URL du conteneur Ollama |
| `PYTHONUNBUFFERED` | `1` | Logs Python non bufferisés |

### `frontend` (fichier `frontend/.env`)

| Variable | Valeur | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000/api` | URL de l'API Django |

### Changer de modèle sans rebuild

```yaml
# docker-compose.yml → service django_api → environment
- OLLAMA_MODEL=qwen2.5:7b-instruct-q4_K_M
```

```bash
docker compose up django_api   # redémarrage suffit, pas de rebuild
```

---

## 11. Structure complète du projet

```
anavid-smart-retail-platform/
│
├── docker-compose.yml               # Orchestration des 5 services
├── Makefile                         # Commandes raccourcies (Linux/Mac)
├── run.bat                          # Commandes raccourcies (Windows)
├── README.md                        # Présentation rapide
├── README_DETAILLE.md               # Ce fichier
│
├── frontend/                        # App Ionic React (Vite)
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json / package-lock.json
│   ├── vite.config.ts
│   ├── tsconfig.json / tsconfig.node.json
│   ├── ionic.config.json
│   ├── eslint.config.js
│   ├── index.html
│   ├── .env                          # VITE_API_URL=http://localhost:8000/api
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       ├── vite-env.d.ts
│       ├── components/
│       │   ├── TabBar.tsx
│       │   └── TabBar.css
│       ├── pages/
│       │   ├── ChatIA.tsx
│       │   ├── ChatIA.css
│       │   ├── Historique.tsx
│       │   └── Historique.css
│       ├── services/
│       │   └── api.ts
│       └── theme/
│           └── variables.css
│
├── backend/
│   │
│   ├── Dockerfile                   # Image de base du conteneur agent
│   ├── requirements.txt             # pandas, chromadb, requests, etc.
│   │
│   ├── django_api/                  # API REST Django (port 8000)
│   │   ├── Dockerfile               # Image légère ~400 MB (sans torch)
│   │   ├── requirements.txt         # Django, DRF, pandas, requests
│   │   ├── manage.py
│   │   ├── db.sqlite3
│   │   ├── config/
│   │   │   ├── settings.py
│   │   │   ├── urls.py
│   │   │   ├── asgi.py
│   │   │   └── wsgi.py
│   │   └── history/
│   │       ├── views.py             # Endpoints historique visiteurs
│   │       ├── visitor_data.py      # Lecture CSV + calculs analytiques
│   │       ├── rag_pipeline.py      # Pipeline RAG (Retrieval + Ollama)
│   │       ├── chat_view.py         # Endpoint POST /api/chat/
│   │       ├── urls.py              # Routing URLs
│   │       └── apps.py
│   │
│   ├── app/                         # Agent RAG CLI (conteneur agent)
│   │   ├── README.md                # Documentation détaillée de l'agent
│   │   ├── visitor_agent.py         # Agent tool calling (Ollama)
│   │   ├── visitor_data.py          # Fonctions analytiques (SA-data.xlsx)
│   │   └── vector_store.py          # ChromaDB (conteneur agent uniquement)
│   │
│   ├── scripts/                     # Benchmark LLM
│   │   ├── config.py                # VRAM, modèles candidats, seuils
│   │   ├── pull_models.py           # Filtrage VRAM + pull Ollama
│   │   └── benchmark.py             # TTFT, throughput, JSON, hallucinations
│   │
│   ├── data/
│   │   ├── shoppingclub_2025_2026.csv   # Historique visiteurs (~59 000 lignes)
│   │   └── SA-data.xlsx                 # Historique visiteurs (Per_Day / Per_Hour)
│   │
│   ├── dataset/
│   │   ├── knowledge_base.json      # FAQ métier (8 docs, indexés par Ollama/Chroma)
│   │   └── tool_calling_queries.json # 50 requêtes benchmark (FR + AR)
│   │
│   ├── vector_db/                   # Index ChromaDB (conteneur agent)
│   │   └── chroma.sqlite3
│   │
│   ├── results/                     # Rapports de benchmark générés
│   │   ├── benchmark_report.json
│   │   ├── eligible_models.json
│   │   └── result_llama3.2_3b-instruct-q4_K_M.json
│   │
│   └── README.md                    # Documentation détaillée backend/benchmark
```

---

## 12. Commandes Makefile / run.bat

```bash
make up            # Démarre Ollama + benchmark + stack complète
make ollama        # Démarre Ollama seul
make bench         # Lance le benchmark (Ollama doit tourner)
make backend       # Django + Frontend (sans Ollama)
make frontend      # Frontend seul (hot-reload)
make django        # Django seul (avec rebuild)
make reindex       # Reconstruit l'index ChromaDB (conteneur agent)
make ask Q="..."   # Pose une question à l'agent CLI
make logs          # Logs Ollama en direct
make status        # État de tous les conteneurs
make down          # Arrête tout
make clean-results # Supprime les rapports benchmark
make clean-all     # Supprime tout + volumes (modèles Ollama inclus !)
```

### Windows (sans Make)

```bat
run.bat up
run.bat down
run.bat logs
run.bat reindex
run.bat ask "Combien de visiteurs hier ?"
```

---

## 13. Dépannage (FAQ)

**Le conteneur `django_api` démarre mais le chat répond "Ollama non joignable"**

```bash
docker compose up ollama
docker compose logs ollama
docker compose restart django_api
```

**Le modèle n'est pas encore téléchargé**

```bash
curl http://localhost:11434/api/tags
docker compose exec ollama ollama pull llama3.2:3b-instruct-q4_K_M
```

**Le build de `django_api` prend trop longtemps**

L'image n'installe pas `torch` ni `chromadb` — le build doit prendre ~2 minutes (pandas + numpy + scipy ≈ 60 Mo). Si plus long, vérifiez la connexion internet.

**Modifier le CSV de données**

Remplacer `backend/data/shoppingclub_2025_2026.csv` par votre fichier (même format). Cache invalidé automatiquement.

**Ajouter des documents à la base de connaissance**

Éditer `backend/dataset/knowledge_base.json` (format `{ "id", "title", "content" }`). Embeddings recalculés automatiquement au prochain démarrage de `django_api` (et via `make reindex` pour l'agent).

**Tester l'API sans le frontend**

```bash
open http://localhost:8000/api/docs/

curl http://localhost:8000/api/history/visitors/count/?date=2026-05-30
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"question": "Historique des 7 derniers jours"}'
```

**Sur Windows sans GPU NVIDIA**

Retirer le bloc `deploy > resources` dans `docker-compose.yml` pour fonctionner en CPU (performances dégradées).

---

*Anavid Store 360 — Sprint 0/1 · Juin 2026*