"""
rag_eval/metrics_generation.py — Métriques d'évaluation de la Génération
=========================================================================
Métriques implémentées :
  - Exact Match (EM)       : correspondance exacte avec la ground truth
  - F1 Score token         : chevauchement de tokens (QA standard)
  - ROUGE-L                : plus longue sous-séquence commune (résumé)
  - BLEU-1 / BLEU-2        : chevauchement n-grammes
  - Faithfulness           : la réponse est-elle fondée sur le contexte ?
  - Answer Relevancy       : la réponse répond-elle à la question ?

Note sur l'architecture Anavid :
  - Le LLM est Llama 3.2 3B via Ollama (local, pas d'API externe).
  - Faithfulness et Answer Relevancy sont estimés lexicalement (sans
    LLM-as-judge) pour rester cohérents avec l'architecture offline.
  - Une note indique comment upgrader vers RAGAS si besoin.
"""

from __future__ import annotations

import re
import math
from collections import Counter


# ══════════════════════════════════════════════════════════════
# Utilitaires texte
# ══════════════════════════════════════════════════════════════

def _normalize(text: str) -> str:
    """Normalise un texte : minuscules, sans ponctuation, espaces normalisés."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokenize(text: str) -> list[str]:
    """Tokenise un texte normalisé en liste de mots."""
    return _normalize(text).split()


def _ngrams(tokens: list[str], n: int) -> Counter:
    """Génère un Counter de n-grammes à partir d'une liste de tokens."""
    return Counter(tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1))


# ══════════════════════════════════════════════════════════════
# 1. Exact Match
# ══════════════════════════════════════════════════════════════

def exact_match(prediction: str, ground_truth: str) -> float:
    """
    Exact Match = 1 si la réponse correspond exactement à la vérité terrain
    (après normalisation), 0 sinon.

    Args:
        prediction   : réponse générée par le LLM.
        ground_truth : réponse attendue.

    Returns:
        1.0 ou 0.0.

    Exemple :
        prediction   = "  Le magasin ouvre à 9h. "
        ground_truth = "le magasin ouvre à 9h"
        → EM = 1.0
    """
    return 1.0 if _normalize(prediction) == _normalize(ground_truth) else 0.0


# ══════════════════════════════════════════════════════════════
# 2. F1 Score (token overlap)
# ══════════════════════════════════════════════════════════════

def f1_score(prediction: str, ground_truth: str) -> float:
    """
    F1 Score basé sur le chevauchement de tokens (standard SQuAD).

    F1 = 2 × (Precision × Recall) / (Precision + Recall)

    Précision  = tokens communs / tokens dans la prédiction
    Recall     = tokens communs / tokens dans la ground truth

    Args:
        prediction   : réponse générée.
        ground_truth : réponse attendue.

    Returns:
        Score F1 entre 0.0 et 1.0.

    Exemple :
        prediction   = "Le magasin est ouvert de 9h à 20h en semaine"
        ground_truth = "Le magasin ouvre du lundi au samedi de 9h à 20h"
        → F1 ≈ 0.57 (tokens en commun : le, magasin, de, 9h, à, 20h)
    """
    pred_tokens = _tokenize(prediction)
    gt_tokens   = _tokenize(ground_truth)

    if not pred_tokens or not gt_tokens:
        return 0.0

    pred_counter = Counter(pred_tokens)
    gt_counter   = Counter(gt_tokens)

    common = sum((pred_counter & gt_counter).values())

    if common == 0:
        return 0.0

    precision = common / len(pred_tokens)
    recall    = common / len(gt_tokens)

    return 2 * precision * recall / (precision + recall)


# ══════════════════════════════════════════════════════════════
# 3. ROUGE-L
# ══════════════════════════════════════════════════════════════

def _lcs_length(a: list[str], b: list[str]) -> int:
    """Longueur de la plus longue sous-séquence commune (LCS)."""
    m, n = len(a), len(b)
    # Optimisation mémoire : seulement 2 lignes
    prev = [0] * (n + 1)
    for i in range(1, m + 1):
        curr = [0] * (n + 1)
        for j in range(1, n + 1):
            if a[i-1] == b[j-1]:
                curr[j] = prev[j-1] + 1
            else:
                curr[j] = max(curr[j-1], prev[j])
        prev = curr
    return prev[n]


def rouge_l(prediction: str, ground_truth: str) -> dict[str, float]:
    """
    ROUGE-L : mesure basée sur la plus longue sous-séquence commune (LCS).
    Préserve l'ordre des mots contrairement à ROUGE-N.

    Utilisé pour évaluer la qualité des résumés et réponses longues.

    Args:
        prediction   : réponse générée.
        ground_truth : réponse attendue.

    Returns:
        Dict avec precision, recall et F1 ROUGE-L.

    Exemple :
        prediction   = "Le magasin ouvre à 9h du matin"
        ground_truth = "Le magasin est ouvert de 9h à 20h"
        → LCS = ["le", "magasin", "9h"] (longueur 3 en ordre)
        → ROUGE-L F1 ≈ 0.46
    """
    pred_tokens = _tokenize(prediction)
    gt_tokens   = _tokenize(ground_truth)

    if not pred_tokens or not gt_tokens:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    lcs = _lcs_length(pred_tokens, gt_tokens)

    precision = lcs / len(pred_tokens)
    recall    = lcs / len(gt_tokens)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall":    round(recall, 4),
        "f1":        round(f1, 4),
    }


# ══════════════════════════════════════════════════════════════
# 4. BLEU
# ══════════════════════════════════════════════════════════════

def bleu(prediction: str, ground_truth: str, max_n: int = 2) -> float:
    """
    BLEU (Bilingual Evaluation Understudy) — chevauchement de n-grammes.
    Implémentation simplifiée (corpus = 1 phrase) avec brevity penalty.

    Args:
        prediction   : réponse générée.
        ground_truth : réponse de référence.
        max_n        : n-grammes max à considérer (défaut 2 pour BLEU-2).

    Returns:
        Score BLEU entre 0.0 et 1.0.

    Note : BLEU a des limitations sur des phrases courtes (variance élevée).
    Préférer F1 et ROUGE-L pour ce projet retail (réponses courtes en FR).
    """
    pred_tokens = _tokenize(prediction)
    gt_tokens   = _tokenize(ground_truth)

    if not pred_tokens or not gt_tokens:
        return 0.0

    # Brevity penalty
    bp = math.exp(1 - len(gt_tokens) / len(pred_tokens)) if len(pred_tokens) < len(gt_tokens) else 1.0

    # Précision pour chaque n
    precisions = []
    for n in range(1, max_n + 1):
        pred_ngrams = _ngrams(pred_tokens, n)
        gt_ngrams   = _ngrams(gt_tokens, n)

        if not pred_ngrams:
            precisions.append(0.0)
            continue

        clipped = sum((pred_ngrams & gt_ngrams).values())
        total   = sum(pred_ngrams.values())
        precisions.append(clipped / total if total > 0 else 0.0)

    # Moyenne géométrique des précisions (avec log pour éviter overflow)
    if any(p == 0 for p in precisions):
        return 0.0

    log_avg = sum(math.log(p) for p in precisions) / len(precisions)
    return round(bp * math.exp(log_avg), 4)


# ══════════════════════════════════════════════════════════════
# 5. Faithfulness (fidélité au contexte)
# ══════════════════════════════════════════════════════════════

def faithfulness(
    answer: str,
    context_passages: list[str],
) -> float:
    """
    Estime dans quelle mesure la réponse est fondée sur le contexte fourni.

    Détecte les hallucinations : chiffres ou faits dans la réponse qui
    ne sont pas présents dans le contexte.

    Implémentation :
      - Extraction des entités numériques et des mots-clés de la réponse
      - Vérification de leur présence dans le contexte
      - Score = proportion de faits vérifiables trouvés dans le contexte

    Note architecture Anavid :
      Le prompt système dit : "Utilise UNIQUEMENT les données du CONTEXTE".
      Cette métrique vérifie que le LLM respecte cette consigne.

    Args:
        answer           : réponse générée par le LLM.
        context_passages : liste des passages fournis au LLM (CSV + KB).

    Returns:
        Score entre 0.0 et 1.0. 1.0 = totalement fidèle, 0.0 = hallucination totale.
    """
    if not answer or not context_passages:
        return 0.0

    context_text = " ".join(context_passages).lower()
    answer_lower = answer.lower()

    # Extraction des nombres dans la réponse (indicateurs de faits chiffrés)
    numbers_in_answer = re.findall(r'\b\d+(?:[.,]\d+)?\b', answer_lower)

    # Extraction des mots-clés substantiels (>5 chars, pas stopwords FR)
    stopwords_fr = {
        "dans", "avec", "pour", "cette", "voici", "selon", "comme",
        "entre", "leurs", "elles", "aussi", "mais", "donc", "ainsi",
        "quand", "dont", "vers", "avant", "après", "depuis", "pendant"
    }
    keywords = [
        w for w in re.findall(r'\b[a-zàâéèêëîïôùûüÿ]{5,}\b', answer_lower)
        if w not in stopwords_fr
    ]

    # Vérification des nombres dans le contexte
    faithful_numbers = sum(1 for n in numbers_in_answer if n in context_text)

    # Vérification des mots-clés dans le contexte
    faithful_keywords = sum(1 for w in keywords if w in context_text)

    total_claims = len(numbers_in_answer) + len(keywords)
    total_faithful = faithful_numbers + faithful_keywords

    if total_claims == 0:
        return 1.0  # Réponse vide ou sans assertions vérifiables

    return round(total_faithful / total_claims, 4)


# ══════════════════════════════════════════════════════════════
# 6. Answer Relevancy
# ══════════════════════════════════════════════════════════════

def answer_relevancy(
    answer: str,
    question: str,
) -> float:
    """
    Estime si la réponse répond réellement à la question posée.

    Implémentation par chevauchement lexical question→réponse.
    Les mots-clés de la question doivent apparaître dans la réponse.

    Note : une version production utilise un LLM-as-judge ou des embeddings.
    Cette version offline est cohérente avec l'architecture Anavid.

    Args:
        answer   : réponse générée par le LLM.
        question : question originale de l'utilisateur.

    Returns:
        Score entre 0.0 et 1.0.

    Exemple :
        question = "Quel produit est le plus vendu ?"
        answer   = "Voici les ventes du mois de mars."
        → Les mots "produit", "vendu" absents → score faible ≈ 0.2

    Exemple (bon) :
        question = "Combien de visiteurs le 2026-05-30 ?"
        answer   = "Le 2026-05-30, 342 visiteurs ont été enregistrés."
        → "visiteurs", "2026-05-30" présents → score élevé ≈ 0.8
    """
    if not answer or not question:
        return 0.0

    # Mots-clés significatifs de la question (>3 chars)
    question_words = set(
        w.lower() for w in re.findall(r'\b\w{4,}\b', question)
    )
    if not question_words:
        return 1.0

    answer_lower = answer.lower()
    covered = sum(1 for w in question_words if w in answer_lower)

    return round(covered / len(question_words), 4)


# ══════════════════════════════════════════════════════════════
# 7. Agrégation — résumé génération
# ══════════════════════════════════════════════════════════════

def compute_generation_metrics(
    answer: str,
    ground_truth: str,
    question: str,
    context_passages: list[str],
) -> dict[str, Any]:
    """
    Calcule toutes les métriques de génération pour une requête.

    Args:
        answer           : réponse générée par le LLM.
        ground_truth     : réponse attendue (ground truth).
        question         : question originale.
        context_passages : passages envoyés au LLM (pour faithfulness).

    Returns:
        Dict avec toutes les métriques de génération.
    """
    rouge = rouge_l(answer, ground_truth)
    return {
        "exact_match":       exact_match(answer, ground_truth),
        "f1_score":          round(f1_score(answer, ground_truth), 4),
        "bleu":              bleu(answer, ground_truth),
        "rouge_l_precision": rouge["precision"],
        "rouge_l_recall":    rouge["recall"],
        "rouge_l_f1":        rouge["f1"],
        "faithfulness":      faithfulness(answer, context_passages),
        "answer_relevancy":  answer_relevancy(answer, question),
    }


# Type hint pour éviter une import circulaire
from typing import Any
