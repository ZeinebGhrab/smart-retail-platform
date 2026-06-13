#!/usr/bin/env python3
"""
pull_models.py — ShopAnalytics
Pull les modèles candidats depuis Ollama après filtrage matériel VRAM.
"""

import os
import sys
import json
import requests
from config import CANDIDATE_MODELS, VRAM_AVAILABLE_GB, vram_required_gb, OLLAMA_HOST

HOST = os.environ.get("OLLAMA_HOST", OLLAMA_HOST)


def print_header(text: str):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def get_already_pulled() -> set:
    try:
        r = requests.get(f"{HOST}/api/tags", timeout=10)
        r.raise_for_status()
        tags = r.json().get("models", [])
        return {m["name"] for m in tags}
    except Exception as e:
        print(f"[WARN] Impossible de lister les modèles existants : {e}")
        return set()


def pull_model(model_id: str) -> bool:
    print(f"\n  → Pull en cours : {model_id} ...")
    try:
        with requests.post(
            f"{HOST}/api/pull",
            json={"name": model_id, "stream": True},
            stream=True,
            timeout=1800,  # 30 min max
        ) as r:
            r.raise_for_status()
            last_status = ""
            for line in r.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                status = data.get("status", "")
                if status != last_status:
                    print(f"     {status}")
                    last_status = status
                if data.get("error"):
                    print(f"  [ERROR] {data['error']}")
                    return False
        print(f"  ✓ {model_id} prêt.")
        return True
    except Exception as e:
        print(f"  [ERROR] Pull échoué pour {model_id} : {e}")
        return False


def main():
    print_header("ShopAnalytics — Pull des modèles LLM")
    print(f"  Ollama host  : {HOST}")
    print(f"  VRAM dispo   : {VRAM_AVAILABLE_GB} Go")

    already_pulled = get_already_pulled()
    eligible = []
    skipped = []

    print("\n  Filtrage matériel (VRAM) :")
    print(f"  {'Modèle':<45} {'VRAM req':>10}  {'Statut'}")
    print(f"  {'-'*45} {'-'*10}  {'-'*12}")

    for m in CANDIDATE_MODELS:
        required = vram_required_gb(m["params_b"])
        if required > VRAM_AVAILABLE_GB:
            status = f"✗ ÉLIMINÉ ({required:.1f} Go > {VRAM_AVAILABLE_GB} Go)"
            skipped.append(m)
        else:
            status = f"✓ OK ({required:.1f} Go)"
            eligible.append(m)
        print(f"  {m['label']:<45} {required:>9.1f}G  {status}")

    if not eligible:
        print("\n[ERREUR] Aucun modèle ne rentre dans la VRAM disponible.")
        print("         Augmentez VRAM_AVAILABLE_GB dans config.py ou utilisez des modèles plus petits.")
        sys.exit(1)

    print(f"\n  → {len(eligible)} modèle(s) éligible(s), {len(skipped)} éliminé(s).")

    pulled_ok = []
    for m in eligible:
        if m["id"] in already_pulled:
            print(f"\n  ✓ {m['id']} déjà présent, skip.")
            pulled_ok.append(m["id"])
        else:
            if pull_model(m["id"]):
                pulled_ok.append(m["id"])

    print_header("Résumé des pulls")
    for mid in pulled_ok:
        print(f"  ✓ {mid}")

    if not pulled_ok:
        print("[ERREUR] Aucun modèle disponible pour le benchmark.")
        sys.exit(1)

    # Sauvegarder la liste des modèles eligibles pour benchmark.py
    with open("/workspace/results/eligible_models.json", "w") as f:
        json.dump(
            [m for m in eligible if m["id"] in pulled_ok],
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(f"\n  Liste sauvegardée → /workspace/results/eligible_models.json")


if __name__ == "__main__":
    main()
