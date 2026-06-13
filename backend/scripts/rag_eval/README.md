# Évaluation RAG — Anavid Store 360

Module d'évaluation du pipeline RAG (`history/rag_pipeline.py`) sur deux niveaux :
le **Retriever** (documents récupérés) et la **Génération** (réponse du LLM).

## Architecture du pipeline Anavid

```
Question utilisateur
       │
       ├──► _build_csv_context()   → données visiteurs (CSV) ──┐
       │                                                         ├──► _build_prompt() ──► Ollama (Llama 3.2)
       └──► _retrieve_kb()         → knowledge_base.json ───────┘
                (embeddings Ollama, cosine similarity)
```

Le Retriever a **deux sources** :
- **CSV** : données visiteurs structurées (`shoppingclub_2025_2026.csv`)
- **KB**  : 8 documents FAQ (`knowledge_base.json`), retrieval sémantique avec `n_results=2`

---

## Métriques implémentées

### 1. Retriever (`metrics_retriever.py`)

| Métrique | Formule | Adapté à Anavid |
|---|---|---|
| **Precision@K** | docs pertinents récupérés / K | K=2 (n_results du pipeline) |
| **Recall@K** | docs pertinents récupérés / docs pertinents existants | Sur les 8 docs KB |
| **MRR** | 1 / rang du premier doc pertinent | Position dans le ranking cosine |
| **nDCG@K** | DCG / IDCG, pondéré par position | Qualité du classement sémantique |
| **Context Precision** | passages KB utiles dans la réponse / total récupérés | Réduit le bruit envoyé au LLM |
| **Context Recall** | couverture des infos nécessaires par le contexte | CSV + KB couvrent la ground truth ? |

### 2. Génération (`metrics_generation.py`)

| Métrique | Usage dans Anavid |
|---|---|
| **Exact Match** | Rarement 1.0 (réponses libres en français) — indicatif |
| **F1 Score** | Chevauchement tokens prédit/attendu — principal indicateur qualité texte |
| **BLEU-2** | N-grammes bigrammes — cohérence locale |
| **ROUGE-L** | Sous-séquence commune — ordre préservé |
| **Faithfulness** | ⭐ Priorité #1 — le LLM n'invente pas de chiffres hors contexte |
| **Answer Relevancy** | La réponse cible bien la question posée |

### 3. Score global (/100)

| Composante | Poids | Seuil recommandé |
|---|---|---|
| Faithfulness | 30 pts | ≥ 0.70 |
| Answer Relevancy | 20 pts | ≥ 0.60 |
| Context Recall | 15 pts | ≥ 0.60 |
| F1 Score | 15 pts | ≥ 0.50 |
| Precision@K | 10 pts | ≥ 0.75 |
| MRR | 10 pts | ≥ 0.75 |

---

## Usage

```bash
# Depuis backend/scripts/
cd backend/scripts

# Mode réel (Ollama doit tourner)
python rag_eval/evaluate_rag.py

# Mode dry-run (sans Ollama — test du module)
python rag_eval/evaluate_rag.py --dry-run

# Verbose (détail par requête)
python rag_eval/evaluate_rag.py --verbose

# Dataset personnalisé
python rag_eval/evaluate_rag.py --dataset /chemin/mon_dataset.json
```

### Via Docker Compose

```bash
# Ajouter au Makefile ou lancer manuellement
docker compose exec django_api python /app/scripts/rag_eval/evaluate_rag.py
```

---

## Structure des fichiers

```
backend/scripts/rag_eval/
├── __init__.py
├── eval_dataset.json          # 12 requêtes avec ground truth
├── metrics_retriever.py       # Precision@K, Recall@K, MRR, nDCG, Context P/R
├── metrics_generation.py      # EM, F1, BLEU, ROUGE-L, Faithfulness, Relevancy
└── evaluate_rag.py            # Runner principal + rapport JSON

backend/results/
└── rag_eval_report.json       # Rapport généré après évaluation
```

---

## Format du dataset d'évaluation

```json
[
  {
    "id": "eval-001",
    "question": "Quels sont les horaires d'ouverture du magasin ?",
    "ground_truth": "Le magasin est ouvert du lundi au samedi de 9h à 20h...",
    "relevant_kb_ids": ["kb-001"],
    "relevant_source": "kb",       // "kb" | "csv" | "both"
    "category": "faq"              // "faq" | "data" | "hybrid"
  }
]
```

---

## Interprétation des résultats

### Faithfulness faible (< 0.70)
Le LLM génère des chiffres ou faits absents du contexte. Actions :
- Renforcer le prompt système : *"Ne génère AUCUN chiffre absent du contexte"*
- Réduire `temperature` (actuellement 0.1 → essayer 0.0)
- Vérifier que `_build_csv_context()` renvoie des données pour la date demandée

### Precision@K faible (< 0.75)
La recherche sémantique KB ramène des documents non pertinents. Actions :
- Augmenter le seuil de similarité cosine dans `_retrieve_kb()`
- Enrichir les titres/contenus KB pour améliorer les embeddings

### Context Recall faible (< 0.60)
Le contexte fourni ne contient pas toutes les infos pour répondre. Actions :
- Augmenter `n_results` de 2 à 3 dans `_retrieve_kb()`
- Enrichir `_build_csv_context()` pour des questions hybrides

### Answer Relevancy faible (< 0.60)
Les réponses sont correctes mais ne ciblent pas la question. Actions :
- Ajouter dans le prompt : *"Réponds directement et précisément à la question"*
- Vérifier les cas `"résumé"` dans `_build_csv_context()` qui génère un contexte global

---

## Évolution : RAGAS en production

Ce module utilise une évaluation **lexicale offline** (sans LLM-as-judge) pour rester
cohérent avec l'architecture Anavid (100% local, Ollama, pas d'API externe).

Pour passer à une évaluation basée sur un LLM-juge (RAGAS) :

```python
# Installer : pip install ragas
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall

result = evaluate(
    dataset=dataset,
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall]
)
```

RAGAS nécessite un LLM juge (OpenAI par défaut, ou Ollama avec adaptation).
