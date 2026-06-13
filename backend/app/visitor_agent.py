# ============================================================
# visitor_agent.py — Agent chatbot (RAG + tool calling, Ollama)
# ============================================================
#
# Couvre les requêtes ShopAnalytics liées aux VISITEURS :
#   - get_visitor_count          (id 3, 23 dans tool_calling_queries.json)
#   - get_hourly_visitor_flow     (id 18)
#   - get_sales_forecast / prévision  -> adapté ici en forecast_visitors (id 24)
#
# Modèle sélectionné automatiquement depuis results/eligible_models.json
# (modèle retenu après filtrage VRAM : Llama 3.2 3B q4_K_M sur la
# config testée — voir README section 12-13).
#
# Usage :
#   python app/visitor_agent.py "Combien de visiteurs hier ?"
#   python app/visitor_agent.py "Quel est le flux horaire aujourd'hui ?"
#   python app/visitor_agent.py "Prévois le nombre de visiteurs pour demain"
# ============================================================

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

from visitor_data import (
    load_data,
    get_visitor_count,
    get_hourly_visitor_flow,
    forecast_visitors,
    get_visitor_history,
)

try:
    from vector_store import semantic_search
except ImportError:  # chromadb non installé / non requis pour les tests purs visiteurs
    semantic_search = None

ROOT = Path(__file__).resolve().parent.parent
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


def get_active_model() -> str:
    """Lit le modèle recommandé dans results/eligible_models.json."""
    eligible_path = ROOT / "results" / "eligible_models.json"
    try:
        with open(eligible_path, encoding="utf-8") as f:
            models = json.load(f)
        if models:
            return models[0]["id"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError, IndexError):
        pass
    return "llama3.2:3b-instruct-q4_K_M"  # repli par défaut


# ------------------------------------------------------------
# Outils exposés au LLM (function calling)
# ------------------------------------------------------------

TOOLS_SPEC = """
Tu es un assistant analytique pour ShopAnalytics (Anavid Store 360).
Tu dois répondre UNIQUEMENT en JSON valide, avec ce format :
{"tool": "<nom_outil>", "parameters": {...}}

Outils disponibles :
1. get_visitor_count(date, camera)
   - "date": format YYYY-MM-DD ou null pour la dernière date connue
   - "camera": "Porte_sud", "Porte_nord" ou null pour le total
   - Utilise cet outil pour : "combien de visiteurs", "nombre de visiteurs enregistrés"

2. get_hourly_visitor_flow(date, camera)
   - mêmes paramètres, retourne le flux horaire de visiteurs
   - Utilise cet outil pour : "flux horaire", "flux de visiteurs par heure"

3. forecast_visitors(target_date, camera)
   - "target_date": format YYYY-MM-DD ou null pour demain
   - Utilise cet outil pour : "prévision", "prédire", "combien de visiteurs demain/la semaine prochaine"

4. get_visitor_history(start_date, end_date, camera, n_days)
   - "start_date" / "end_date": format YYYY-MM-DD ou null
   - "camera": "Porte_sud", "Porte_nord" ou null pour le total
   - "n_days": nombre entier (ex: 7) ou null. Si start_date/end_date sont null
     et n_days est fourni, retourne les n_days derniers jours disponibles.
   - Utilise cet outil pour : "historique", "évolution", "tendance",
     "ces derniers jours/semaines/mois", "compare les jours précédents"

5. search_knowledge_base(query)
   - "query": la question reformulée
   - Utilise cet outil pour toute question GÉNÉRALE/DÉFINITION ne portant pas
     sur un chiffre précis du jour (ex : "qu'est-ce que le taux de conversion ?",
     "quels sont les horaires du magasin ?", "quelles caméras sont installées ?")

Réponds uniquement avec le JSON, sans texte additionnel.
"""


def _search_kb_tool(query: str, data: dict | None = None) -> dict:
    """Wrapper outil : recherche sémantique dans la base vectorielle (KB)."""
    if semantic_search is None:
        return {"error": "Base vectorielle indisponible (chromadb non installé)."}
    hits = semantic_search(query, n_results=2)
    return {"query": query, "results": hits}


TOOL_FUNCS = {
    "get_visitor_count": get_visitor_count,
    "get_hourly_visitor_flow": get_hourly_visitor_flow,
    "forecast_visitors": forecast_visitors,
    "get_visitor_history": get_visitor_history,
    "search_knowledge_base": _search_kb_tool,
}


def call_llm(prompt: str, model: str) -> str:
    """Appelle Ollama en mode génération (non-stream)."""
    resp = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model": model,
            "prompt": f"{TOOLS_SPEC}\n\nRequête utilisateur : {prompt}\n\nJSON :",
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_ctx": 4096,
                "num_predict": 512,
            },
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


def parse_tool_call(raw: str) -> dict | None:
    """Extrait le JSON {"tool": ..., "parameters": {...}} de la réponse LLM."""
    raw = raw.strip()
    # Retire d'éventuels ```json ... ``` ou texte autour
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        return None
    candidate = raw[start:end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _clean_params(params: dict) -> dict:
    """Nettoie les paramètres renvoyés par le LLM (ex: "null" string -> None)."""
    cleaned = {}
    for k, v in params.items():
        if isinstance(v, str) and v.strip().lower() in ("null", "none", ""):
            cleaned[k] = None
        else:
            cleaned[k] = v
    return cleaned


def run_tool(call: dict, data: dict) -> dict:
    tool_name = call.get("tool")
    params = _clean_params(call.get("parameters", {}) or {})
    func = TOOL_FUNCS.get(tool_name)
    if not func:
        return {"error": f"Outil inconnu : {tool_name}"}
    try:
        return func(**params, data=data)
    except TypeError as e:
        return {"error": f"Paramètres invalides pour {tool_name}: {e}"}


def answer_query(user_query: str, model: str | None = None) -> dict:
    """
    Pipeline complet RAG :
      1. LLM choisit l'outil + paramètres (tool calling)
      2. Exécution de l'outil sur les données réelles (SA-data.xlsx)
      3. (Optionnel) LLM reformule la réponse en langage naturel
    """
    model = model or get_active_model()
    data = load_data()

    try:
        raw = call_llm(user_query, model)
        call = parse_tool_call(raw)
    except requests.exceptions.RequestException as e:
        call = None
        raw = f"(Ollama indisponible : {e})"

    if call is None:
        q = user_query.lower()
        if "prévi" in q or "prédi" in q or "prochain" in q or "demain" in q:
            result = forecast_visitors(data=data)
            tool_used = "forecast_visitors (fallback mots-clés)"
        elif "historique" in q or "évolution" in q or "tendance" in q or "derniers jours" in q or "dernière semaine" in q:
            result = get_visitor_history(data=data, n_days=7)
            tool_used = "get_visitor_history (fallback mots-clés)"
        elif "horaire" in q or "flux" in q or "heure" in q:
            result = get_hourly_visitor_flow(data=data)
            tool_used = "get_hourly_visitor_flow (fallback mots-clés)"
        elif "visiteur" in q or "visite" in q:
            result = get_visitor_count(data=data)
            tool_used = "get_visitor_count (fallback mots-clés)"
        else:
            # Question générale -> fallback sémantique sur la base vectorielle
            result = _search_kb_tool(user_query)
            tool_used = "search_knowledge_base (fallback sémantique)"
        return {"tool_used": tool_used, "llm_raw": raw, "result": result, "model": model}

    result = run_tool(call, data)
    return {"tool_used": call.get("tool"), "parameters": call.get("parameters"),
            "llm_raw": raw, "result": result, "model": model}


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "Combien de visiteurs hier dans le magasin ?"
    out = answer_query(query)
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))