# ============================================================
# visitor_data.py — Chargement & analyse des données visiteurs
# Source : SA-data.xlsx (feuilles Per_Day, Per_Hour)
# ============================================================
#
# Fournit :
#   - load_data()                      -> dict avec les DataFrames Per_Day / Per_Hour
#   - get_visitor_count(date, camera)  -> nb visiteurs pour une date/caméra
#   - get_hourly_visitor_flow(date)    -> flux horaire (toutes caméras)
#   - forecast_visitors(...)           -> prédiction simple (régression linéaire
#                                          sur l'historique disponible)
#
# NOTE : le dataset actuel ne contient qu'UNE seule date (2026-06-08).
# Un modèle de prédiction fiable nécessite un historique multi-jours.
# En attendant, forecast_visitors() utilise une heuristique de repli
# (moyenne pondérée par jour de semaine si dispo, sinon valeur du
# dernier jour connu) ET expose clairement son niveau de confiance.
# ============================================================

from __future__ import annotations

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "SA-data.xlsx"


def load_data(path: str | Path = DATA_PATH) -> dict[str, pd.DataFrame]:
    """Charge les feuilles Per_Day et Per_Hour du fichier Excel."""
    xls = pd.ExcelFile(path)
    per_day = xls.parse("Per_Day")
    per_hour = xls.parse("Per_Hour")

    # La feuille Per_Hour a des cellules fusionnées (camera/date répétés
    # uniquement sur la première ligne de chaque bloc) -> forward-fill
    per_hour["camera"] = per_hour["camera"].ffill()
    per_hour["date"] = per_hour["date"].ffill()

    per_day["date"] = pd.to_datetime(per_day["date"]).dt.date
    per_hour["date"] = pd.to_datetime(per_hour["date"]).dt.date

    return {"per_day": per_day, "per_hour": per_hour}


# ------------------------------------------------------------
# Requêtes simples (tool calling)
# ------------------------------------------------------------

def get_visitor_count(date: str | None = None, camera: str | None = None,
                       data: dict | None = None) -> dict:
    """
    Retourne le nombre de visiteurs pour une date donnée.
    - date : "YYYY-MM-DD" (si None -> dernière date dispo)
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
                       + (f" (caméra {camera})" if camera else "")
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
            "message": f"Aucune donnée horaire pour le {target}."
        }

    grouped = rows.groupby("hour", as_index=False)["count"].sum().sort_values("hour")
    return {
        "date": str(target),
        "camera": camera or "toutes",
        "hourly_flow": grouped.to_dict(orient="records"),
        "total": int(grouped["count"].sum()),
        "peak_hour": grouped.loc[grouped["count"].idxmax(), "hour"],
    }


# ------------------------------------------------------------
# Prédiction du nombre de visiteurs
# ------------------------------------------------------------

def forecast_visitors(target_date: str | None = None, camera: str | None = None,
                       data: dict | None = None) -> dict:
    """
    Prédit le nombre de visiteurs pour `target_date` (par défaut : demain).

    Méthode :
      - Si >= 7 dates distinctes disponibles -> régression linéaire simple
        (tendance) + moyenne par jour de semaine.
      - Si < 7 dates (cas actuel : 1 seule date) -> heuristique de repli :
        on retourne la dernière valeur connue, avec un avertissement
        explicite sur la fiabilité ("modèle non entraîné, données
        insuffisantes").

    Le modèle s'adapte automatiquement dès que plus de données seront
    ajoutées au fichier SA-data.xlsx (Per_Day) : il devient une
    régression réelle dès qu'un historique suffisant existe.
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

    # Agrège par date (toutes caméras confondues si camera=None)
    daily = df.groupby("date", as_index=False)["visit_Count"].sum()

    if n_dates < 7:
        # --- Heuristique de repli : pas assez d'historique ---
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
                f"date(s) disponible(s) dans l'historique (minimum 7 "
                f"recommandé). Estimation basée sur la dernière valeur "
                f"connue ({last_value} visiteurs le {daily['date'].iloc[-1]}). "
                f"Ajoutez davantage de jours dans SA-data.xlsx pour activer "
                f"la régression."
            ),
        }

    # --- Régression linéaire simple sur le temps + ajustement jour-semaine ---
    daily["t"] = (daily["date"] - daily["date"].min()).apply(lambda d: d.days)
    daily["weekday"] = daily["date"].apply(lambda d: d.weekday())

    X = daily["t"].values.astype(float)
    y = daily["visit_Count"].values.astype(float)

    # régression linéaire (moindres carrés)
    A = np.vstack([X, np.ones(len(X))]).T
    slope, intercept = np.linalg.lstsq(A, y, rcond=None)[0]

    t_target = (target - daily["date"].min()).days
    trend_pred = slope * t_target + intercept

    # ajustement saisonnier par jour de semaine (moyenne des résidus)
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
        "confidence": "moyenne" if n_dates < 30 else "bonne",
        "model_status": "entraine",
        "n_historical_points": int(n_dates),
        "message": (
            f"Prédiction basée sur {n_dates} jours d'historique : "
            f"tendance={slope:.2f}/jour, intercept={intercept:.1f}, "
            f"ajustement jour({target.strftime('%A')})={adjustment:.1f}."
        ),
    }


if __name__ == "__main__":
    d = load_data()
    print(get_visitor_count(data=d))
    print(get_hourly_visitor_flow(data=d))
    print(forecast_visitors(data=d))
    print(forecast_visitors(target_date="2026-06-09", data=d))