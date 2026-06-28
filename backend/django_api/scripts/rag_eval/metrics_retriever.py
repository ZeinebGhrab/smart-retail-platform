"""
rag_eval/metrics_retriever.py — Métriques d'évaluation du Retriever
=====================================================================
Métriques implémentées (adaptées à l'architecture Anavid) :
  - Precision@K   : proportion de docs KB pertinents parmi les K récupérés
  - Recall@K      : proportion de docs KB pertinents effectivement retrouvés
  - MRR           : position du premier document pertinent
  - nDCG@K        : qualité du classement avec pondération positionnelle
  - Context Precision : les passages envoyés au LLM sont-ils tous utiles ?
  - Context Recall    : les passages couvrent-ils toutes les infos nécessaires ?

Note architecture :
  Le pipeline Anavid a DEUX sources de retrieval :
    1. CSV  → _build_csv_context() : données visiteurs structurées
    2. KB   → _retrieve_kb()       : knowledge_base.json (8 docs)

  Les métriques Precision/Recall/MRR/nDCG s'appliquent sur la KB.
  Context Precision/Recall s'appliquent sur le contexte total (CSV + KB).
"""

from __future__ import annotations

import math
from typing import Any


# ══════════════════════════════════════════════════════════════
# 1. Precision@K
# ══════════════════════════════════════════════════════════════

def precision_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int) -> float:
    """
    Precision@K = |{docs pertinents} ∩ {top-K récupérés}| / K

    Args:
        retrieved_ids : IDs des documents récupérés, dans l'ordre de ranking.
        relevant_ids  : IDs des documents réellement pertinents (ground truth).
        k             : nombre de documents à considérer.

    Returns:
        Score entre 0.0 et 1.0.

    Exemple (KB Anavid) :
        retrieved_ids = ["kb-001", "kb-004", "kb-002"]
        relevant_ids  = ["kb-001", "kb-004"]
        k = 2
        → Precision@2 = 2/2 = 1.0
    """
    if k <= 0:
        return 0.0
    top_k = retrieved_ids[:k]
    relevant_set = set(relevant_ids)
    hits = sum(1 for doc_id in top_k if doc_id in relevant_set)
    return hits / k


# ══════════════════════════════════════════════════════════════
# 2. Recall@K
# ══════════════════════════════════════════════════════════════

def recall_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int) -> float:
    """
    Recall@K = |{docs pertinents} ∩ {top-K récupérés}| / |docs pertinents|

    Args:
        retrieved_ids : IDs des documents récupérés, dans l'ordre de ranking.
        relevant_ids  : IDs des documents réellement pertinents.
        k             : nombre de documents à considérer.

    Returns:
        Score entre 0.0 et 1.0. Retourne 0.0 si relevant_ids est vide.

    Exemple (KB Anavid, n_results=2) :
        retrieved_ids = ["kb-001", "kb-007"]
        relevant_ids  = ["kb-001", "kb-007", "kb-008"]
        k = 2
        → Recall@2 = 2/3 = 0.667
    """
    if not relevant_ids:
        return 0.0
    top_k = set(retrieved_ids[:k])
    relevant_set = set(relevant_ids)
    hits = len(top_k & relevant_set)
    return hits / len(relevant_set)


# ══════════════════════════════════════════════════════════════
# 3. MRR — Mean Reciprocal Rank
# ══════════════════════════════════════════════════════════════

def reciprocal_rank(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
    """
    Reciprocal Rank = 1 / position_du_premier_doc_pertinent

    Args:
        retrieved_ids : IDs des documents récupérés, dans l'ordre de ranking.
        relevant_ids  : IDs des documents réellement pertinents.

    Returns:
        Score entre 0.0 et 1.0.
        - 1.0  : premier document pertinent en position 1
        - 0.5  : premier document pertinent en position 2
        - 0.0  : aucun document pertinent trouvé

    Exemple (KB Anavid) :
        retrieved_ids = ["kb-003", "kb-001"]   ← kb-001 en position 2
        relevant_ids  = ["kb-001"]
        → RR = 1/2 = 0.5
    """
    relevant_set = set(relevant_ids)
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in relevant_set:
            return 1.0 / rank
    return 0.0


def mean_reciprocal_rank(
    all_retrieved: list[list[str]],
    all_relevant: list[list[str]],
) -> float:
    """
    MRR = moyenne des Reciprocal Ranks sur un ensemble de requêtes.

    Args:
        all_retrieved : liste de listes d'IDs récupérés (une par requête).
        all_relevant  : liste de listes d'IDs pertinents (une par requête).

    Returns:
        Score MRR entre 0.0 et 1.0.
    """
    if not all_retrieved:
        return 0.0
    rr_scores = [
        reciprocal_rank(retrieved, relevant)
        for retrieved, relevant in zip(all_retrieved, all_relevant)
    ]
    return sum(rr_scores) / len(rr_scores)


# ══════════════════════════════════════════════════════════════
# 4. nDCG@K — Normalized Discounted Cumulative Gain
# ══════════════════════════════════════════════════════════════

def ndcg_at_k(
    retrieved_ids: list[str],
    relevant_ids: list[str],
    k: int,
    relevance_scores: dict[str, float] | None = None,
) -> float:
    """
    nDCG@K mesure la qualité du classement : un doc pertinent en tête
    vaut plus qu'un doc pertinent en bas de liste.

    nDCG@K = DCG@K / IDCG@K

    DCG@K  = Σ rel_i / log2(i+1)   pour i de 1 à K
    IDCG@K = DCG@K d'un classement parfait (meilleur score possible)

    Args:
        retrieved_ids    : IDs récupérés dans l'ordre de ranking.
        relevant_ids     : IDs pertinents (ground truth).
        k                : fenêtre de calcul.
        relevance_scores : dict optionnel {id: score} pour pertinence graduée.
                           Si None, binaire (1 si pertinent, 0 sinon).

    Returns:
        Score entre 0.0 et 1.0. Plus proche de 1.0 = meilleur classement.

    Exemple (KB Anavid, k=2) :
        retrieved_ids = ["kb-001", "kb-007"]
        relevant_ids  = ["kb-001", "kb-007"]
        → DCG@2  = 1/log2(2) + 1/log2(3) = 1.0 + 0.631 = 1.631
        → IDCG@2 = même (classement parfait)
        → nDCG@2 = 1.0
    """
    if k <= 0 or not relevant_ids:
        return 0.0

    relevant_set = set(relevant_ids)

    def _rel(doc_id: str) -> float:
        if relevance_scores:
            return relevance_scores.get(doc_id, 0.0)
        return 1.0 if doc_id in relevant_set else 0.0

    # DCG réel
    dcg = sum(
        _rel(doc_id) / math.log2(rank + 1)
        for rank, doc_id in enumerate(retrieved_ids[:k], start=1)
    )

    # IDCG = classement parfait (docs les plus pertinents en premier)
    ideal_rels = sorted(
        [_rel(doc_id) for doc_id in relevant_ids],
        reverse=True,
    )[:k]
    idcg = sum(
        rel / math.log2(rank + 1)
        for rank, rel in enumerate(ideal_rels, start=1)
        if rel > 0
    )

    return dcg / idcg if idcg > 0 else 0.0


# ══════════════════════════════════════════════════════════════
# 5. Context Precision & Context Recall (métriques RAG spécifiques)
# ══════════════════════════════════════════════════════════════

def context_precision(
    retrieved_passages: list[str],
    answer: str,
    question: str,
) -> float:
    """
    Estime si les passages récupérés sont réellement utilisés dans la réponse.

    Implémentation légère (sans LLM-as-judge) :
    Pour chaque passage KB récupéré, on vérifie si ses mots-clés
    apparaissent dans la réponse générée.

    Note : une version production utiliserait un LLM juge (ex: RAGAS).
    Cette version fonctionne offline avec le modèle Ollama du projet.

    Args:
        retrieved_passages : textes des passages KB envoyés au LLM.
        answer             : réponse générée par le LLM.
        question           : question originale de l'utilisateur.

    Returns:
        Score entre 0.0 et 1.0.
    """
    if not retrieved_passages:
        return 1.0  # pas de passage KB → pas de bruit KB possible

    answer_lower = answer.lower()
    useful_count = 0

    for passage in retrieved_passages:
        # Extraire les mots significatifs du passage (>4 chars)
        words = [w.lower() for w in passage.split() if len(w) > 4]
        if not words:
            continue
        # Le passage est "utile" si ≥ 30% de ses mots clés apparaissent dans la réponse
        hits = sum(1 for w in words if w in answer_lower)
        if hits / len(words) >= 0.30:
            useful_count += 1

    return useful_count / len(retrieved_passages)


def context_recall(
    retrieved_passages: list[str],
    ground_truth: str,
) -> float:
    """
    Estime si les passages récupérés contiennent les informations
    nécessaires pour répondre (couverture de la vérité terrain).

    Implémentation légère par chevauchement lexical.
    Une version production utilise un LLM-as-judge.

    Args:
        retrieved_passages : textes des passages récupérés (KB + CSV).
        ground_truth       : réponse attendue (ground truth).

    Returns:
        Score entre 0.0 et 1.0.
    """
    if not ground_truth or not retrieved_passages:
        return 0.0

    # Mots significatifs de la ground truth
    gt_words = set(w.lower() for w in ground_truth.split() if len(w) > 4)
    if not gt_words:
        return 1.0

    # Ensemble des mots dans tous les passages récupérés
    all_retrieved_text = " ".join(retrieved_passages).lower()
    covered = sum(1 for w in gt_words if w in all_retrieved_text)

    return covered / len(gt_words)


# ══════════════════════════════════════════════════════════════
# 6. Agrégation — résumé retriever
# ══════════════════════════════════════════════════════════════

def compute_retriever_metrics(
    retrieved_ids: list[str],
    relevant_ids: list[str],
    retrieved_passages: list[str],
    answer: str,
    ground_truth: str,
    k: int = 2,
) -> dict[str, float]:
    """
    Calcule toutes les métriques retriever pour une requête.

    Args:
        retrieved_ids      : IDs des docs KB récupérés (dans l'ordre).
        relevant_ids       : IDs des docs KB pertinents (ground truth).
        retrieved_passages : textes des passages envoyés au LLM.
        answer             : réponse générée.
        ground_truth       : réponse attendue.
        k                  : fenêtre @K (défaut = 2, car n_results=2 dans le pipeline).

    Returns:
        Dict avec toutes les métriques retriever.
    """
    return {
        f"precision@{k}": round(precision_at_k(retrieved_ids, relevant_ids, k), 4),
        f"recall@{k}":    round(recall_at_k(retrieved_ids, relevant_ids, k), 4),
        "mrr":            round(reciprocal_rank(retrieved_ids, relevant_ids), 4),
        f"ndcg@{k}":      round(ndcg_at_k(retrieved_ids, relevant_ids, k), 4),
        "context_precision": round(context_precision(retrieved_passages, answer, ""), 4),
        "context_recall":    round(context_recall(retrieved_passages, ground_truth), 4),
    }
