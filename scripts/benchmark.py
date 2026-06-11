#!/usr/bin/env python3
"""
benchmark.py — ShopAnalytics LLM Benchmark
Mesure : TTFT, throughput, JSON tool calling, anti-hallucination
Rapport final : results/benchmark_report.json + affichage console
"""

import os
import sys
import json
import time
import requests
import datetime
from pathlib import Path
from tabulate import tabulate
from config import (
    OLLAMA_HOST, THRESHOLDS, INFERENCE_OPTIONS,
    N_WARMUP, N_RUNS, RESULTS_DIR, DATASET_PATH,
)

HOST = os.environ.get("OLLAMA_HOST", OLLAMA_HOST)
RESULTS = Path(RESULTS_DIR)
RESULTS.mkdir(parents=True, exist_ok=True)

# ── Prompts système ──────────────────────────────────────────
SYSTEM_TOOL_CALLING = """Tu es l'assistant IA de ShopAnalytics, une plateforme retail B2B.
Quand l'utilisateur pose une question sur des données métier, réponds UNIQUEMENT avec un objet JSON valide.
Format obligatoire :
{
  "tool": "<nom_de_l_outil>",
  "parameters": { "<clé>": "<valeur>" }
}
Ne génère aucun texte en dehors du JSON. Pas de markdown, pas d'explication."""

SYSTEM_ANTI_HALLUCINATION = """Tu es l'assistant IA de ShopAnalytics.
Réponds uniquement à partir des données fournies dans le contexte. 
Ne génère jamais de chiffres ou faits non présents dans le contexte."""

ANTI_HALLUCINATION_CONTEXT = """
Contexte (données vérifiées) :
- Date : 11 juin 2026
- Ventes du jour : 0 €  (magasin fermé pour inventaire)
- Météo à Sfax : 38°C, ensoleillé
- Personnel présent : 0 (fermeture exceptionnelle)
"""

ANTI_HALLUCINATION_QUERY = (
    "Le 11 juin, le magasin a réalisé 0 vente et il a neigé à Sfax. "
    "Combien de ventes ont été réalisées et quel temps faisait-il ?"
)

# ── Helpers HTTP ─────────────────────────────────────────────

def call_ollama_stream(model: str, messages: list, system: str = "") -> dict:
    """
    Appel Ollama en mode streaming.
    Retourne : { "ttft": float, "throughput": float, "text": str, "total_tokens": int }
    """
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": INFERENCE_OPTIONS,
    }
    if system:
        payload["system"] = system

    t_start = time.perf_counter()
    t_first_token = None
    full_text = ""
    total_tokens = 0

    with requests.post(
        f"{HOST}/api/chat",
        json=payload,
        stream=True,
        timeout=120,
    ) as resp:
        resp.raise_for_status()
        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            chunk = json.loads(raw_line)

            if "error" in chunk:
                raise RuntimeError(f"Ollama error: {chunk['error']}")

            delta = chunk.get("message", {}).get("content", "")
            if delta and t_first_token is None:
                t_first_token = time.perf_counter()

            full_text += delta
            if chunk.get("done"):
                eval_count = chunk.get("eval_count", 0)
                eval_duration_ns = chunk.get("eval_duration", 1)
                total_tokens = eval_count
                break

    t_end = time.perf_counter()
    ttft = (t_first_token - t_start) if t_first_token else (t_end - t_start)
    generation_time = t_end - (t_first_token or t_start)
    throughput = total_tokens / generation_time if generation_time > 0 else 0.0

    return {
        "ttft": round(ttft, 3),
        "throughput": round(throughput, 1),
        "text": full_text.strip(),
        "total_tokens": total_tokens,
    }


# ── Tests ────────────────────────────────────────────────────

def test_ttft_throughput(model: str) -> dict:
    """Test TTFT et throughput sur un prompt simple."""
    print(f"    [TTFT+Throughput] warmup × {N_WARMUP} ...")
    
    messages = [{"role": "user", "content": "Quels sont les articles les plus vendus cette semaine ?"}]
    
    # Warmup (ignoré)
    for _ in range(N_WARMUP):
        call_ollama_stream(model, messages, SYSTEM_TOOL_CALLING)

    print(f"    [TTFT+Throughput] mesures × {N_RUNS} ...")
    ttfts, throughputs = [], []
    for i in range(N_RUNS):
        result = call_ollama_stream(model, messages, SYSTEM_TOOL_CALLING)
        ttfts.append(result["ttft"])
        throughputs.append(result["throughput"])
        print(f"      run {i+1}: TTFT={result['ttft']}s  TPS={result['throughput']}")

    return {
        "ttft_avg": round(sum(ttfts) / len(ttfts), 3),
        "ttft_min": round(min(ttfts), 3),
        "throughput_avg": round(sum(throughputs) / len(throughputs), 1),
        "throughput_max": round(max(throughputs), 1),
    }


def test_json_tool_calling(model: str, dataset: list) -> dict:
    """Test de fidélité au format JSON strict sur 50 requêtes métier."""
    print(f"    [Tool Calling] {len(dataset)} requêtes ...")
    
    valid_json = 0
    valid_tool = 0
    errors = []

    for i, item in enumerate(dataset):
        if (i + 1) % 10 == 0:
            print(f"      → {i+1}/{len(dataset)} requêtes traitées ...")
        
        messages = [{"role": "user", "content": item["query"]}]
        try:
            result = call_ollama_stream(model, messages, SYSTEM_TOOL_CALLING)
            text = result["text"]
            
            # Nettoyer éventuels backticks markdown
            text_clean = text.strip().strip("```json").strip("```").strip()
            
            parsed = json.loads(text_clean)
            valid_json += 1
            
            if parsed.get("tool") and parsed.get("parameters") is not None:
                valid_tool += 1
            else:
                errors.append({"id": item["id"], "reason": "missing_tool_or_parameters", "raw": text[:100]})
        
        except json.JSONDecodeError:
            errors.append({"id": item["id"], "reason": "invalid_json", "raw": result.get("text", "")[:100]})
        except Exception as e:
            errors.append({"id": item["id"], "reason": str(e)[:80]})

    total = len(dataset)
    return {
        "total_queries": total,
        "valid_json": valid_json,
        "valid_json_pct": round(valid_json / total * 100, 1),
        "valid_tool_structure": valid_tool,
        "valid_tool_pct": round(valid_tool / total * 100, 1),
        "errors": errors[:10],  # max 10 exemples d'erreurs
    }


def test_anti_hallucination(model: str) -> dict:
    """Test de fidélité au contexte — le modèle ne doit pas inventer."""
    print(f"    [Anti-Hallucination] ...")
    
    messages = [
        {"role": "user", "content": ANTI_HALLUCINATION_CONTEXT + "\n\n" + ANTI_HALLUCINATION_QUERY}
    ]
    result = call_ollama_stream(model, messages, SYSTEM_ANTI_HALLUCINATION)
    text = result["text"].lower()
    
    # Vérifications simples : le modèle doit mentionner 0 vente et ne PAS mentionner de neige
    mentions_zero_sales = "0" in text or "zéro" in text or "aucune" in text
    mentions_snow = any(w in text for w in ["neige", "snow", "neigé", "neiger"])
    # La réponse correcte : 0 vente, 38°C ensoleillé
    mentions_sun = any(w in text for w in ["38", "ensoleillé", "soleil", "chaud"])
    
    passed = mentions_zero_sales and not mentions_snow
    
    return {
        "response": result["text"][:300],
        "mentions_correct_sales": mentions_zero_sales,
        "invented_snow": mentions_snow,
        "mentions_correct_weather": mentions_sun,
        "hallucination_free": passed,
    }


def test_context_latency_penalty(model: str) -> dict:
    """Mesure de la dégradation du throughput avec un contexte long."""
    print(f"    [Context Latency Penalty] court vs long ...")
    
    short_msg = [{"role": "user", "content": "Quelles sont les ventes d'aujourd'hui ?"}]
    long_context = "Données de vente : " + ", ".join([f"SKU-{i}: {i*3} unités" for i in range(500)])
    long_msg = [{"role": "user", "content": long_context + "\n\nFais un résumé des ventes."}]
    
    r_short = call_ollama_stream(model, short_msg, SYSTEM_TOOL_CALLING)
    r_long = call_ollama_stream(model, long_msg, SYSTEM_ANTI_HALLUCINATION)
    
    penalty_pct = 0.0
    if r_short["throughput"] > 0:
        penalty_pct = round((r_short["throughput"] - r_long["throughput"]) / r_short["throughput"] * 100, 1)
    
    return {
        "throughput_short_ctx": r_short["throughput"],
        "throughput_long_ctx": r_long["throughput"],
        "degradation_pct": penalty_pct,
    }


# ── Scoring ──────────────────────────────────────────────────

def score_model(results: dict) -> dict:
    """Calcule un score global et des flags pass/fail."""
    perf = results["ttft_throughput"]
    tc = results["tool_calling"]
    ah = results["anti_hallucination"]

    ttft_ok = perf["ttft_avg"] <= THRESHOLDS["ttft_max_sec"]
    tps_ok = perf["throughput_avg"] >= THRESHOLDS["throughput_min_tps"]
    tps_min_ok = perf["throughput_avg"] >= THRESHOLDS["throughput_hard_min"]
    json_ok = tc["valid_json_pct"] >= THRESHOLDS["json_success_min_pct"]
    ah_ok = ah["hallucination_free"]

    # Score pondéré /100
    score = 0
    score += 25 if ttft_ok else (12 if perf["ttft_avg"] <= 3.0 else 0)
    score += 25 if tps_ok else (12 if tps_min_ok else 0)
    score += 35 if json_ok else round(35 * tc["valid_json_pct"] / 100)
    score += 15 if ah_ok else 0

    return {
        "score_100": score,
        "ttft_pass": ttft_ok,
        "throughput_pass": tps_ok,
        "json_pass": json_ok,
        "hallucination_free": ah_ok,
        "recommended": ttft_ok and tps_min_ok and json_ok and ah_ok,
    }


# ── Main ─────────────────────────────────────────────────────

def main():
    # Charger les modèles éligibles
    eligible_path = RESULTS / "eligible_models.json"
    if not eligible_path.exists():
        print("[ERROR] eligible_models.json introuvable. Lancer pull_models.py d'abord.")
        sys.exit(1)

    with open(eligible_path) as f:
        models = json.load(f)

    with open(DATASET_PATH) as f:
        dataset = json.load(f)

    print("\n" + "="*60)
    print("  ShopAnalytics — LLM Benchmark")
    print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Modèles à tester : {len(models)}")
    print("="*60)

    all_results = []

    for model_meta in models:
        model_id = model_meta["id"]
        label = model_meta["label"]
        print(f"\n{'─'*60}")
        print(f"  Modèle : {label}")
        print(f"{'─'*60}")

        try:
            model_result = {
                "model_id": model_id,
                "label": label,
                "timestamp": datetime.datetime.now().isoformat(),
            }

            model_result["ttft_throughput"] = test_ttft_throughput(model_id)
            model_result["tool_calling"] = test_json_tool_calling(model_id, dataset)
            model_result["anti_hallucination"] = test_anti_hallucination(model_id)
            model_result["context_latency"] = test_context_latency_penalty(model_id)
            model_result["scoring"] = score_model(model_result)

            all_results.append(model_result)

            # Sauvegarde intermédiaire
            out_path = RESULTS / f"result_{model_id.replace(':', '_').replace('/', '_')}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(model_result, f, indent=2, ensure_ascii=False)
            print(f"\n  → Résultats sauvegardés : {out_path.name}")

        except Exception as e:
            print(f"\n  [ERROR] Benchmark échoué pour {model_id} : {e}")
            all_results.append({"model_id": model_id, "label": label, "error": str(e)})

    # ── Rapport final ────────────────────────────────────────
    print("\n\n" + "="*60)
    print("  RAPPORT FINAL — COMPARAISON DES MODÈLES")
    print("="*60)

    table_rows = []
    for r in all_results:
        if "error" in r:
            table_rows.append([r["label"], "ERROR", "-", "-", "-", "-", "-"])
            continue
        p = r["ttft_throughput"]
        tc = r["tool_calling"]
        s = r["scoring"]
        table_rows.append([
            r["label"],
            f"{p['ttft_avg']}s {'✓' if s['ttft_pass'] else '✗'}",
            f"{p['throughput_avg']} t/s {'✓' if s['throughput_pass'] else '✗'}",
            f"{tc['valid_json_pct']}% {'✓' if s['json_pass'] else '✗'}",
            "✓" if s["hallucination_free"] else "✗",
            f"{s['score_100']}/100",
            "✅ RECOMMANDÉ" if s["recommended"] else "❌",
        ])

    headers = ["Modèle", "TTFT", "Throughput", "JSON%", "Anti-Halluc.", "Score", "Verdict"]
    print(tabulate(table_rows, headers=headers, tablefmt="rounded_outline"))

    # Meilleur modèle
    scored = [r for r in all_results if "scoring" in r]
    if scored:
        best = max(scored, key=lambda r: r["scoring"]["score_100"])
        print(f"\n  🏆 Meilleur modèle : {best['label']} (score {best['scoring']['score_100']}/100)")
        if best["scoring"]["recommended"]:
            print(f"     → Tous les seuils validés. Déploiement recommandé.")
        else:
            print(f"     → Certains seuils non atteints — voir rapport détaillé.")

    # Sauvegarde rapport global
    report_path = RESULTS / "benchmark_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.datetime.now().isoformat(),
            "thresholds": THRESHOLDS,
            "results": all_results,
        }, f, indent=2, ensure_ascii=False)
    print(f"\n  📄 Rapport complet → {report_path}")


if __name__ == "__main__":
    main()
