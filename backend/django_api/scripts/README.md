# `scripts/` — Outils de benchmarking et sélection de modèle

Ce dossier contient les **scripts d'ingénierie** utilisés pour sélectionner, tester et configurer le modèle LLM embarqué dans ShopAnalytics. Ces scripts s'exécutent dans le conteneur `backend` (accès direct à Ollama) et produisent les fichiers JSON consommés par l'agent.

---

## Fichiers

### `config.py` — Configuration centrale du benchmark

Centralise tous les paramètres du pipeline de sélection de modèle. Importé par `benchmark.py` et `pull_models.py`.

**Paramètres clés :**

| Section | Paramètres |
|---|---|
| **Modèles candidats** | `qwen2.5:7b-instruct-q4_K_M`, `mistral:7b-instruct-v0.3-q4_K_M`, `llama3.2:3b-instruct-q4_K_M` |
| **Seuils de performance** | TTFT ≤ 1,5 s · Throughput ≥ 10 tok/s · JSON valide ≥ 95 % |
| **Contrainte matérielle** | `VRAM_AVAILABLE_GB = 5.5` (règle : `params_b × 0.7 + 2 Go`) |
| **Paramètres d'inférence** | `temperature=0.1`, `top_p=0.9`, `num_ctx=4096`, `num_predict=1024` |
| **Protocole** | 1 warmup ignoré + 3 runs mesurés par requête |

> `num_predict=1024` (vs 256/512 initialement) : ajustement nécessaire après que les réponses JSON complexes (4 paramètres, tableaux imbriqués) étaient tronquées à 512 tokens.

---

### `pull_models.py` — Téléchargement des modèles Ollama

Parcourt `CANDIDATE_MODELS` dans `config.py`, filtre les modèles compatibles avec la VRAM disponible, et lance `ollama pull` pour chaque modèle éligible.

```bash
# Exécution (dans le conteneur backend ou sur l'hôte avec Ollama installé)
python scripts/pull_models.py
```

Pré-requis : Ollama doit être démarré et `OLLAMA_HOST` correctement défini.

---

### `benchmark.py` — Évaluation comparative des modèles LLM

Script principal de benchmarking. Teste chaque modèle candidat sur l'ensemble des requêtes de `dataset/tool_calling_queries.json` et mesure 4 métriques :

| Métrique | Description | Seuil |
|---|---|---|
| **TTFT** | Time To First Token — latence avant le premier token (s) | ≤ 1,5 s |
| **Throughput** | Tokens générés par seconde | ≥ 10 tok/s (hard min) |
| **JSON success rate** | % de réponses JSON valides (tool calling bien formé) | ≥ 95 % |
| **Anti-hallucination** | Vérification que l'outil sélectionné correspond à l'attendu | — |

**Protocole d'un run :**
1. Warmup (1 requête ignorée) pour préchauffer le cache JIT/KV d'Ollama
2. 3 runs mesurés (moyennés pour réduire la variance)
3. Validation JSON : `json.loads()` + vérification de la clé `"tool"`
4. Filtrage final : seuls les modèles passant **tous** les seuils sont écrits dans `eligible_models.json`

**Sorties :**
- `results/benchmark_report.json` — rapport complet (toutes métriques, tous modèles)
- `results/eligible_models.json` — liste ordonnée des modèles retenus (consommée par `visitor_agent.py`)

```bash
python scripts/benchmark.py
```

**Résultat sur la config testée (5,5 Go VRAM) :**
Le seul modèle retenu est `llama3.2:3b-instruct-q4_K_M` — les modèles 7B dépassent la contrainte VRAM disponible.

---

## Flux de travail complet

```
pull_models.py          # 1. Télécharger les modèles éligibles
    ↓
benchmark.py            # 2. Évaluer et sélectionner le meilleur
    ↓
results/eligible_models.json   # 3. Résultat consommé par visitor_agent.py
```

Ce flux est à relancer lors de chaque changement de serveur cible ou après mise à jour des seuils dans `config.py`.