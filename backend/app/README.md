# `app/` — Agent RAG Python (mode standalone)

Ce dossier contient le **cœur analytique de ShopAnalytics** : un agent conversationnel RAG (Retrieval-Augmented Generation) qui tourne en mode Python pur, indépendamment du serveur Django. Il est utilisé pour les tests locaux, les scripts de développement, et constitue le prototype de référence dont s'inspire `django_api/history/`.

---

## Architecture interne

```
app/
├── visitor_data.py      # Chargement & traitement des données CSV
├── visitor_agent.py     # Agent LLM : tool calling + fallback RAG
└── vector_store.py      # Base vectorielle ChromaDB (KB sémantique)
```

---

## Fichiers

### `visitor_data.py` — Couche données

Charge et normalise `data/shoppingclub_2025_2026.csv` (349 jours, ~2,7 Mo) et expose quatre fonctions analytiques appelées par l'agent :

| Fonction | Description |
|---|---|
| `load_data()` | Charge le CSV, normalise les colonnes (`camera`, `gender`, `age`, `datetime`), retourne deux DataFrames : `per_day` et `per_hour` |
| `get_visitor_count(date, camera)` | Nombre de visiteurs pour une date/caméra avec ventilation genre × âge |
| `get_hourly_visitor_flow(date, camera)` | Flux horaire (passages/heure) + heure de pointe |
| `forecast_visitors(target_date, camera)` | Prévision J+1 par régression linéaire pondérée + ajustement jour de semaine |
| `get_visitor_history(start_date, end_date, camera, n_days)` | Série temporelle sur une plage de dates |

**Normalisation intégrée :**
- Caméras : `"Cam porte1"` / `"cam_porte1"` → `"Porte_nord"` ; `"Cam_porte2"` → `"Porte_sud"`
- Genre : `"MEN"` / `"Male"` → `"men"` ; `"WOMEN"` / `"Female"` → `"women"`
- Âge : `"18-29"` / `"age_18-29"` → `"age_18_29"` (format uniforme)
- Dates : parsing `dayfirst=True` (format `DD/MM/YYYY HH:MM:SS`)

---

### `visitor_agent.py` — Agent LLM (tool calling)

Pipeline RAG complet en deux étapes :

**Étape 1 — Routage par le LLM (tool calling)**

Le LLM (Ollama, modèle `llama3.2:3b-instruct-q4_K_M` par défaut) reçoit le message utilisateur et répond **uniquement en JSON** avec la structure :
```json
{ "tool": "get_visitor_count", "parameters": { "date": "2026-05-15", "camera": null } }
```

Cinq outils sont exposés :
- `get_visitor_count` — comptage journalier
- `get_hourly_visitor_flow` — flux horaire
- `forecast_visitors` — prévision
- `get_visitor_history` — historique multi-jours
- `search_knowledge_base` — questions générales (FAQ, définitions)

**Étape 2 — Exécution sur les données réelles**

Le `tool_name` est résolu vers la fonction Python correspondante dans `visitor_data.py` ou `vector_store.py`, et le résultat est retourné directement.

**Fallback par mots-clés** : si le LLM échoue à produire un JSON valide (Ollama indisponible ou réponse malformée), un système de détection par mots-clés (`"prévi"`, `"horaire"`, `"visiteur"`…) sélectionne l'outil le plus probable.

**Sélection du modèle** : le modèle actif est lu depuis `results/eligible_models.json` (produit par `scripts/benchmark.py`). Cela permet de changer de modèle sans modifier le code.

---

### `vector_store.py` — Base vectorielle sémantique (ChromaDB)

Indexe `dataset/knowledge_base.json` (8 documents FAQ/métier) dans une base **ChromaDB persistante** stockée dans `vector_db/`.

- **Embeddings** : `sentence-transformers/all-MiniLM-L6-v2` (CPU-friendly, ~80 Mo, multilingue FR/EN/AR)
- **Persistance** : `vector_db/chroma.sqlite3` (monté en volume Docker)
- **Rôle** : fallback sémantique pour les questions ouvertes ne correspondant à aucun tool structuré (ex : _"Qu'est-ce que le taux de conversion ?"_, _"Quels sont les horaires du magasin ?"_)
- **Auto-reindex** : si la collection est vide au premier appel, `reindex()` est appelé automatiquement

> **Note** : dans le conteneur `django_api`, ChromaDB et sentence-transformers ne sont **pas** installés (trop lourds). Les embeddings y sont délégués directement à Ollama via `/api/embeddings`. Ce module `vector_store.py` est donc propre à l'agent standalone `app/`.

---

## Utilisation en ligne de commande

```bash
# Poser une question à l'agent
python app/visitor_agent.py "Combien de visiteurs hier ?"
python app/visitor_agent.py "Quel est le flux horaire aujourd'hui ?"
python app/visitor_agent.py "Prévois le nombre de visiteurs pour demain"

# Reconstruire l'index vectoriel
python app/vector_store.py --reindex

# Tester une recherche sémantique
python app/vector_store.py "définition du panier moyen"
```

---

## Dépendances

```
pandas, numpy, openpyxl     # traitement données
requests                     # appels Ollama HTTP
chromadb                     # base vectorielle
sentence-transformers        # embeddings (all-MiniLM-L6-v2)
```

> Variables d'environnement : `OLLAMA_HOST` (défaut : `http://localhost:11434`)