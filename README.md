# ShopAnalytics — LLM Benchmark Stack
**Projet :** Anavid Store 360 — Module Analytics & Préférences  
**Sprint 0 — Cadrage & Sélection du modèle LLM**

## Structure

```
shopanalytics-llm-bench/
├── docker-compose.yml          # Ollama + benchmark runner
├── Makefile                    # Commandes rapides
├── scripts/
│   ├── config.py               # ⚙️  Paramètres à adapter (VRAM, seuils...)
│   ├── pull_models.py          # Pull des modèles avec filtrage VRAM
│   └── benchmark.py            # Mesures TTFT, throughput, JSON, anti-halluc.
├── dataset/
│   └── tool_calling_queries.json   # 50 requêtes métier ShopAnalytics
└── results/                    # Rapports JSON générés automatiquement
```

## Lancement rapide

```bash
# 1 — Adapter la VRAM disponible dans config.py
#     VRAM_AVAILABLE_GB = <ta valeur>

# 2 — Lancer tout d'un coup
make up

# Ou étape par étape :
make ollama        # Démarre Ollama en background
make bench         # Lance pull + benchmark
```

## Adapter à ton serveur

### Changer la VRAM disponible
Dans `scripts/config.py` :
```python
VRAM_AVAILABLE_GB = 12.0  # Ex: RTX 3080 12 Go
```

### Ajouter / modifier des modèles candidats
```python
CANDIDATE_MODELS = [
    {
        "id": "qwen2.5:14b-instruct-q4_K_M",   # nom exact Ollama
        "label": "Qwen 2.5 14B (q4_K_M)",
        "params_b": 14,
        "notes": "...",
    },
    # ...
]
```

### Modifier les seuils de performance
```python
THRESHOLDS = {
    "ttft_max_sec": 1.5,       # Temps jusqu'au 1er token (s)
    "throughput_min_tps": 20,  # tokens/s idéal
    "throughput_hard_min": 10, # tokens/s minimum
    "json_success_min_pct": 95 # % JSON valides requis
}
```

## Tests effectués

| Test | Description | Seuil |
|------|-------------|-------|
| TTFT | Temps jusqu'au premier token | < 1.5s |
| Throughput | Vitesse de génération | > 20 t/s |
| JSON Tool Calling | 50 requêtes métier → JSON valide | > 95% |
| Anti-Hallucination | Fidélité au contexte fourni | 100% |
| Latency Penalty | Dégradation contexte court vs long | info |

## Sortie attendue

```
╭──────────────────────────────────────────────────────╮
│  Modèle             │ TTFT  │ TPS  │ JSON% │ Score  │
├─────────────────────┼───────┼──────┼───────┼────────┤
│ Qwen 2.5 14B        │ 1.2s✓ │ 22✓  │ 98%✓  │ 90/100 │
│ Mistral 7B v0.3     │ 0.6s✓ │ 35✓  │ 92%✗  │ 72/100 │
│ Llama 3 8B          │ 0.7s✓ │ 30✓  │ 88%✗  │ 67/100 │
╰──────────────────────────────────────────────────────╯

🏆 Meilleur modèle : Qwen 2.5 14B (score 90/100)
```

## Notes

- Les modèles sont téléchargés une seule fois (volume Docker persistant).
- `N_WARMUP = 1` et `N_RUNS = 3` dans `config.py` pour ajuster la précision.
- Le dataset de 50 requêtes couvre FR + AR (RTL) et tous les cas d'usage ShopAnalytics.
- Le rapport JSON complet est dans `results/benchmark_report.json`.
