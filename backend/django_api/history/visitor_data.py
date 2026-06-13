# ============================================================
# history/visitor_data.py — Chargement & analyse des données visiteurs
# Source : data/shoppingclub_2025_2026.csv (chemin configurable via
#          la variable d'environnement VISITOR_DATA_CSV / settings.VISITOR_DATA_CSV)
# ============================================================
#
# Fournit :
#   - load_data()                      -> dict avec les DataFrames per_day / per_hour
#   - get_visitor_count(date, camera)  -> nb visiteurs pour une date/caméra
#   - get_hourly_visitor_flow(date)    -> flux horaire (toutes caméras)
#   - forecast_visitors(...)           -> prédiction (régression linéaire sur historique)
#   - list_cameras()                   -> liste des caméras disponibles
#   - get_summary()                    -> KPIs globaux (période, totaux, etc.)
#
# Le résultat de load_data() est mis en cache en mémoire et rechargé
# automatiquement si le fichier CSV est modifié (mtime).
# ============================================================

from __future__ import annotations

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import timedelta

from django.conf import settings

DATA_PATH = Path(settings.VISITOR_DATA_CSV)

# Mapping caméras CSV -> noms normalisés
_CAMERA_MAP = {
    "cam porte1": "Porte_nord",
    "cam_porte1": "Porte_nord",
    "cam porte2": "Porte_sud",
    "cam_porte2": "Porte_sud",
}


def _norm_gender(g: str) -> str:
    g = str(g).strip().lower()
    if g in ("men", "male", "m"):
        return "men"
    if g in ("women", "female", "f"):
        return "women"
    return g


_AGE_LABELS = {
    "0-9": "age_0_9",
    "age_0-9": "age_0_9",
    "age_0_9": "age_0_9",
    "10-17": "age_10_17",
    "age_10-17": "age_10_17",
    "age_10_17": "age_10_17",
    "adolescents": "age_10_17",
    "18-29": "age_18_29",
    "age_18-29": "age_18_29",
    "age_18_29": "age_18_29",
    "adultes": "age_18_29",
    "30-39": "age_30_39",
    "age_30-39": "age_30_39",
    "age_30_39": "age_30_39",
    "40-49": "age_40_49",
    "age_40-49": "age_40_49",
    "age_40_49": "age_40_49",
    "60-100": "age_60_100",
    "age_60-100": "age_60_100",
    "age_60_100": "age_60_100",
    "seniors": "age_60_100",
    "enfants": "age_0_9",
}


def _norm_age(a: str) -> str:
    return _AGE_LABELS.get(str(a).strip().lower(), str(a).strip().lower())


# ------------------------------------------------------------
# Cache en mémoire (rechargement si le CSV change)
# ------------------------------------------------------------
_CACHE: dict = {"mtime": None, "data": None}


def load_data(path: str | Path = DATA_PATH, force_reload: bool = False) -> dict[str, pd.DataFrame]:
    """
    Charge et normalise le CSV de visites.

    Retourne un dict avec deux DataFrames :
      - "per_day"  : une ligne par (date, camera) avec totaux et ventilation
      - "per_hour" : une ligne par (date, camera, hour) avec le compte horaire

    Le résultat est mis en cache et rechargé automatiquement si le
    fichier a été modifié depuis le dernier chargement.
    """
    path = Path(path)
    mtime = path.stat().st_mtime if path.exists() else None

    if not force_reload and _CACHE["data"] is not None and _CACHE["mtime"] == mtime:
        return _CACHE["data"]

    df = pd.read_csv(path)

    # --- Normalisation de base ---
    df["dt"] = pd.to_datetime(df["datetime"], dayfirst=True)
    df["date"] = df["dt"].dt.date
    df["hour"] = df["dt"].dt.hour
    df["camera"] = (
        df["camera"].str.strip().str.lower().map(lambda x: _CAMERA_MAP.get(x, x))
    )
    df["gender"] = df["gender"].map(_norm_gender)
    df["age"] = df["age"].map(_norm_age)
    df["count"] = df["Visits"].fillna(0).astype(int)

    # --- per_hour : agrégat (date, camera, hour) ---
    per_hour = df.groupby(["date", "camera", "hour"], as_index=False)["count"].sum()

    # --- per_day : agrégat (date, camera) + pivot genre + pivot âge ---
    base = (
        df.groupby(["date", "camera"], as_index=False)["count"]
        .sum()
        .rename(columns={"count": "visit_Count"})
    )

    gender_piv = (
        df.groupby(["date", "camera", "gender"])["count"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )
    gender_piv.columns.name = None
    gender_piv = gender_piv.rename(columns={"men": "gender_men", "women": "gender_women"})

    age_piv = (
        df.groupby(["date", "camera", "age"])["count"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )
    age_piv.columns.name = None

    _adult_cols = [c for c in age_piv.columns if c in ("age_18_29", "age_30_39", "age_40_49")]
    if _adult_cols:
        age_piv["age_adult"] = age_piv[_adult_cols].sum(axis=1)
        age_piv = age_piv.drop(columns=_adult_cols)
    for old, new in [("age_0_9", "age_child"), ("age_10_17", "age_teenager"), ("age_60_100", "age_senior")]:
        if old in age_piv.columns:
            age_piv = age_piv.rename(columns={old: new})

    per_day = base.merge(gender_piv, on=["date", "camera"], how="left").merge(
        age_piv, on=["date", "camera"], how="left"
    )

    for col in ["gender_men", "gender_women", "age_child", "age_teenager", "age_adult", "age_senior"]:
        if col not in per_day.columns:
            per_day[col] = 0
        per_day[col] = per_day[col].fillna(0).astype(int)

    result = {"per_day": per_day, "per_hour": per_hour}
    _CACHE["mtime"] = mtime
    _CACHE["data"] = result
    return result


# ------------------------------------------------------------
# Requêtes
# ------------------------------------------------------------

def list_cameras(data: dict | None = None) -> list[str]:
    data = data or load_data()
    return sorted(data["per_day"]["camera"].unique().tolist())


def get_visitor_history(
    start_date: str | None = None,
    end_date: str | None = None,
    camera: str | None = None,
    data: dict | None = None,
) -> dict:
    """
    Historique journalier des visiteurs (analytics).

    - start_date / end_date : "YYYY-MM-DD" (bornes incluses, optionnelles)
    - camera : "Porte_nord" / "Porte_sud" (si None -> toutes, agrégées par date)
    """
    data = data or load_data()
    df = data["per_day"].copy()

    if camera:
        df = df[df["camera"] == camera]

    if start_date:
        start = pd.to_datetime(start_date).date()
        df = df[df["date"] >= start]
    if end_date:
        end = pd.to_datetime(end_date).date()
        df = df[df["date"] <= end]

    df = df.sort_values(["date", "camera"])

    if not camera:
        # Agréger toutes les caméras par date
        agg_cols = [
            "visit_Count", "gender_men", "gender_women",
            "age_child", "age_teenager", "age_adult", "age_senior",
        ]
        df = df.groupby("date", as_index=False)[agg_cols].sum()
        df["camera"] = "toutes"

    df["date"] = df["date"].astype(str)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "camera": camera or "toutes",
        "count": len(df),
        "results": df.to_dict(orient="records"),
    }


def get_visitor_count(date: str | None = None, camera: str | None = None,
                       data: dict | None = None) -> dict:
    """
    Retourne le nombre de visiteurs pour une date donnée.
    - date   : "YYYY-MM-DD" (si None -> dernière date dispo)
    - camera : "Porte_sud" / "Porte_nord" (si None -> total)
    """
    data = data or load_data()
    df = data["per_day"]

    if not date or str(date).strip().lower() in ("null", "none"):
        target = df["date"].max()
    else:
        target = pd.to_datetime(date).date()

    rows = df[df["date"] == target]
    if camera:
        rows = rows[rows["camera"] == camera]

    if rows.empty:
        return {
            "date": str(target),
            "camera": camera or "toutes",
            "visit_count": None,
            "message": f"Aucune donnée disponible pour le {target}."
                       + (f" (caméra {camera})" if camera else ""),
        }

    total = int(rows["visit_Count"].sum())
    return {
        "date": str(target),
        "camera": camera or "toutes",
        "visit_count": total,
        "breakdown": rows[["camera", "visit_Count", "gender_men", "gender_women",
                            "age_child", "age_teenager", "age_adult", "age_senior"]]
                     .to_dict(orient="records"),
    }


def get_hourly_visitor_flow(date: str | None = None, camera: str | None = None,
                             data: dict | None = None) -> dict:
    """Retourne le flux horaire de visiteurs pour une date donnée."""
    data = data or load_data()
    df = data["per_hour"]

    if not date or str(date).strip().lower() in ("null", "none"):
        target = df["date"].max()
    else:
        target = pd.to_datetime(date).date()

    rows = df[df["date"] == target]
    if camera:
        rows = rows[rows["camera"] == camera]

    if rows.empty:
        return {
            "date": str(target),
            "camera": camera or "toutes",
            "hourly_flow": [],
            "message": f"Aucune donnée horaire pour le {target}.",
        }

    grouped = rows.groupby("hour", as_index=False)["count"].sum().sort_values("hour")
    return {
        "date": str(target),
        "camera": camera or "toutes",
        "hourly_flow": grouped.to_dict(orient="records"),
        "total": int(grouped["count"].sum()),
        "peak_hour": int(grouped.loc[grouped["count"].idxmax(), "hour"]),
    }


# ------------------------------------------------------------
# Prédiction du nombre de visiteurs
# ------------------------------------------------------------

def forecast_visitors(target_date: str | None = None, camera: str | None = None,
                       data: dict | None = None) -> dict:
    """
    Prédit le nombre de visiteurs pour `target_date` (par défaut : demain).

    Méthode :
      - Si >= 7 dates distinctes -> régression linéaire (tendance)
        + ajustement saisonnier par jour de semaine.
      - Sinon -> heuristique de repli (dernière valeur connue).
    """
    data = data or load_data()
    df = data["per_day"].copy()

    if camera:
        df = df[df["camera"] == camera]

    df = df.sort_values("date")
    n_dates = df["date"].nunique()

    if not target_date or str(target_date).strip().lower() in ("null", "none"):
        last_date = df["date"].max()
        target = last_date + timedelta(days=1)
    else:
        target = pd.to_datetime(target_date).date()

    daily = df.groupby("date", as_index=False)["visit_Count"].sum()

    if n_dates < 7:
        last_value = int(daily["visit_Count"].iloc[-1])
        return {
            "target_date": str(target),
            "camera": camera or "toutes",
            "predicted_visit_count": last_value,
            "method": "repli_dernier_jour_connu",
            "confidence": "faible",
            "model_status": "non_entraine",
            "message": (
                f"Modèle de prédiction non entraîné : seulement {n_dates} "
                f"date(s) disponible(s). Minimum recommandé : 7. "
                f"Estimation = dernière valeur connue ({last_value} visiteurs "
                f"le {daily['date'].iloc[-1]})."
            ),
        }

    daily["t"] = (daily["date"] - daily["date"].min()).apply(lambda d: d.days)
    daily["weekday"] = daily["date"].apply(lambda d: d.weekday())

    X = daily["t"].values.astype(float)
    y = daily["visit_Count"].values.astype(float)

    A = np.vstack([X, np.ones(len(X))]).T
    slope, intercept = np.linalg.lstsq(A, y, rcond=None)[0]

    t_target = (target - daily["date"].min()).days
    trend_pred = slope * t_target + intercept

    daily["trend"] = slope * daily["t"] + intercept
    daily["residual"] = daily["visit_Count"] - daily["trend"]
    weekday_adj = daily.groupby("weekday")["residual"].mean()
    adjustment = weekday_adj.get(target.weekday(), 0.0)

    prediction = max(0, round(trend_pred + adjustment))

    return {
        "target_date": str(target),
        "camera": camera or "toutes",
        "predicted_visit_count": int(prediction),
        "method": "regression_lineaire_tendance_+_ajustement_jour_semaine",
        "confidence": "bonne" if n_dates >= 30 else "moyenne",
        "model_status": "entraine",
        "n_historical_points": int(n_dates),
        "message": (
            f"Prédiction basée sur {n_dates} jours d'historique : "
            f"tendance={slope:.2f}/jour, intercept={intercept:.1f}, "
            f"ajustement jour({target.strftime('%A')})={adjustment:.1f}."
        ),
    }


# ------------------------------------------------------------
# Résumé global (KPIs)
# ------------------------------------------------------------

def get_summary(data: dict | None = None) -> dict:
    data = data or load_data()
    df = data["per_day"]

    total_visits = int(df["visit_Count"].sum())
    by_camera = (
        df.groupby("camera", as_index=False)["visit_Count"].sum()
        .to_dict(orient="records")
    )
    by_gender = {
        "men": int(df["gender_men"].sum()),
        "women": int(df["gender_women"].sum()),
    }
    by_age = {
        "child": int(df["age_child"].sum()),
        "teenager": int(df["age_teenager"].sum()),
        "adult": int(df["age_adult"].sum()),
        "senior": int(df["age_senior"].sum()),
    }

    return {
        "period": {
            "start_date": str(df["date"].min()),
            "end_date": str(df["date"].max()),
            "n_days": int(df["date"].nunique()),
        },
        "total_visits": total_visits,
        "by_camera": by_camera,
        "by_gender": by_gender,
        "by_age": by_age,
        "cameras": list_cameras(data),
    }
