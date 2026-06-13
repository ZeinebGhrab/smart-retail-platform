# ============================================================
# history/rag_pipeline.py — Pipeline RAG léger
#
# Pourquoi sans torch / chromadb / sentence-transformers ?
#   → torch seul = 532 MB téléchargés au build du conteneur
#   → la KB ne contient que 8 documents : ChromaDB inutile
#   → Ollama expose déjà /api/embeddings : on l'utilise !
#
# Architecture dans Docker :
#
#  [django_api]  ──HTTP──►  [ollama]
#    │                        llama3.2:3b-instruct-q4_K_M
#    │  1. _build_csv_context()   : lit /app/data/*.csv  (volume)
#    │  2. _retrieve_kb()         : embeddings via Ollama /api/embeddings
#    │                              cosine similarity en Python pur
#    │  3. _build_prompt()        : assemble contexte + question
#    │  4. _call_ollama()         : génération via /api/generate
#    └──────────────────────────────────────────────────────────
#
# Variables d'environnement (docker-compose.yml) :
#   OLLAMA_HOST        = http://ollama:11434
#   OLLAMA_MODEL       = llama3.2:3b-instruct-q4_K_M
#   VISITOR_DATA_CSV   = /app/data/shoppingclub_2025_2026.csv
# ============================================================

from __future__ import annotations

import json
import math
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import requests

# ── Chemins (volumes Docker) ──────────────────────────────────
DATA_CSV = Path(os.environ.get("VISITOR_DATA_CSV", "/app/data/shoppingclub_2025_2026.csv"))
KB_JSON  = Path("/app/dataset/knowledge_base.json")

OLLAMA_HOST  = os.environ.get("OLLAMA_HOST",  "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b-instruct-q4_K_M")

# ── Cache CSV ─────────────────────────────────────────────────
_df_cache: pd.DataFrame | None = None
_csv_mtime: float = 0.0


def _load_csv() -> pd.DataFrame:
    global _df_cache, _csv_mtime
    mtime = DATA_CSV.stat().st_mtime if DATA_CSV.exists() else 0.0
    if _df_cache is None or mtime != _csv_mtime:
        df = pd.read_csv(str(DATA_CSV))
        df["datetime_parsed"] = pd.to_datetime(df["datetime"], dayfirst=True, errors="coerce")
        df["date"]        = df["datetime_parsed"].dt.date.astype(str)
        df["hour"]        = df["datetime_parsed"].dt.hour
        df["camera_norm"] = df["camera"].str.lower().str.replace(" ", "_")
        _df_cache  = df
        _csv_mtime = mtime
    return _df_cache


# ── 1. RETRIEVAL CSV ──────────────────────────────────────────

def _build_csv_context(question: str) -> str:
    df    = _load_csv()
    q     = question.lower()
    date  = _extract_date(question)
    cam   = _extract_camera(question)
    ndays = _extract_n_days(question)
    lines: list[str] = []

    if date:
        sub = df[df["date"] == date]
        if cam:
            key = "porte1" if "nord" in cam.lower() else "porte2"
            sub = sub[sub["camera_norm"].str.contains(key, na=False)]
        if not sub.empty:
            lines.append(f"Données visiteurs du {date} :")
            lines.append(f"  Total : {int(sub['Visits'].sum())}")
            for c, v in sub.groupby("camera")["Visits"].sum().items():
                lines.append(f"  {c} : {int(v)}")
            for g, v in sub.groupby("gender")["Visits"].sum().items():
                lines.append(f"  Genre {g} : {int(v)}")
            for a, v in sub.groupby("age")["Visits"].sum().items():
                lines.append(f"  Tranche {a} : {int(v)}")
            by_h = sub.groupby("hour")["Visits"].sum().sort_values(ascending=False)
            lines.append("  Heures de pointe :")
            for h, v in by_h.head(5).items():
                lines.append(f"    {int(h):02d}h : {int(v)} visites")
        else:
            lines.append(f"Aucune donnée pour le {date}.")

    if any(k in q for k in ["historique", "derniers", "semaine", "mois", "évolution", "tendance"]):
        n      = ndays or 7
        recent = sorted(df["date"].unique())[-n:]
        sub    = df[df["date"].isin(recent)]
        daily  = sub.groupby("date")["Visits"].sum()
        lines.append(f"\nHistorique des {len(recent)} derniers jours :")
        for d, v in daily.items():
            lines.append(f"  {d} : {int(v)} visiteurs")
        lines.append(f"  Moyenne : {int(daily.mean())} visiteurs/jour")

    if not lines or any(k in q for k in ["résumé", "bilan", "total", "global"]):
        all_dates = sorted(df["date"].unique())
        lines.append(f"\nRésumé global :")
        lines.append(f"  Total visites : {int(df['Visits'].sum())}")
        lines.append(f"  Période : {all_dates[0]} → {all_dates[-1]}")
        for g, v in df.groupby("gender")["Visits"].sum().items():
            lines.append(f"  {g} : {int(v)}")

    return "\n".join(lines) if lines else "Données non disponibles."


# ── 2. RETRIEVAL KB — embeddings via Ollama (pas de torch) ───

# Cache des embeddings de la KB (calculés une seule fois au démarrage)
_kb_docs: list[dict] | None = None
_kb_embeddings: list[list[float]] | None = None


def _embed_ollama(text: str) -> list[float]:
    """Appelle /api/embeddings d'Ollama — pas besoin de sentence-transformers."""
    resp = requests.post(
        f"{OLLAMA_HOST}/api/embeddings",
        json={"model": OLLAMA_MODEL, "prompt": text},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def _cosine(a: list[float], b: list[float]) -> float:
    dot  = sum(x * y for x, y in zip(a, b))
    na   = math.sqrt(sum(x * x for x in a))
    nb   = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def _retrieve_kb(question: str, n_results: int = 2) -> str:
    """
    Recherche sémantique sur la KB (8 docs).
    Embeddings calculés via Ollama /api/embeddings → cosine similarity en Python pur.
    Résultat mis en cache : Ollama n'est appelé qu'une fois par doc au démarrage.
    """
    global _kb_docs, _kb_embeddings

    if not KB_JSON.exists():
        return "(knowledge_base.json introuvable)"

    # Chargement + embedding de la KB au premier appel
    if _kb_docs is None:
        with open(str(KB_JSON), encoding="utf-8") as f:
            _kb_docs = json.load(f)
        try:
            _kb_embeddings = [
                _embed_ollama(f"{d['title']} : {d['content']}")
                for d in _kb_docs
            ]
        except Exception:
            # Ollama pas encore prêt → fallback mots-clés
            _kb_embeddings = []

    # Fallback mots-clés si embeddings indisponibles
    if not _kb_embeddings:
        q_words = set(question.lower().split())
        scored  = sorted(
            _kb_docs,
            key=lambda d: sum(1 for w in q_words if w in (d["title"] + d["content"]).lower()),
            reverse=True,
        )
        return "\n".join(f"[{d['title']}] {d['content']}" for d in scored[:n_results])

    # Embedding de la question + cosine similarity
    try:
        q_emb  = _embed_ollama(question)
        scored = sorted(
            zip(_kb_embeddings, _kb_docs),
            key=lambda t: _cosine(t[0], q_emb),
            reverse=True,
        )
        return "\n".join(
            f"[{d['title']}] {d['content']}"
            for _, d in scored[:n_results]
        )
    except Exception:
        # Ollama temporairement indispo → mots-clés
        q_words = set(question.lower().split())
        scored2 = sorted(
            _kb_docs,
            key=lambda d: sum(1 for w in q_words if w in (d["title"] + d["content"]).lower()),
            reverse=True,
        )
        return "\n".join(f"[{d['title']}] {d['content']}" for d in scored2[:n_results])


# ── 3. PROMPT BUILDER ─────────────────────────────────────────

_SYSTEM = """\
Tu es l'assistant analytique d'Anavid Store 360.
Réponds UNIQUEMENT en français, de façon concise et structurée.
Utilise UNIQUEMENT les données du CONTEXTE ci-dessous.
Ne fabrique pas de chiffres. Formate avec des emojis et des tirets."""


def _build_prompt(question: str, csv_ctx: str, kb_ctx: str) -> str:
    return (
        f"{_SYSTEM}\n\n"
        f"=== DONNÉES VISITEURS (CSV) ===\n{csv_ctx}\n\n"
        f"=== BASE DE CONNAISSANCE (FAQ) ===\n{kb_ctx}\n\n"
        f"=== QUESTION ===\n{question}\n\n"
        f"=== RÉPONSE ==="
    )


# ── 4. LLM — Ollama /api/generate ────────────────────────────

def _call_ollama(prompt: str) -> str:
    resp = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model":  OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p":       0.9,
                "num_ctx":     4096,
                "num_predict": 1024,
            },
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


# ── 5. PIPELINE PRINCIPAL ─────────────────────────────────────

def run_rag_pipeline(question: str) -> dict[str, Any]:
    csv_ctx = _build_csv_context(question)
    kb_ctx  = _retrieve_kb(question)
    prompt  = _build_prompt(question, csv_ctx, kb_ctx)

    try:
        answer = _call_ollama(prompt)
    except requests.exceptions.ConnectionError:
        answer = (
            f"⚠️ Ollama non joignable ({OLLAMA_HOST}).\n"
            "Lancez : `docker compose up ollama`"
        )
    except requests.exceptions.Timeout:
        answer = "⚠️ Timeout : le modèle met trop de temps à répondre."
    except Exception as exc:
        answer = f"⚠️ Erreur LLM : {exc}"

    return {
        "answer":  answer,
        "model":   OLLAMA_MODEL,
        "sources": {
            "csv":      str(DATA_CSV),
            "kb":       str(KB_JSON),
            "embeddings": f"{OLLAMA_HOST}/api/embeddings",
        },
    }


# ── Helpers ───────────────────────────────────────────────────

def _extract_date(text: str) -> str | None:
    m = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
    if m:
        return m.group(1)
    m = re.search(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', text)
    if m:
        return f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
    q = text.lower()
    t = datetime.today()
    if "hier" in q:
        return (t - timedelta(days=1)).strftime("%Y-%m-%d")
    if "aujourd" in q:
        return t.strftime("%Y-%m-%d")
    return None


def _extract_camera(text: str) -> str | None:
    t = text.lower()
    if "nord" in t: return "Porte_nord"
    if "sud"  in t: return "Porte_sud"
    return None


def _extract_n_days(text: str) -> int | None:
    m = re.search(r'(\d+)\s*(jours?|semaines?)', text.lower())
    if m:
        n = int(m.group(1))
        return n * 7 if "semaine" in m.group(2) else n
    if "semaine" in text.lower(): return 7
    if "mois"    in text.lower(): return 30
    return None