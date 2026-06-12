# ShopAnalytics — LLM Benchmark Stack

**Projet :** Anavid Store 360 — Module Analytics & Préférences  
**Sprint 0 — Cadrage & Sélection du modèle LLM**

---

## 1. Vue d'ensemble

Ce projet automatise la sélection du meilleur modèle LLM local pour ShopAnalytics. Il orchestre Ollama via Docker, filtre les modèles selon la VRAM disponible, puis les évalue sur cinq critères clés : latence au premier token (TTFT), débit (tokens/s), fidélité JSON (tool calling), absence d'hallucinations et dégradation sur contexte long.

---

## 2. Structure du projet

```
shopanalytics-llm-bench/
├── docker-compose.yml                  # Stack Ollama + benchmark runner
├── Makefile                            # Commandes rapides (Linux/Mac)
├── run.bat                             # Commandes rapides (Windows)
├── scripts/
│   ├── config.py                       # Paramètres : VRAM, modèles, seuils, inférence
│   ├── pull_models.py                  # Filtrage VRAM + pull des modèles Ollama
│   └── benchmark.py                    # Mesures TTFT, throughput, JSON, anti-hallucination
├── dataset/
│   └── tool_calling_queries.json       # 50 requêtes métier ShopAnalytics (FR + AR)
└── results/                            # Rapports JSON générés automatiquement
```

---

## 3. Prérequis

- Docker Desktop (avec GPU passthrough activé pour NVIDIA)
- Driver NVIDIA + `nvidia-container-toolkit` (Linux) ou WSL 2 (Windows)
- `git` — pour cloner le dépôt
- `make` (Linux/Mac) ou utiliser `run.bat` (Windows)

> La VRAM disponible est la seule valeur à ajuster avant le premier lancement (voir section 6).

---

## 4. Lancement rapide

### Linux / macOS

```bash
# 1. Adapter la VRAM dans scripts/config.py
#    VRAM_AVAILABLE_GB = <ta valeur>

# 2. Lancer tout d'un coup
make up

# Ou étape par étape :
make ollama   # Démarre Ollama en arrière-plan
make bench    # pull_models.py → benchmark.py
```

### Windows

```bat
run.bat up
```

---

## 5. Commandes disponibles

| Commande | Équivalent Windows | Action |
|----------|--------------------|--------|
| `make up` | `run.bat up` | Démarre Ollama + attend healthcheck + lance le benchmark complet |
| `make ollama` | `run.bat ollama` | Démarre uniquement Ollama en arrière-plan |
| `make bench` | `run.bat bench` | Lance `pull_models.py` + `benchmark.py` (Ollama doit tourner) |
| `make logs` | `run.bat logs` | Affiche les logs Ollama en temps réel |
| `make status` | `run.bat status` | Affiche le statut des containers Docker |
| `make down` | `run.bat down` | Arrête tous les containers |
| `make clean-results` | `run.bat clean` | Supprime les fichiers `results/*.json` |
| `make clean-all` | — | Supprime containers + volumes ⚠️ efface les modèles téléchargés |

---

## 6. Configuration (`scripts/config.py`)

### 6.1 VRAM disponible

Seul paramètre obligatoire à modifier. Règle empirique utilisée :

```
VRAM requise ≈ params_b × 0.7 + 2.0 Go  (quantification q4_K_M)
```

```python
VRAM_AVAILABLE_GB = 5.5   # Ajuster selon le serveur cible
```

### 6.2 Modèles candidats (défaut)

| Modèle | Params | VRAM req. | Notes |
|--------|--------|-----------|-------|
| `qwen2.5:7b-instruct-q4_K_M` | 7 B | 6.9 Go | Meilleur FR/AR, tool calling solide |
| `mistral:7b-instruct-v0.3-q4_K_M` | 7 B | 6.9 Go | Rapide, bon JSON |
| `llama3.2:3b-instruct-q4_K_M` | 3 B | 4.1 Go | Très léger — baseline vitesse |

Pour ajouter ou modifier un modèle :

```python
CANDIDATE_MODELS = [
    {
        "id": "qwen2.5:14b-instruct-q4_K_M",  # nom exact Ollama
        "label": "Qwen 2.5 14B (q4_K_M)",
        "params_b": 14,
        "notes": "...",
    },
]
```

### 6.3 Seuils de performance

```python
THRESHOLDS = {
    "ttft_max_sec": 1.5,          # Temps jusqu'au 1er token (s)
    "throughput_min_tps": 20.0,   # tokens/s idéal
    "throughput_hard_min": 10.0,  # tokens/s minimum absolu
    "json_success_min_pct": 95.0, # % JSON valides requis
}
```

### 6.4 Paramètres d'inférence

```python
INFERENCE_OPTIONS = {
    "temperature": 0.1,   # Faible = plus déterministe (tool calling)
    "top_p": 0.9,
    "num_ctx": 4096,      # Taille du contexte
    "num_predict": 256,   # Tokens max par requête
}

N_WARMUP = 1   # Requêtes ignorées (JIT/cache warmup)
N_RUNS   = 3   # Requêtes mesurées (moyenne)
```

---

## 7. Tests effectués

| Test | Description | Seuil |
|------|-------------|-------|
| **TTFT** | Temps jusqu'au premier token (N_RUNS moyennés) | < 1.5 s |
| **Throughput** | Vitesse de génération (tokens/s) | > 20 t/s (hard min 10) |
| **JSON Tool Calling** | 50 requêtes métier → JSON `{tool, parameters}` valide | > 95 % |
| **Anti-Hallucination** | Fidélité au contexte — 0 vente, 38 °C Sfax | 100 % (pass/fail) |
| **Context Latency Penalty** | Dégradation throughput ctx court vs long (500 SKU) | Informatif |

### Contexte du test anti-hallucination

Le modèle reçoit un contexte vérifié :

- Date : 11 juin 2026 — fermeture pour inventaire → **0 vente, 0 personnel**
- Météo à Sfax : **38 °C, ensoleillé**

Le test passe si le modèle mentionne `0` vente **et** n'invente pas de météo (ex. neige).

---

## 8. Scoring et décision

| Critère | Poids | Condition |
|---------|-------|-----------|
| TTFT | 25 pts | ≤ 1.5 s → 25 pts \| ≤ 3.0 s → 12 pts \| > 3 s → 0 pt |
| Throughput | 25 pts | ≥ 20 t/s → 25 pts \| ≥ 10 t/s → 12 pts \| < 10 → 0 pt |
| JSON Tool Calling | 35 pts | ≥ 95 % → 35 pts \| sinon proportionnel |
| Anti-Hallucination | 15 pts | Réponse fidèle → 15 pts \| invention → 0 pt |
| **Total** | **100 pts** | **✅ RECOMMANDÉ** si TTFT ✓ + hard_min ✓ + JSON ✓ + AH ✓ |

---

## 9. Dataset — 50 requêtes métier

Le fichier `dataset/tool_calling_queries.json` couvre l'intégralité des cas d'usage ShopAnalytics :

- Ventes, CA, top produits, comparaisons temporelles
- Gestion du stock (alertes, ruptures, réassort, SKU)
- Visiteurs, flux horaire, taux de conversion, panier moyen
- Personnel (planning, absentéisme), promotions, incidents
- Requêtes en arabe (RTL) — IDs 21 à 23

Chaque entrée définit `expected_tool` et `expected_keys`, permettant une validation structurelle précise au-delà de la simple validité JSON.

---

## 10. Résultats et rapports

### Exemple de sortie console

```
╭─────────────────────────────────────────────────────────────╮
│  Modèle                    │ TTFT    │ TPS  │ JSON% │ Score │
├────────────────────────────┼─────────┼──────┼───────┼───────┤
│ Qwen 2.5 7B (q4_K_M)       │ 1.2s ✓  │ 22 ✓ │ 98% ✓ │ 90/100│
│ Mistral 7B v0.3 (q4_K_M)   │ 0.6s ✓  │ 35 ✓ │ 92% ✗ │ 72/100│
│ Llama 3.2 3B (q4_K_M)      │ 0.4s ✓  │ 48 ✓ │ 85% ✗ │ 65/100│
╰─────────────────────────────────────────────────────────────╯

🏆 Meilleur modèle : Qwen 2.5 7B (score 90/100)
   → Tous les seuils validés. Déploiement recommandé.
```

### Fichiers générés dans `results/`

| Fichier | Contenu |
|---------|---------|
| `eligible_models.json` | Modèles retenus après filtrage VRAM |
| `result_<model_id>.json` | Rapport détaillé par modèle |
| `benchmark_report.json` | Rapport global comparatif (tous modèles) |

> Les modèles sont téléchargés une seule fois dans le volume Docker `shopanalytics_ollama_models` et réutilisés lors des lancements suivants.

---

## 11. Architecture Docker

### Service `ollama`

- Image : `ollama/ollama:latest`
- Volume persistant : `shopanalytics_ollama_models` → `/root/.ollama`
- `OLLAMA_NUM_PARALLEL=1` et `OLLAMA_MAX_LOADED_MODELS=1` pour des mesures reproductibles
- GPU NVIDIA activé via `nvidia-container-toolkit` (`driver: nvidia, count: all`)
- Healthcheck toutes les 10 s — le service `benchmark` attend `service_healthy`

### Service `benchmark` (one-shot)

- Image : `python:3.11-slim` — `pip install requests colorama tabulate`
- Exécute `pull_models.py` puis `benchmark.py`
- `restart: no` — s'arrête automatiquement à la fin du benchmark
- `OLLAMA_HOST` injecté via variable d'environnement → `http://ollama:11434`

---

## 12. Comparaison des modèles LLM candidats

Le tableau suivant compare les trois modèles évalués par ce benchmark (`scripts/config.py`) selon les critères pertinents pour ShopAnalytics. À titre de référence, une colonne **Cloud (GPT-3.5 / GPT-4)** est ajoutée pour situer le choix « LLM local via Ollama » par rapport à une solution propriétaire.

| Critère | Qwen 2.5 7B (q4_K_M) | Mistral 7B v0.3 (q4_K_M) | Llama 3.2 3B (q4_K_M) | GPT-3.5 / GPT-4 (référence cloud) |
|---|---|---|---|---|
| **Architecture** | Transformer decoder-only, open-source | Transformer decoder-only, open-source | Transformer decoder-only, open-source, léger | Transformer propriétaire (API cloud) |
| **Déploiement** | Local (Ollama / Docker) | Local (Ollama / Docker) | Local (Ollama / Docker) | Cloud API (payant, dépendance externe) |
| **VRAM requise (q4_K_M)** | 6.9 Go | 6.9 Go | 4.1 Go | N/A (calcul délégué au fournisseur) |
| **Latence (TTFT, seuil benchmark)** | Faible — cible < 1.5 s | Très faible — cible < 1.5 s | Très faible — cible < 1.5 s | Variable selon réseau et charge |
| **Throughput (seuil benchmark)** | Cible > 20 t/s | Cible > 20 t/s | Cible > 20 t/s (souvent le plus rapide) | Variable selon réseau |
| **Multilingue (FR / AR / EN)** | Très bon (FR/AR solides) | Bon (FR/EN, AR plus faible) | Correct (FR/EN, AR limité) | Excellent |
| **Confidentialité des données** | Totale (aucune donnée transmise) | Totale (aucune donnée transmise) | Totale (aucune donnée transmise) | Données envoyées vers le cloud |
| **Capacité de raisonnement** | Élevée | Moyenne à élevée | Moyenne | Très élevée |
| **JSON Tool Calling (test dataset)** | Très fiable (cible > 95 %) | Fiable mais moins stable sur AR | Correct, plus d'erreurs de structure | Très fiable |
| **Personnalisation (fine-tuning)** | Facile (Modelfile Ollama / LoRA) | Facile (Modelfile Ollama / LoRA) | Facile (Modelfile Ollama / LoRA) | Non disponible (modèles fermés) |
| **Coût** | Gratuit (matériel local) | Gratuit (matériel local) | Gratuit (matériel local) | Payant à l'usage (par token) |

> *Table : Comparaison des modèles LLM candidats — ShopAnalytics Benchmark (Sprint 0)*

### Recommandation

- **Qwen 2.5 7B** est le candidat privilégié si la VRAM disponible est ≥ 6.9 Go : meilleur compromis FR/AR + tool calling.
- **Mistral 7B v0.3** est une alternative valable pour le débit, au prix d'une fiabilité JSON légèrement inférieure sur les requêtes en arabe.
- **Llama 3.2 3B** reste le choix de repli sur matériel contraint (≤ 5.5 Go de VRAM, comme dans la configuration testée), avec une dégradation attendue sur le score JSON Tool Calling et le raisonnement métier.
- La solution **cloud (GPT-3.5/4)** n'est pas retenue pour ShopAnalytics en raison de l'exigence de **confidentialité totale des données retail** (ventes, personnel, sécurité) imposée par Anavid Store 360.

---

## 13. Notes et conseils

- Sur GPU ≤ 6 Go, seuls Llama 3.2 3B et Qwen 2.5 7B passent le filtre VRAM — ajuster `VRAM_AVAILABLE_GB` en conséquence.
- Augmenter `N_RUNS` (ex. 5 ou 10) pour des mesures plus stables sur du matériel partagé.
- Le test de latency penalty utilise un contexte synthétique de 500 SKU — il est informatif et n'impacte pas le score final.
- Sur Windows sans GPU NVIDIA, retirer le bloc `deploy > resources` du `docker-compose.yml` pour fonctionner en CPU (performances dégradées).
- Le rapport JSON complet est dans `results/benchmark_report.json` — exploitable dans un dashboard ou un pipeline CI/CD.