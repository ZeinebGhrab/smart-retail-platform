# ============================================================
# history/chatbot/rag_pipeline.py — Pipeline RAG léger
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

# URL du service FastAPI ML (visitor_ml_api dans docker-compose)
ML_API_HOST  = os.environ.get("ML_API_HOST", "http://visitor-ml-api:8000")

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
        df["gender"]      = df["gender"].map(_normalize_gender)
        df["age"]         = df["age"].map(_normalize_age)
        _df_cache  = df
        _csv_mtime = mtime
    return _df_cache


# ── Normalisation des catégories (le CSV contient des labels
#    incohérents selon la source d'export : "Female"/"WOMEN",
#    "0-9"/"age_0-9"/"age_0_9"/"Enfants", etc.) ──────────────

_GENDER_MAP = {
    "female": "Femme",
    "women":  "Femme",
    "male":   "Homme",
    "men":    "Homme",
}


def _normalize_gender(value: str) -> str:
    return _GENDER_MAP.get(str(value).strip().lower(), str(value).strip())


# Mappe toutes les variantes vers une tranche d'âge canonique
_AGE_MAP = {
    "0-9":          "0-9 ans",
    "age_0-9":      "0-9 ans",
    "age_0_9":      "0-9 ans",
    "enfants":      "0-9 ans",
    "10-17":        "10-17 ans",
    "age_10-17":    "10-17 ans",
    "age_10_17":    "10-17 ans",
    "adolescents":  "10-17 ans",
    "18-29":        "18-29 ans",
    "age_18-29":    "18-29 ans",
    "age_18_29":    "18-29 ans",
    "30-39":        "30-39 ans",
    "40-49":        "40-49 ans",
    "adultes":      "18-49 ans",
    "60-100":       "60+ ans",
    "age_60-100":   "60+ ans",
    "age_60_100":   "60+ ans",
    "seniors":      "60+ ans",
}


def _normalize_age(value: str) -> str:
    key = str(value).strip().lower()
    return _AGE_MAP.get(key, str(value).strip())


# Mappe le nom technique de la caméra (colonne "camera" du CSV, ex.
# "Cam porte1"/"Cam_porte2") vers le nom utilisé par les utilisateurs
# et la KB ("Porte_nord"/"Porte_sud"), pour que le LLM fasse le lien
# entre la question ("Porte_nord") et les données du contexte.
def _camera_label(camera_raw: str) -> str:
    c = str(camera_raw).lower().replace(" ", "_")
    if "porte1" in c:
        return "Porte_nord (Cam porte1)"
    if "porte2" in c:
        return "Porte_sud (Cam_porte2)"
    return str(camera_raw)


# ── 1. RETRIEVAL CSV ──────────────────────────────────────────

def _build_csv_context(question: str) -> str:
    df    = _load_csv()
    q     = question.lower()

    # "hier"/"aujourd'hui" sont calculés par rapport à la DERNIÈRE date
    # disponible dans le CSV (et non la date réelle du jour), car le
    # jeu de données est historique et peut s'arrêter avant aujourd'hui.
    last_available = sorted(df["date"].unique())[-1]
    reference_date = datetime.strptime(last_available, "%Y-%m-%d")

    date  = _extract_date(question, reference_date=reference_date)
    cam   = _extract_camera(question)
    ndays = _extract_n_days(question)
    lines: list[str] = []

    is_relative_date = bool(re.search(r'\bhier\b|\baujourd', q)) and not re.search(r'\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{4}', question)

    if date:
        sub = df[df["date"] == date]
        if cam:
            key = "porte1" if "nord" in cam.lower() else "porte2"
            sub = sub[sub["camera_norm"].str.contains(key, na=False)]
        if not sub.empty:
            if is_relative_date:
                label = "hier" if "hier" in q else "aujourd'hui"
                lines.append(f"Données enregistrées du {date} ({label}, visites indiquées par caméra) :")
            else:
                lines.append(f"Données enregistrées du {date} (visites indiquées par caméra) :")
            if cam:
                lines.append(f"  (Filtré sur la caméra {cam})")
            lines.append(f"  Total : {int(sub['Visits'].sum())}")
            for c, v in sub.groupby("camera")["Visits"].sum().items():
                lines.append(f"  {_camera_label(c)} : {int(v)}")
            for g, v in sub.groupby("gender")["Visits"].sum().items():
                lines.append(f"  Genre {g} : {int(v)}")
            for a, v in sub.groupby("age")["Visits"].sum().items():
                lines.append(f"  Tranche {a} : {int(v)}")
            by_h = sub.groupby("hour")["Visits"].sum().sort_values(ascending=False)
            lines.append("  Heures de pointe :")
            for h, v in by_h.head(5).items():
                lines.append(f"    {int(h):02d}h : {int(v)} visites")
        elif is_relative_date:
            # "hier"/"aujourd'hui" sans données (ex: caméra absente ce jour-là)
            # → on retombe sur le jour le plus récent disponible plutôt que
            # de répondre "aucune donnée", ce qui induirait le LLM en erreur.
            fallback_sub = df[df["date"] == last_available]
            if cam:
                fallback_sub = fallback_sub[fallback_sub["camera_norm"].str.contains(key, na=False)]
            if not fallback_sub.empty:
                lines.append(
                    f"Aucune donnée pour le {date} (\"{('hier' if 'hier' in q else 'aujourd hui')}\"). "
                    f"Dernières données disponibles : {last_available} :"
                )
                lines.append(f"  Total : {int(fallback_sub['Visits'].sum())}")
                for c, v in fallback_sub.groupby("camera")["Visits"].sum().items():
                    lines.append(f"  {_camera_label(c)} : {int(v)}")
            else:
                lines.append(f"Aucune donnée pour le {date}. Dernière date disponible dans les données : {last_available}.")
        else:
            lines.append(f"Aucune donnée pour le {date}. Dernière date disponible dans les données : {last_available}.")

    if any(k in q for k in ["historique", "derniers", "semaine", "mois", "évolution", "tendance"]):
        n      = ndays or 7
        recent = sorted(df["date"].unique())[-n:]
        sub    = df[df["date"].isin(recent)]
        daily  = sub.groupby("date")["Visits"].sum()
        lines.append(f"\nHistorique des {len(recent)} derniers jours (présente le nombre de visiteurs par jour) :")
        for d, v in daily.items():
            lines.append(f"  {d} : {int(v)} visiteurs")
        lines.append(f"  Moyenne journalière : {int(daily.mean())} visiteurs/jour")

    if not lines or any(k in q for k in ["résumé", "bilan", "total", "global"]):
        all_dates = sorted(df["date"].unique())
        lines.append(f"\nRésumé global :")
        lines.append(f"  Total visites : {int(df['Visits'].sum())}")
        lines.append(f"  Période couverte : {all_dates[0]} → {all_dates[-1]}")
        lines.append(f"  Répartition par genre :")
        for g, v in df.groupby("gender")["Visits"].sum().items():
            lines.append(f"    {g} : {int(v)}")
        lines.append(f"  Répartition par tranche d'âge :")
        for a, v in df.groupby("age")["Visits"].sum().items():
            lines.append(f"    {a} : {int(v)}")

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


def _retrieve_kb(question: str, n_results: int = 2, min_sim: float = 0.45) -> str:
    """
    Recherche sémantique sur la KB (8 docs).
    Embeddings calculés via Ollama /api/embeddings → cosine similarity en Python pur.
    Résultat mis en cache : Ollama n'est appelé qu'une fois par doc au démarrage.

    Un seuil minimal de similarité (`min_sim`) est appliqué : on ne retient
    un doc que s'il est suffisamment proche de la question. Cela évite de
    toujours injecter `n_results` documents (souvent du bruit) quand un seul
    (ou zéro) document est réellement pertinent.
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
        top = [d for d in scored[:n_results]
               if sum(1 for w in q_words if w in (d["title"] + d["content"]).lower()) > 0]
        if not top:
            return ""
        return "\n".join(f"[{d['title']}] {d['content']}" for d in top)

    # Embedding de la question + cosine similarity
    try:
        q_emb  = _embed_ollama(question)
        scored = sorted(
            zip(_kb_embeddings, _kb_docs),
            key=lambda t: _cosine(t[0], q_emb),
            reverse=True,
        )
        top = [(sim, d) for (emb, d) in scored[:n_results]
               for sim in (_cosine(emb, q_emb),)
               if sim >= min_sim]
        if not top:
            return ""
        return "\n".join(
            f"[{d['title']}] {d['content']}"
            for _, d in top
        )
    except Exception:
        # Ollama temporairement indispo → mots-clés
        q_words = set(question.lower().split())
        scored2 = sorted(
            _kb_docs,
            key=lambda d: sum(1 for w in q_words if w in (d["title"] + d["content"]).lower()),
            reverse=True,
        )
        top2 = [d for d in scored2[:n_results]
                if sum(1 for w in q_words if w in (d["title"] + d["content"]).lower()) > 0]
        if not top2:
            return ""
        return "\n".join(f"[{d['title']}] {d['content']}" for d in top2)


# ── 2b. ML PREDICTION — FastAPI visitor_ml_api ────────────────

# Prompt de classification sémantique (envoyé à Ollama avant le pipeline principal).
# Conçu pour être court et résistant aux fautes d'orthographe / formulations libres.
_CLASSIFY_PROMPT = """\
Tu es un classificateur. Réponds UNIQUEMENT par un seul mot : FUTUR ou PASSE.

La question porte-t-elle sur le nombre de visiteurs à venir (futur, prévision, demain, \
semaine prochaine, etc.) ou sur des données déjà enregistrées (passé, hier, bilan, historique) ?

Règle : si la question mentionne une date ou période FUTURE, réponds FUTUR.
Si elle porte sur des données déjà connues ou passées, réponds PASSE.
Si aucun des deux n'est clair, réponds PASSE.

Question : {question}
Réponse :"""


def _classify_intent_llm(question: str) -> str:
    """
    Appelle Ollama avec un micro-prompt de classification pour détecter
    si la question porte sur des visiteurs futurs (ML) ou passés (RAG CSV).

    Retourne "FUTUR" ou "PASSE".
    Résistant aux fautes d'orthographe et aux formulations inhabituelles.
    Timeout court (10 s) pour ne pas pénaliser la latence.
    """
    today_str = datetime.today().strftime("%Y-%m-%d")
    prompt = _CLASSIFY_PROMPT.format(question=question) + f"\n(Date du jour : {today_str})"
    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model":  OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0,   # déterministe
                    "num_predict": 4,     # on attend 1 mot : FUTUR ou PASSE
                    "seed": 0,
                },
            },
            timeout=10,
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "").strip().upper()
        # Tolérance : "FUTUR", "FUTURE", "FUTUR.", "ML", "AVENIR" → FUTUR
        if any(tok in raw for tok in ("FUTUR", "FUTURE", "AVENIR", "ML", "PREVI")):
            return "FUTUR"
        return "PASSE"
    except Exception:
        # Si Ollama est lent ou indispo lors de la classification, on tombe
        # sur le fallback par date ci-dessous (voir _is_future_prediction_query).
        return "UNKNOWN"


def _is_future_prediction_query(question: str) -> bool:
    """
    Détermine si la question porte sur des visiteurs FUTURS (→ ML)
    ou sur les données historiques (→ RAG CSV).

    Stratégie à deux niveaux :
      1. Date explicite dans la question : décision 100 % fiable par comparaison
         calendaire, sans appel LLM (cas le plus fréquent en pratique).
      2. Sinon → classification sémantique par Ollama (résistante aux fautes,
         aux formulations libres, aux langues mélangées).
         Si Ollama est indisponible → défaut PASSE (comportement conservateur).
    """
    today = datetime.today()

    # ── Niveau 1 : date explicite → décision calendaire ──────────
    for pattern, fmt in [
        (r'\b(\d{4}-\d{2}-\d{2})\b', "%Y-%m-%d"),
        (r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', None),
    ]:
        for m in re.finditer(pattern, question):
            try:
                if fmt:
                    d = datetime.strptime(m.group(1), fmt)
                else:
                    day, month, year = m.group(1), m.group(2), m.group(3)
                    d = datetime(int(year), int(month), int(day))
                return d.date() > today.date()
            except ValueError:
                pass

    # ── Niveau 2 : classification sémantique par LLM ─────────────
    intent = _classify_intent_llm(question)
    if intent == "FUTUR":
        return True
    # "PASSE" ou "UNKNOWN" (Ollama indispo) → mode RAG CSV par défaut
    return False



def _extract_future_dates(text: str) -> list[str]:
    """
    Extrait les dates futures mentionnées dans la question.
    Retourne une liste de dates au format YYYY-MM-DD.
    Gère aussi les références relatives : "demain", "semaine prochaine".
    """
    today = datetime.today()
    dates: list[str] = []

    # Dates explicites
    for m in re.finditer(r'\b(\d{4}-\d{2}-\d{2})\b', text):
        try:
            d = datetime.strptime(m.group(1), "%Y-%m-%d")
            if d.date() >= today.date():
                dates.append(m.group(1))
        except ValueError:
            pass

    for m in re.finditer(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', text):
        try:
            d = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            if d.date() >= today.date():
                dates.append(d.strftime("%Y-%m-%d"))
        except ValueError:
            pass

    # Références relatives
    t = text.lower()
    if "demain" in t:
        dates.append((today + timedelta(days=1)).strftime("%Y-%m-%d"))

    if "semaine prochaine" in t:
        # Lundi de la semaine prochaine → dimanche (7 jours)
        next_monday = today + timedelta(days=(7 - today.weekday()))
        for i in range(7):
            dates.append((next_monday + timedelta(days=i)).strftime("%Y-%m-%d"))

    if "mois prochain" in t:
        # Premier jour du mois suivant
        if today.month == 12:
            first_next = datetime(today.year + 1, 1, 1)
        else:
            first_next = datetime(today.year, today.month + 1, 1)
        # 7 premiers jours du mois prochain
        for i in range(7):
            dates.append((first_next + timedelta(days=i)).strftime("%Y-%m-%d"))

    # Dédupliquer tout en conservant l'ordre
    seen: set[str] = set()
    result: list[str] = []
    for d in dates:
        if d not in seen:
            seen.add(d)
            result.append(d)

    # Si aucune date trouvée → demain par défaut
    if not result:
        result.append((today + timedelta(days=1)).strftime("%Y-%m-%d"))

    return result[:14]  # Max 14 jours pour éviter trop d'appels ML


# Coordonnées Sfax (identiques au workflow n8n)
_SFAX_LAT = 34.7406
_SFAX_LON = 10.7603

# Cache météo : évite de rappeler Open-Meteo pour la même date dans la même requête
_weather_cache: dict[str, dict] = {}

# Cache jours fériés Tunisie par année
_holiday_cache: dict[int, set[str]] = {}


def _fetch_weather(date_str: str) -> dict:
    """
    Récupère les prévisions météo pour une date future via Open-Meteo.
    Utilise /forecast avec daily (temperature_2m_max, wind_speed_10m_max)
    pour couvrir les dates à venir (jusqu'à ~16 jours).

    Retourne : {"temperature": float, "wind_speed": float, "source": str}
    Fallback Sfax été si Open-Meteo est inaccessible ou date hors horizon.
    """
    if date_str in _weather_cache:
        return _weather_cache[date_str]

    fallback = {"temperature": 32.0, "wind_speed": 15.0, "source": "fallback_sfax"}

    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude":          _SFAX_LAT,
                "longitude":         _SFAX_LON,
                "daily":             "temperature_2m_max,wind_speed_10m_max",
                "timezone":          "Africa/Tunis",
                "start_date":        date_str,
                "end_date":          date_str,
                "forecast_days":     16,
            },
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()

        daily = data.get("daily", {})
        temps = daily.get("temperature_2m_max", [])
        winds = daily.get("wind_speed_10m_max", [])

        if temps and winds and temps[0] is not None:
            result = {
                "temperature": round(float(temps[0]), 1),
                "wind_speed":  round(float(winds[0] if winds[0] is not None else 15.0), 1),
                "source":      "open-meteo",
            }
            _weather_cache[date_str] = result
            return result

    except Exception:
        pass

    _weather_cache[date_str] = fallback
    return fallback


def _fetch_holidays_tn(year: int) -> set[str]:
    """
    Récupère la liste des jours fériés tunisiens pour une année via Nager.Date.
    Retourne un set de dates YYYY-MM-DD.
    Résultat mis en cache par année.
    """
    if year in _holiday_cache:
        return _holiday_cache[year]

    try:
        resp = requests.get(
            f"https://date.nager.at/api/v3/PublicHolidays/{year}/TN",
            timeout=8,
        )
        if resp.status_code == 200:
            holidays = {h["date"] for h in resp.json() if "date" in h}
            _holiday_cache[year] = holidays
            return holidays
    except Exception:
        pass

    _holiday_cache[year] = set()
    return set()


def _get_type_jour(date_str: str) -> tuple[str, str]:
    """
    Détermine le type du jour (normal / ferie) pour une date donnée.
    Retourne (type_jour, label_fr) — ex: ("ferie", "jour férié").
    """
    year = int(date_str[:4])
    holidays = _fetch_holidays_tn(year)
    if date_str in holidays:
        return "ferie", "jour férié 🎉"
    return "normal", "jour normal"


def _fetch_ml_prediction(date_str: str) -> dict:
    """
    Enrichit la date avec météo + statut férié, puis appelle
    POST /predict sur la FastAPI ML (LightGBM).

    Retourne un dict contenant :
      - "date", "total_daily", "temperature", "wind_speed",
        "type_jour", "type_jour_label", "weather_source"
      - "error" en cas d'échec
    """
    # ── 1. Enrichissement météo ──────────────────────────────────
    weather   = _fetch_weather(date_str)
    temperature = weather["temperature"]
    wind_speed  = weather["wind_speed"]
    weather_src = weather["source"]

    # ── 2. Statut jour férié ────────────────────────────────────
    type_jour, type_jour_label = _get_type_jour(date_str)

    # ── 3. Appel FastAPI ML ─────────────────────────────────────
    try:
        resp = requests.post(
            f"{ML_API_HOST}/predict",
            json={
                "date":        date_str,
                "temperature": temperature,
                "wind_speed":  wind_speed,
                "type_jour":   type_jour,
            },
            timeout=20,
        )
        resp.raise_for_status()
        ml_data = resp.json()

        # Calcul du total journalier depuis la liste de prédictions horaires
        predictions = ml_data.get("predictions", [])
        # Chaque entrée = (hour, camera) → on déduplique par heure
        # (summe des 2 caméras pour avoir le total par heure, puis total jour)
        seen_hours: dict[int, int] = {}
        for p in predictions:
            h = p.get("hour", 0)
            v = p.get("total_visits", 0)
            seen_hours[h] = seen_hours.get(h, 0) + v
        total_daily = sum(seen_hours.values())

        return {
            "date":             date_str,
            "total_daily":      total_daily,
            "temperature":      temperature,
            "wind_speed":       wind_speed,
            "type_jour":        type_jour,
            "type_jour_label":  type_jour_label,
            "weather_source":   weather_src,
            "raw":              ml_data,   # pour debug éventuel
        }

    except requests.exceptions.ConnectionError:
        return {"error": f"ML API non joignable ({ML_API_HOST})", "date": date_str}
    except requests.exceptions.Timeout:
        return {"error": "ML API timeout (>20 s)", "date": date_str}
    except requests.exceptions.HTTPError as exc:
        return {"error": f"ML API HTTP {getattr(exc.response,'status_code','?')}", "date": date_str}
    except Exception as exc:
        return {"error": str(exc), "date": date_str}


def _build_ml_context(question: str) -> str:
    """
    Construit le bloc de contexte ML complet à injecter dans le prompt Ollama.

    Pour chaque date future détectée dans la question :
      1. Récupère la météo prévue (Open-Meteo, Sfax)
      2. Vérifie si c'est un jour férié tunisien (Nager.Date)
      3. Appelle la FastAPI ML avec ces features
      4. Formate le résultat pour le LLM

    En cas d'indisponibilité d'Open-Meteo ou Nager, des valeurs de fallback
    sont utilisées (la prédiction ML reste possible, moins précise).
    """
    dates = _extract_future_dates(question)
    lines: list[str] = ["=== PRÉVISIONS ML (LightGBM — features météo + calendrier) ==="]

    any_success = False
    for date_str in dates:
        result = _fetch_ml_prediction(date_str)

        if "error" in result:
            lines.append(f"  {date_str} : ⚠️ {result['error']}")
            continue

        any_success = True
        total     = result["total_daily"]
        temp      = result["temperature"]
        wind      = result["wind_speed"]
        tj_label  = result["type_jour_label"]
        wsrc      = result["weather_source"]

        # Ligne principale
        lines.append(f"  {date_str} : {total} visiteurs prévus")

        # Détail des features utilisées (transparence pour le LLM)
        meteo_note = f"météo {'prévue' if wsrc == 'open-meteo' else 'estimée (fallback)'}"
        lines.append(f"    └─ {tj_label} | {meteo_note} : {temp}°C, vent {wind} km/h")

    if not any_success:
        lines.append("  ⚠️ Aucune prédiction ML disponible pour les dates demandées.")

    lines.append(
        "\nNote : prévisions basées sur les données historiques, la météo Open-Meteo "
        "et les jours fériés tunisiens (Nager.Date). Il s'agit d'estimations."
    )
    return "\n".join(lines)




_SYSTEM = """\
Tu es l'assistant analytique d'Anavid Store 360.

RÈGLES ABSOLUES — RESPECTER IMPÉRATIVEMENT :
1. Réponds UNIQUEMENT en français, de façon concise et directe.
2. Utilise UNIQUEMENT les informations présentes dans le CONTEXTE fourni ci-dessous.
3. NE JAMAIS inventer, deviner ou extrapoler des chiffres, des faits ou des données.
4. Si une information n'est pas dans le contexte, réponds exactement : "Je n'ai pas cette information dans les données disponibles."
5. Cite toujours la source de l'information (ex: "selon les données CSV...", "d'après la base de connaissance...").
6. Quand des prévisions ML sont disponibles, précise toujours qu'il s'agit d'estimations.
7. Formate la réponse avec des emojis et des tirets pour la lisibilité.
8. Reste strictement fidèle aux données : ne paraphrase pas en introduisant des inexactitudes."""


def _build_prompt(question: str, csv_ctx: str, kb_ctx: str, history: str = "", ml_ctx: str = "") -> str:
    history_block = f"=== HISTORIQUE DE LA CONVERSATION ===\n{history}\n\n" if history else ""
    kb_block  = f"=== BASE DE CONNAISSANCE (FAQ) ===\n{kb_ctx}\n\n" if kb_ctx else ""
    ml_block  = f"{ml_ctx}\n\n" if ml_ctx else ""
    csv_block = f"=== DONNÉES VISITEURS HISTORIQUES (CSV) ===\n{csv_ctx}\n\n" if csv_ctx and csv_ctx != "Données non disponibles." else ""
    return (
        f"{_SYSTEM}\n\n"
        f"{ml_block}"
        f"{csv_block}"
        f"{kb_block}"
        f"{history_block}"
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
                "temperature": 0.0,  # déterministe pour maximiser la faithfulness
                "top_p":       0.9,
                "num_ctx":     4096,
                "num_predict": 1024,
                "seed":        42,
            },
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


# ── 5. PIPELINE PRINCIPAL ─────────────────────────────────────

def run_rag_pipeline(question: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    """
    Pipeline principal du chatbot.

    Deux modes de fonctionnement selon la nature de la question :

    1. Question sur les données PASSÉES → RAG classique (CSV + KB + Ollama)
    2. Question sur des visiteurs FUTURS → Appel FastAPI ML + Ollama pour formuler

    Args:
        question : question courante de l'utilisateur.
        history  : liste d'échanges précédents, format
                   [{"role": "user"|"assistant", "content": "..."}].
                   Utilisé pour donner au LLM le contexte de la conversation
                   (ex: "Et hier ?" après "Combien de visiteurs aujourd'hui ?").
                   Limité aux N derniers échanges pour rester dans num_ctx.
    """
    history = history or []

    # On ne garde que les derniers échanges pour limiter la taille du prompt
    recent_history = history[-6:]
    history_text = "\n".join(
        f"{'Utilisateur' if h.get('role') == 'user' else 'Assistant'} : {h.get('content', '')}"
        for h in recent_history
        if h.get("content")
    )

    # La requête utilisée pour le retrieval combine la question courante
    # avec le dernier message utilisateur de l'historique, pour résoudre
    # les questions de suivi elliptiques (ex: "Et demain ?").
    last_user_turns = [h["content"] for h in recent_history if h.get("role") == "user" and h.get("content")]
    retrieval_query = " ".join(last_user_turns[-1:] + [question]) if last_user_turns else question

    # ── Détection : question future → ML, question passée → RAG CSV ──
    is_future = _is_future_prediction_query(retrieval_query)

    if is_future:
        # Mode ML : on appelle la FastAPI, pas besoin du CSV historique
        ml_ctx  = _build_ml_context(retrieval_query)
        # La KB peut apporter du contexte sur le modèle de prévision
        kb_ctx  = _retrieve_kb(retrieval_query)
        csv_ctx = ""  # pas de données passées nécessaires pour une prévision
        mode    = "ml_prediction"
    else:
        # Mode RAG classique : CSV + KB
        ml_ctx  = ""
        csv_ctx = _build_csv_context(retrieval_query)
        kb_ctx  = "" if _is_pure_data_query(retrieval_query) else _retrieve_kb(retrieval_query)
        mode    = "rag"

    prompt = _build_prompt(question, csv_ctx, kb_ctx, history=history_text, ml_ctx=ml_ctx)

    try:
        answer = _call_ollama(prompt)
    except requests.exceptions.ConnectionError:
        answer = (
            f"⚠️ Ollama non joignable ({OLLAMA_HOST}).\n"
            "Lancez : `docker compose up ollama`"
        )
    except requests.exceptions.Timeout:
        answer = "⚠️ Timeout : le modèle met trop de temps à répondre."
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 500:
            answer = (
                f"⚠️ Modèle '{OLLAMA_MODEL}' non disponible dans Ollama.\n"
                f"Exécutez : `docker exec shop-anavid-int-ollama ollama pull {OLLAMA_MODEL}`\n"
                f"Puis relancez votre question."
            )
        else:
            answer = f"⚠️ Erreur Ollama HTTP {getattr(exc.response, 'status_code', '?')} : {exc}"
    except Exception as exc:
        answer = f"⚠️ Erreur LLM : {exc}"

    return {
        "answer":  answer,
        "model":   OLLAMA_MODEL,
        "mode":    mode,        # "rag" ou "ml_prediction" — utile pour le frontend/debug
        "sources": {
            "csv":        str(DATA_CSV) if not is_future else None,
            "ml_api":     f"{ML_API_HOST}/predict" if is_future else None,
            "kb":         str(KB_JSON),
            "embeddings": f"{OLLAMA_HOST}/api/embeddings",
        },
    }



# ── Helpers ───────────────────────────────────────────────────

def _extract_date(text: str, reference_date: datetime | None = None) -> str | None:
    """
    Extrait une date de la question.

    Pour "hier"/"aujourd'hui", la date est calculée relativement à
    `reference_date` (par défaut : aujourd'hui réel). Comme le CSV
    contient des données historiques (qui peuvent s'arrêter avant la
    date réelle), le pipeline doit passer la DERNIÈRE date disponible
    dans le CSV comme `reference_date`, pour que "hier"/"aujourd'hui"
    pointent vers des données qui existent réellement.
    """
    m = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
    if m:
        return m.group(1)
    m = re.search(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', text)
    if m:
        return f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
    q = text.lower()
    t = reference_date or datetime.today()
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


def _is_pure_data_query(text: str) -> bool:
    """
    Détecte les questions qui portent uniquement sur les données
    visiteurs (CSV) : date précise, bilan/résumé global, historique.

    Pour ces questions, _retrieve_kb() n'apporte généralement aucune
    information utile (la KB est une FAQ thématique, pas une source de
    chiffres) — son seul effet est d'ajouter du bruit dans le contexte
    et de pénaliser Context Precision/Recall. On la désactive donc dans
    ce cas, sauf si la question contient aussi un mot-clé FAQ explicite
    (ex: "politique", "procédure", "définition") ou une caméra nommée
    (ex: "Porte_nord"), où la KB reste utile pour le contexte.
    """
    t = text.lower()

    has_date = bool(re.search(r'\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{4}', text)) \
        or "hier" in t or "aujourd" in t
    has_summary_kw = any(k in t for k in
        ["bilan", "résumé global", "résumé", "historique", "derniers jours",
         "évolution", "tendance"])
    mentions_visitors = "visiteur" in t or "visite" in t
    mentions_camera = "porte_nord" in t or "porte_sud" in t or "porte nord" in t or "porte sud" in t

    # Mots-clés indiquant une vraie question FAQ (KB) malgré la présence
    # d'un mot lié aux données — on garde alors la KB active.
    has_faq_kw = any(k in t for k in
        ["politique", "procédure", "confidentialité", "définition",
         "caméras de comptage", "installé", "conversion", "panier",
         "stock", "limite", "modèle de prévision"])

    is_data_topic = (has_date or has_summary_kw) and (mentions_visitors or has_summary_kw)

    return is_data_topic and not has_faq_kw and not mentions_camera