# ShopAnalytics — Backend

**Projet :** Anavid Store 360 — Module Analytics & RAG  
**Stack :** Django 5 · Django REST Framework · Ollama · Python 3.11 · Docker

---

## 1. Vue d'ensemble

Le backend ShopAnalytics fournit :
- une **API REST** exposant les métriques visiteurs (comptage, flux horaire, prévisions, historique)
- un **endpoint de chat RAG** en langage naturel, alimenté par un LLM local via Ollama
- un **pipeline de benchmarking** one-shot pour sélectionner le meilleur modèle LLM selon la VRAM disponible

Tout tourne en local dans Docker — aucune donnée n'est envoyée vers un service cloud externe, conformément aux exigences de confidentialité d'Anavid Store 360.

---

## 2. Structure du projet

```
backend/
├── django_api/                          # ✅ Serveur API REST (production)
│   ├── config/
│   │   ├── settings.py                  # Paramètres Django (DB, CORS, apps)
│   │   ├── urls.py                      # Routage racine + Swagger/ReDoc
│   │   └── wsgi.py / asgi.py
│   ├── history/
│   │   ├── views.py                     # Endpoints GET analytics visiteurs
│   │   ├── chat_view.py                 # Endpoint POST /api/chat/ (RAG)
│   │   ├── rag_pipeline.py              # Pipeline RAG (contexte CSV + KB + Ollama)
│   │   ├── visitor_data.py              # Chargement CSV + cache mtime
│   │   └── urls.py                      # Routage de l'app history
│   ├── manage.py
│   ├── requirements.txt                 # Sans torch/chromadb (image légère ~200 Mo)
│   └── Dockerfile
├── scripts/                             # ✅ Benchmarking one-shot
│   ├── config.py                        # VRAM, modèles candidats, seuils
│   ├── pull_models.py                   # Filtrage VRAM + pull Ollama
│   └── benchmark.py                     # TTFT · throughput · JSON% · anti-hallucination
├── data/                                # ✅ Données opérationnelles (volume Docker)
│   ├── shoppingclub_2025_2026.csv       # Historique visiteurs 349 jours (~2,7 Mo)
│   └── SA-data.xlsx                     # Données de référence complémentaires
├── dataset/                             # ✅ Données applicatives fixes (versionnées)
│   ├── knowledge_base.json              # 8 documents FAQ/métier (base RAG)
│   └── tool_calling_queries.json        # Jeu de test benchmark (50 requêtes FR/AR)
├── results/                             # ✅ Artefacts benchmark (générés)
│   ├── eligible_models.json             # Modèles retenus → consommé par rag_pipeline
│   ├── benchmark_report.json            # Rapport comparatif complet
│   └── result_*.json                    # Détail par modèle
├── Dockerfile                           # Image agent standalone (déprécié)
└── requirements.txt                     # Dépendances agent standalone (déprécié)
```

---

## 3. Architecture de production

```
[Frontend Ionic]
      │  HTTP GET/POST
      ▼
[django_api :8000]
      │
      ├─ GET /api/history/*  →  history/visitor_data.py  →  data/*.csv
      │
      └─ POST /api/chat/     →  history/rag_pipeline.py
                                    │
                                    ├─ contexte CSV (métriques du jour)
                                    ├─ similarité cosinus sur knowledge_base.json
                                    └─ HTTP  →  [Ollama :11434]
                                                llama3.2:3b-instruct-q4_K_M
```

**Points clés :**
- `django_api` ne dépend **pas** de ChromaDB ni de sentence-transformers — les embeddings sont délégués à Ollama via HTTP (modèle déjà chargé en mémoire)
- Le CSV est chargé une fois en mémoire avec invalidation par `mtime` — pas de rechargement inutile
- Le modèle actif est lu depuis `results/eligible_models.json` (produit par `scripts/benchmark.py`)

---

## 4. Endpoints API

Base URL : `http://localhost:8000/api/`

| Méthode | URL | Description |
|---|---|---|
| `GET` | `/api/history/visitors/` | Historique journalier (genre/âge) |
| `GET` | `/api/history/visitors/count/` | Comptage pour une date |
| `GET` | `/api/history/visitors/hourly/` | Flux horaire + heure de pointe |
| `GET` | `/api/history/visitors/forecast/` | Prévision J+1 (régression linéaire) |
| `GET` | `/api/history/summary/` | KPIs globaux |
| `GET` | `/api/history/cameras/` | Liste des caméras |
| `POST` | `/api/chat/` | Chat RAG en langage naturel |
| `GET` | `/api/docs/` | Swagger UI |
| `GET` | `/api/redoc/` | ReDoc |

**Paramètres communs :** `date` (YYYY-MM-DD) · `start_date` · `end_date` · `camera` (Porte_nord / Porte_sud)

---

## 5. Prérequis

- Docker Desktop avec GPU passthrough NVIDIA activé
- Driver NVIDIA + `nvidia-container-toolkit` (Linux) ou WSL 2 (Windows)
- `make` (Linux/macOS) ou `run.bat` (Windows)

> La seule valeur à ajuster avant le premier lancement est `VRAM_AVAILABLE_GB` dans `scripts/config.py`.

---

## 6. Lancement rapide

### Linux / macOS

```bash
# Démarrer la stack complète
make up

# Ou étape par étape
make ollama          # Démarre Ollama
make bench           # Sélectionne le modèle (one-shot)
make api             # Démarre django_api
```

### Windows

```bat
run.bat up
```

---

## 7. Commandes disponibles

| Commande | Action |
|---|---|
| `make up` | Démarre Ollama + benchmark + django_api |
| `make ollama` | Démarre uniquement Ollama |
| `make bench` | Lance `pull_models.py` + `benchmark.py` |
| `make api` | Démarre django_api uniquement |
| `make logs` | Logs Ollama en temps réel |
| `make down` | Arrête tous les containers |
| `make clean-results` | Supprime `results/*.json` |
| `make clean-all` | Supprime containers + volumes ⚠️ efface les modèles |

---

## 8. Configuration du benchmark (`scripts/config.py`)

### VRAM disponible

```python
VRAM_AVAILABLE_GB = 5.5   # Règle : params_b × 0.7 + 2.0 Go (q4_K_M)
```

### Modèles candidats

| Modèle | VRAM req. | Notes |
|---|---|---|
| `qwen2.5:7b-instruct-q4_K_M` | 6.9 Go | Meilleur FR/AR, tool calling solide |
| `mistral:7b-instruct-v0.3-q4_K_M` | 6.9 Go | Rapide, bon JSON |
| `llama3.2:3b-instruct-q4_K_M` | 4.1 Go | Repli sur matériel contraint |

### Seuils de performance

| Métrique | Seuil |
|---|---|
| TTFT | ≤ 1,5 s |
| Throughput | ≥ 10 tok/s (hard min) |
| JSON Tool Calling | ≥ 95 % |
| Anti-hallucination | 100 % (pass/fail) |

---

## 9. Pipeline RAG — `POST /api/chat/`

```
Message utilisateur
      │
      ▼
_build_csv_context()      # KPIs du jour extraits du CSV
      +
_retrieve_kb()            # similarité cosinus sur knowledge_base.json
                          # (embeddings via Ollama /api/embeddings)
      │
      ▼
_build_prompt()           # contexte CSV + docs KB + question
      │
      ▼
_call_ollama()            # génération via Ollama /api/generate
      │
      ▼
{ "response": "..." }
```

**Fallback déterministe** : si Ollama est indisponible ou retourne un JSON malformé, un système de détection par mots-clés (`"prévi"`, `"horaire"`, `"visiteur"`…) sélectionne directement la fonction Python correspondante dans `visitor_data.py`.

---

## 10. Modèle de prévision visiteurs

- **≥ 7 jours d'historique** → régression linéaire (tendance) + ajustement par jour de semaine
- **< 7 jours** → retourne la dernière valeur connue avec `model_status: "non_entraine"` et `confidence: "faible"`

---

## 11. Résultats benchmark

### Exemple de sortie console

```
╭────────────────────────────────────────────────────────╮
│  Modèle                    │ TTFT   │ TPS  │ JSON% │ Score │
├────────────────────────────┼────────┼──────┼───────┼───────┤
│ Qwen 2.5 7B (q4_K_M)       │ 1.2s ✓ │ 22 ✓ │ 98% ✓ │ 90/100│
│ Mistral 7B v0.3 (q4_K_M)   │ 0.6s ✓ │ 35 ✓ │ 92% ✗ │ 72/100│
│ Llama 3.2 3B (q4_K_M)      │ 0.4s ✓ │ 48 ✓ │ 85% ✗ │ 65/100│
╰────────────────────────────────────────────────────────╯
🏆 Modèle retenu : Llama 3.2 3B (config 5,5 Go VRAM)
```

### Scoring

| Critère | Poids |
|---|---|
| TTFT | 25 pts |
| Throughput | 25 pts |
| JSON Tool Calling | 35 pts |
| Anti-hallucination | 15 pts |

---

## 12. Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://ollama:11434` | URL du service Ollama |
| `OLLAMA_MODEL` | `llama3.2:3b-instruct-q4_K_M` | Modèle LLM actif |
| `VISITOR_DATA_CSV` | `/app/data/shoppingclub_2025_2026.csv` | Chemin CSV visiteurs |
| `DJANGO_ALLOWED_HOSTS` | `*` | Hosts autorisés |

---

## 13. Notes

- Sur GPU ≤ 6 Go, seul Llama 3.2 3B passe le filtre VRAM — ajuster `VRAM_AVAILABLE_GB` en conséquence.
- `app/` et `vector_db/` sont des artefacts du prototype Sprint 1 — ils peuvent être supprimés sans impact sur la production (voir `app/README.md`).
- Sur Windows sans GPU NVIDIA, retirer le bloc `deploy > resources` du `docker-compose.yml` pour fonctionner en CPU.