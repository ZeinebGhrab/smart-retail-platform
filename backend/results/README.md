# `results/` — Rapports de benchmark et sélection de modèle

Ce dossier contient les **artefacts produits par `scripts/benchmark.py`**. Ces fichiers JSON sont générés automatiquement et ne doivent pas être modifiés à la main. Ils sont versionnés dans Git pour tracer l'historique des évaluations de modèles.

---

## Fichiers

### `benchmark_report.json`

Rapport complet de la dernière exécution du benchmark. Documente les performances mesurées pour chaque modèle candidat sur l'ensemble du jeu de test `dataset/tool_calling_queries.json`.

**Structure :**
```json
{
  "generated_at": "2026-06-11T...",
  "thresholds": { "ttft_max_sec": 1.5, "throughput_min_tps": 10.0, ... },
  "models": [
    {
      "id": "llama3.2:3b-instruct-q4_K_M",
      "ttft_avg_sec": ...,
      "throughput_avg_tps": ...,
      "json_success_pct": ...,
      "eligible": true
    },
    ...
  ]
}
```

---

### `eligible_models.json`

Liste filtrée des modèles **ayant passé tous les seuils** de performance (TTFT, throughput, JSON success rate) et compatibles avec la VRAM disponible. Ordonné du plus performant au moins performant.

**Fichier actuel :**
```json
[
  {
    "id": "llama3.2:3b-instruct-q4_K_M",
    "label": "Llama 3.2 3B (q4_K_M)",
    "params_b": 3,
    "notes": "Très léger, baseline de vitesse"
  }
]
```

**Consommé par :** `app/visitor_agent.py` via la fonction `get_active_model()` — le premier élément de la liste est utilisé comme modèle actif. Si le fichier est vide ou absent, l'agent tombe en repli sur `llama3.2:3b-instruct-q4_K_M`.

---

### `result_llama3.2_3b-instruct-q4_K_M.json`

Rapport détaillé pour le modèle `llama3.2:3b-instruct-q4_K_M` — résultats requête par requête (outil attendu vs. outil retourné, latences, tokens générés).

---

## Notes

- Ces fichiers sont produits sur la **config matérielle testée** (5,5 Go VRAM). Sur un serveur plus puissant, relancer `scripts/benchmark.py` après avoir mis à jour `VRAM_AVAILABLE_GB` dans `scripts/config.py`.
- En production, ce dossier peut être monté en volume pour permettre la mise à jour du modèle sans rebuild de l'image Docker.