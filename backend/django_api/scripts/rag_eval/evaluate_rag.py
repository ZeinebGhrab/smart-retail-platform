#!/usr/bin/env python3
"""
rag_eval/evaluate_rag.py — Évaluateur RAG complet pour Anavid Store 360
=========================================================================
Ce script évalue le pipeline RAG d'Anavid sur deux niveaux :
  1. Qualité du Retriever (KB sémantique + CSV visiteurs)
  2. Qualité de la Génération (réponse Llama 3.2 via Ollama)

Métriques Retriever :
  - Precision@K, Recall@K, MRR, nDCG@K
  - Context Precision, Context Recall

Métriques Génération :
  - Exact Match, F1 Score, BLEU-2, ROUGE-L
  - Faithfulness, Answer Relevancy

Usage :
  # Depuis le dossier backend/scripts/
  python rag_eval/evaluate_rag.py

  # Avec un dataset personnalisé
  python rag_eval/evaluate_rag.py --dataset /chemin/eval_dataset.json

  # Mode verbose (affiche chaque réponse)
  python rag_eval/evaluate_rag.py --verbose

  # Sans appeler Ollama (utilise les réponses mock pour tester le module)
  python rag_eval/evaluate_rag.py --dry-run

Rapport de sortie :
  results/rag_eval_report.json  ← rapport complet
  Affichage console             ← résumé tabulaire
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Ajouter le dossier django_api au path pour importer rag_pipeline
# NB: selon le conteneur depuis lequel ce script est lancé, le code
# Django ne se trouve pas forcément au même endroit :
#   - conteneur "django_api" : code monté sur /app
#   - lancement local        : backend/django_api (sibling de scripts/)
_BACKEND = Path(__file__).resolve().parent.parent
_CANDIDATES = [
    _BACKEND / "django_api",
    Path("/app"),
]
_RAG_FOUND = False
for _candidate in _CANDIDATES:
    # Support both locations: history/rag_pipeline.py (legacy) and history/chatbot/rag_pipeline.py
    if (_candidate / "history" / "rag_pipeline.py").exists():
        sys.path.insert(0, str(_candidate))
        _RAG_FOUND = True
        break
    if (_candidate / "history" / "chatbot" / "rag_pipeline.py").exists():
        sys.path.insert(0, str(_candidate))
        _RAG_FOUND = True
        break

try:
    # Essai 1 : history.chatbot.rag_pipeline (emplacement actuel sprint-2)
    try:
        from history.chatbot.rag_pipeline import (
            _retrieve_kb,
            _build_csv_context,
            _call_ollama,
            _build_prompt,
            _is_pure_data_query,
            KB_JSON,
            run_rag_pipeline,
        )
    except ImportError:
        # Essai 2 : history.rag_pipeline (emplacement legacy)
        from history.rag_pipeline import (
            _retrieve_kb,
            _build_csv_context,
            _call_ollama,
            _build_prompt,
            _is_pure_data_query,
            KB_JSON,
            run_rag_pipeline,
        )
    PIPELINE_AVAILABLE = True
    print("[INFO] rag_pipeline accessible.")
except ImportError as _ie:
    PIPELINE_AVAILABLE = False
    print(f"[WARN] rag_pipeline non accessible — mode --dry-run forcé. ({_ie})\n")

from metrics_retriever import compute_retriever_metrics
from metrics_generation import compute_generation_metrics

# ── Chemins ──────────────────────────────────────────────────
EVAL_DIR     = Path(__file__).parent
RESULTS_DIR  = _BACKEND / "results"
DATASET_PATH = EVAL_DIR / "eval_dataset.json"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

K = 2  # n_results du pipeline Anavid (_retrieve_kb retourne 2 docs)


# ══════════════════════════════════════════════════════════════
# Extraction des IDs récupérés depuis le texte KB retourné
# ══════════════════════════════════════════════════════════════

def _parse_kb_ids_from_text(kb_text: str) -> list[str]:
    """
    Extrait les IDs de documents KB depuis le texte retourné par _retrieve_kb().
    Format attendu : "[kb-001] Contenu..." ou "[Horaires d'ouverture] Contenu..."

    Si les IDs ne sont pas dans le texte, on fait le matching par titre.
    """
    import re

    # Cherche les IDs directs au format [kb-XXX]
    ids = re.findall(r'\[(kb-\d{3})\]', kb_text)
    if ids:
        return ids

    # Sinon on retourne une liste vide (le texte sera utilisé directement)
    return []


def _load_kb_title_to_id() -> dict[str, str]:
    """Charge la correspondance titre → ID depuis knowledge_base.json."""
    if not KB_JSON.exists():
        return {}
    try:
        with open(str(KB_JSON), encoding="utf-8") as f:
            docs = json.load(f)
        return {d["title"].lower(): d["id"] for d in docs}
    except Exception:
        return {}


def _infer_kb_ids_from_text(kb_text: str, title_to_id: dict[str, str]) -> list[str]:
    """Infère les IDs KB en cherchant les titres exacts dans le texte récupéré.

    rag_pipeline._retrieve_kb() renvoie le texte sous la forme
    "[Titre du doc] Contenu...\n[Titre du doc 2] Contenu...".
    On cherche donc le titre complet (et non quelques mots, trop bruités
    par les mots courants comme "du"/"de"/"des"), et on conserve l'ordre
    d'apparition dans kb_text (= ordre de pertinence renvoyé par le pipeline).
    """
    kb_lower = kb_text.lower()
    matches: list[tuple[int, str]] = []
    for title, doc_id in title_to_id.items():
        idx = kb_lower.find(title)
        if idx != -1:
            matches.append((idx, doc_id))
    matches.sort(key=lambda t: t[0])
    return [doc_id for _, doc_id in matches[:K]]


# ══════════════════════════════════════════════════════════════
# Réponses mock pour --dry-run
# ══════════════════════════════════════════════════════════════

MOCK_ANSWERS = {
    "eval-001": "Le magasin est ouvert du lundi au samedi de 9h à 20h et le dimanche de 10h à 18h.",
    "eval-002": "Le taux de conversion correspond au rapport entre le nombre d'acheteurs et le nombre total de visiteurs, exprimé en pourcentage.",
    "eval-003": "Le panier moyen est calculé en divisant le chiffre d'affaires par le nombre de transactions.",
    "eval-004": "Deux caméras sont installées : Porte_nord et Porte_sud.",
    "eval-005": "En cas de stock critique, une alerte est envoyée au responsable logistique pour réapprovisionner sous 24h.",
    "eval-006": "Les pics de visites surviennent entre 11h-13h et 16h-18h.",
    "eval-007": "Le modèle ne prend pas en compte les événements exceptionnels et sa précision diminue au-delà de 7 jours.",
    "eval-008": "Les données CSV indiquent les visites enregistrées pour cette date.",
    "eval-009": "Le résumé global inclut le total des visites et la répartition par genre sur toute la période.",
    "eval-010": "Les données de la Porte_nord pour la date demandée sont disponibles dans le CSV.",
    "eval-011": "Non, la politique interdit le partage des données visiteurs avec des tiers sans consentement.",
    "eval-012": "Voici l'historique des 7 derniers jours avec le nombre de visiteurs par jour et la moyenne journalière.",
}

MOCK_KB_RETRIEVED = {
    "eval-001": ["kb-001"],
    "eval-002": ["kb-002"],
    "eval-003": ["kb-003"],
    "eval-004": ["kb-004"],
    "eval-005": ["kb-005"],
    "eval-006": ["kb-007"],
    "eval-007": ["kb-008"],
    "eval-008": [],
    "eval-009": [],
    "eval-010": ["kb-004"],
    "eval-011": ["kb-006"],
    "eval-012": [],
}


# ══════════════════════════════════════════════════════════════
# Évaluation d'une requête
# ══════════════════════════════════════════════════════════════

def evaluate_one(
    item: dict,
    title_to_id: dict[str, str],
    dry_run: bool = False,
    verbose: bool = False,
) -> dict:
    """
    Évalue une seule requête du dataset.

    Retourne un dict avec :
      - id, question, ground_truth
      - retrieved_kb_ids, retrieved_passages
      - answer
      - retriever_metrics, generation_metrics
      - latency_ms
    """
    question    = item["question"]
    ground_truth = item["ground_truth"]
    relevant_ids = item.get("relevant_kb_ids", [])

    t_start = time.perf_counter()

    if dry_run or not PIPELINE_AVAILABLE:
        # Mode dry-run : réponses et retrieval simulés
        answer = MOCK_ANSWERS.get(item["id"], "Réponse simulée.")
        kb_ids = MOCK_KB_RETRIEVED.get(item["id"], [])
        kb_texts = [f"[{kid}] Contenu simulé pour {kid}" for kid in kb_ids]
        csv_text = "Données CSV simulées."
        retrieved_passages = kb_texts + ([csv_text] if csv_text else [])
    else:
        # Mode réel : appel au pipeline Anavid
        try:
            csv_text = _build_csv_context(question)
            if _is_pure_data_query(question):
                kb_text = ""
            else:
                kb_text  = _retrieve_kb(question, n_results=K)

            # Extraire les IDs des docs récupérés
            kb_ids = _parse_kb_ids_from_text(kb_text)
            if not kb_ids:
                kb_ids = _infer_kb_ids_from_text(kb_text, title_to_id)

            retrieved_passages = [p for p in (kb_text, csv_text) if p]
            prompt = _build_prompt(question, csv_text, kb_text)
            answer = _call_ollama(prompt)

        except Exception as exc:
            answer = f"[ERREUR] {exc}"
            kb_ids = []
            retrieved_passages = []

    latency_ms = round((time.perf_counter() - t_start) * 1000, 1)

    # Calcul des métriques
    retriever_m = compute_retriever_metrics(
        retrieved_ids=kb_ids,
        relevant_ids=relevant_ids,
        retrieved_passages=retrieved_passages,
        answer=answer,
        ground_truth=ground_truth,
        k=K,
    )

    generation_m = compute_generation_metrics(
        answer=answer,
        ground_truth=ground_truth,
        question=question,
        context_passages=retrieved_passages,
    )

    result = {
        "id":                item["id"],
        "question":          question,
        "category":          item.get("category", "unknown"),
        "relevant_source":   item.get("relevant_source", "unknown"),
        "ground_truth":      ground_truth,
        "answer":            answer,
        "retrieved_kb_ids":  kb_ids,
        "relevant_kb_ids":   relevant_ids,
        "retriever_metrics": retriever_m,
        "generation_metrics": generation_m,
        "latency_ms":        latency_ms,
    }

    if verbose:
        _print_item_result(result)

    return result


def _print_item_result(r: dict) -> None:
    """Affiche le détail d'une requête évaluée."""
    print(f"\n  ┌─ [{r['id']}] {r['question'][:70]}")
    print(f"  │  Réponse    : {r['answer'][:80]}...")
    rm = r["retriever_metrics"]
    gm = r["generation_metrics"]
    print(f"  │  KB récup.  : {r['retrieved_kb_ids']}  (attendus: {r['relevant_kb_ids']})")
    print(f"  │  P@{K}={rm[f'precision@{K}']:.2f}  R@{K}={rm[f'recall@{K}']:.2f}  MRR={rm['mrr']:.2f}  nDCG@{K}={rm[f'ndcg@{K}']:.2f}")
    print(f"  │  F1={gm['f1_score']:.2f}  ROUGE-L={gm['rouge_l_f1']:.2f}  Faith={gm['faithfulness']:.2f}  Relev={gm['answer_relevancy']:.2f}")
    print(f"  └─ Latence : {r['latency_ms']} ms")


# ══════════════════════════════════════════════════════════════
# Agrégation des résultats
# ══════════════════════════════════════════════════════════════

def aggregate_results(results: list[dict]) -> dict:
    """Calcule les moyennes de toutes les métriques sur l'ensemble du dataset."""

    def _avg(key_path: list[str]) -> float:
        vals = []
        for r in results:
            obj = r
            for k in key_path:
                obj = obj.get(k, {})
            if isinstance(obj, (int, float)):
                vals.append(obj)
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    return {
        "n_queries": len(results),
        "retriever": {
            f"precision@{K}": _avg(["retriever_metrics", f"precision@{K}"]),
            f"recall@{K}":    _avg(["retriever_metrics", f"recall@{K}"]),
            "mrr":            _avg(["retriever_metrics", "mrr"]),
            f"ndcg@{K}":      _avg(["retriever_metrics", f"ndcg@{K}"]),
            "context_precision": _avg(["retriever_metrics", "context_precision"]),
            "context_recall":    _avg(["retriever_metrics", "context_recall"]),
        },
        "generation": {
            "exact_match":       _avg(["generation_metrics", "exact_match"]),
            "f1_score":          _avg(["generation_metrics", "f1_score"]),
            "bleu":              _avg(["generation_metrics", "bleu"]),
            "rouge_l_f1":        _avg(["generation_metrics", "rouge_l_f1"]),
            "faithfulness":      _avg(["generation_metrics", "faithfulness"]),
            "answer_relevancy":  _avg(["generation_metrics", "answer_relevancy"]),
        },
        "latency_ms_avg": _avg(["latency_ms"]),
    }


def _score_overall(agg: dict) -> dict:
    """
    Calcule un score global /100 selon les priorités du projet Anavid.

    Pondération :
      - Faithfulness       : 30 pts  (priorité #1 — pas d'hallucination)
      - Answer Relevancy   : 20 pts  (répond à la question)
      - Context Recall     : 15 pts  (contexte suffisant)
      - F1 Score           : 15 pts  (qualité textuelle)
      - Precision@K        : 10 pts  (retrieval KB propre)
      - MRR                : 10 pts  (premier doc pertinent)
    """
    r = agg["retriever"]
    g = agg["generation"]

    score = (
        g["faithfulness"]      * 30 +
        g["answer_relevancy"]  * 20 +
        r["context_recall"]    * 15 +
        g["f1_score"]          * 15 +
        r[f"precision@{K}"]    * 10 +
        r["mrr"]               * 10
    )
    return {
        "score_100":     round(score, 1),
        "faithfulness_ok":     g["faithfulness"] >= 0.70,
        "relevancy_ok":        g["answer_relevancy"] >= 0.60,
        "context_recall_ok":   r["context_recall"] >= 0.60,
        "retrieval_precision_ok": r[f"precision@{K}"] >= 0.75,
    }


# ══════════════════════════════════════════════════════════════
# Affichage console
# ══════════════════════════════════════════════════════════════

def print_report(agg: dict, scoring: dict) -> None:
    """Affiche le rapport final dans la console."""
    r = agg["retriever"]
    g = agg["generation"]

    print("\n" + "═" * 65)
    print("  ANAVID RAG EVALUATION — RAPPORT FINAL")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  {agg['n_queries']} requêtes évaluées")
    print("═" * 65)

    print("\n  📡 RETRIEVER\n")
    print(f"    Precision@{K}       : {r[f'precision@{K}']:.4f}  {'✅' if r[f'precision@{K}'] >= 0.75 else '⚠️ '}")
    print(f"    Recall@{K}          : {r[f'recall@{K}']:.4f}")
    print(f"    MRR               : {r['mrr']:.4f}  {'✅' if r['mrr'] >= 0.75 else '⚠️ '}")
    print(f"    nDCG@{K}            : {r[f'ndcg@{K}']:.4f}")
    print(f"    Context Precision : {r['context_precision']:.4f}")
    print(f"    Context Recall    : {r['context_recall']:.4f}  {'✅' if r['context_recall'] >= 0.60 else '⚠️ '}")

    print("\n  ✍️  GÉNÉRATION\n")
    print(f"    Exact Match       : {g['exact_match']:.4f}")
    print(f"    F1 Score          : {g['f1_score']:.4f}  {'✅' if g['f1_score'] >= 0.50 else '⚠️ '}")
    print(f"    BLEU-2            : {g['bleu']:.4f}")
    print(f"    ROUGE-L F1        : {g['rouge_l_f1']:.4f}")
    print(f"    Faithfulness      : {g['faithfulness']:.4f}  {'✅' if g['faithfulness'] >= 0.70 else '❌'}")
    print(f"    Answer Relevancy  : {g['answer_relevancy']:.4f}  {'✅' if g['answer_relevancy'] >= 0.60 else '⚠️ '}")

    print(f"\n  ⏱️  Latence moyenne : {agg['latency_ms_avg']:.0f} ms")

    print("\n" + "─" * 65)
    verdict = "✅ PIPELINE RAG VALIDÉ" if scoring["score_100"] >= 70 else "⚠️  AMÉLIORATIONS RECOMMANDÉES"
    print(f"\n  🏆 SCORE GLOBAL : {scoring['score_100']}/100  — {verdict}")
    print()

    if not scoring["faithfulness_ok"]:
        print("  ❌ Faithfulness < 0.70 : risque d'hallucinations — vérifier le prompt système")
    if not scoring["relevancy_ok"]:
        print("  ⚠️  Answer Relevancy < 0.60 : les réponses ne ciblent pas assez les questions")
    if not scoring["context_recall_ok"]:
        print("  ⚠️  Context Recall < 0.60 : le contexte récupéré est insuffisant")
    if not scoring["retrieval_precision_ok"]:
        print("  ⚠️  Precision@K < 0.75 : trop de docs KB non pertinents récupérés")
    print()


# ══════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Évaluateur RAG pour Anavid Store 360"
    )
    parser.add_argument(
        "--dataset", type=Path, default=DATASET_PATH,
        help=f"Chemin vers le dataset d'évaluation (défaut: {DATASET_PATH})"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Affiche le détail de chaque requête évaluée"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Utilise des réponses simulées (sans appeler Ollama)"
    )
    parser.add_argument(
        "--output", type=Path, default=RESULTS_DIR / "rag_eval_report.json",
        help="Chemin du rapport JSON de sortie"
    )
    args = parser.parse_args()

    dry_run = args.dry_run or not PIPELINE_AVAILABLE

    # Chargement du dataset
    if not args.dataset.exists():
        print(f"[ERROR] Dataset introuvable : {args.dataset}")
        sys.exit(1)

    with open(args.dataset, encoding="utf-8") as f:
        dataset = json.load(f)

    print(f"\n{'═' * 65}")
    print("  Anavid Store 360 — RAG Evaluation")
    print(f"  {len(dataset)} requêtes  |  {'Mode dry-run' if dry_run else 'Mode réel (Ollama)'}")
    print(f"{'═' * 65}")

    # Chargement de la KB pour le matching IDs
    title_to_id = _load_kb_title_to_id() if PIPELINE_AVAILABLE else {}

    # Évaluation
    all_results = []
    for i, item in enumerate(dataset, 1):
        print(f"  [{i:02d}/{len(dataset)}] {item['question'][:55]}...", end="\r")
        result = evaluate_one(item, title_to_id, dry_run=dry_run, verbose=args.verbose)
        all_results.append(result)
    print(" " * 70, end="\r")  # effacer la ligne de progression

    # Agrégation et scoring
    agg     = aggregate_results(all_results)
    scoring = _score_overall(agg)

    # Affichage console
    print_report(agg, scoring)

    # Sauvegarde JSON
    report = {
        "generated_at": datetime.now().isoformat(),
        "config": {
            "k": K,
            "model": os.environ.get("OLLAMA_MODEL", "llama3.2:3b-instruct-q4_K_M"),
            "dry_run": dry_run,
            "dataset": str(args.dataset),
        },
        "aggregate": agg,
        "scoring": scoring,
        "details": all_results,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"  📄 Rapport JSON → {args.output}\n")


if __name__ == "__main__":
    main()