"""
Visitor Daily Prediction API
--------------------------------
Expose le modèle LightGBM (niveau journalier) via une API REST FastAPI.

Endpoint principal :
    POST /predict
    Body JSON : {
        "date": "YYYY-MM-DD",
        "temperature": 32.0,        # temp_max_c (°C) — depuis Open-Meteo
        "wind_speed": 18.0,         # wind_kmh — depuis Open-Meteo
        "type_jour": "normal"       # "normal" | "ferie" — depuis Nager.Date
    }

Retourne :
    {
        "date": "2026-06-25",
        "predictions": [
            {
                "hour": 10,
                "camera": "Cam_porte1",
                "profile": [...],
                "total_visits": 42
            },
            ...
        ]
    }

Architecture :
  - LightGBM (lightgbm_shoppingclub.pkl) prédit le total visiteurs/jour
    à partir des features météo + calendrier.
  - La répartition par heure/caméra/profil est calculée par des poids
    statistiques (distribution historique) appliqués au total journalier.
"""

from datetime import date as date_type
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_PATH = "lightgbm_shoppingclub.pkl"

OPENING_HOURS = list(range(7, 24))   # 7h à 23h inclus
CAMERAS       = ["Cam_porte1", "Cam_porte2"]
GENDERS       = ["Female", "Male"]
AGES          = ["0-9", "10-17", "18-29", "30-39", "40-49", "60-100"]

# Features attendues par le modèle LightGBM (ordre identique à l'entraînement)
LGBM_FEATURES = [
    "day_of_week", "is_weekend", "month", "week_of_year", "quarter",
    "is_pre_holiday", "is_post_holiday", "is_school_holiday",
    "pre_holiday_name_enc",
    "days_to_next_holiday", "days_since_last_holiday",
    "temp_max_c", "temp_min_c", "temp_range_c",
    "precipitation_mm", "wind_kmh", "humidity_pct",
    "weather_comfort_score", "is_rainy", "heat_stress",
    "weather_category_enc",
]

# Distribution horaire (poids relatifs, somme = 1) — basée sur la moyenne
# statistique shoppingclub. Remplacer par des valeurs réelles si disponibles.
HOUR_WEIGHTS = {
     7: 0.020,  8: 0.035,  9: 0.055, 10: 0.075, 11: 0.075,
    12: 0.070, 13: 0.060, 14: 0.065, 15: 0.070, 16: 0.075,
    17: 0.080, 18: 0.080, 19: 0.065, 20: 0.050, 21: 0.035,
    22: 0.025, 23: 0.015,
}

# Poids caméras (répartition portes)
CAMERA_WEIGHTS = {"Cam_porte1": 0.55, "Cam_porte2": 0.45}

# Poids profils (gender × age) — distribution moyenne historique
PROFILE_WEIGHTS = {
    ("Female", "18-29"): 0.18, ("Female", "30-39"): 0.14, ("Female", "40-49"): 0.10,
    ("Female", "10-17"): 0.07, ("Female", "60-100"): 0.05, ("Female", "0-9"):   0.03,
    ("Male",   "18-29"): 0.14, ("Male",   "30-39"): 0.12, ("Male",   "40-49"): 0.09,
    ("Male",   "10-17"): 0.06, ("Male",   "60-100"): 0.06, ("Male",   "0-9"):   0.02,
}
# Normalisation de sécurité
_pw_sum = sum(PROFILE_WEIGHTS.values())
PROFILE_WEIGHTS = {k: v / _pw_sum for k, v in PROFILE_WEIGHTS.items()}


# ---------------------------------------------------------------------------
# App FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Visitor Daily Prediction API (LightGBM)",
    description="Prédiction journalière du nombre de visiteurs avec features météo + calendrier.",
    version="2.0.0",
)

try:
    model = joblib.load(MODEL_PATH)
except FileNotFoundError:
    model = None


# ---------------------------------------------------------------------------
# Schémas Pydantic
# ---------------------------------------------------------------------------

class PredictRequest(BaseModel):
    date: str
    temperature: Optional[float] = None   # temp_max_c (°C)
    wind_speed: Optional[float]  = None   # wind_kmh
    type_jour: Optional[str]     = "normal"  # "normal" | "ferie"


class ProfileEntry(BaseModel):
    gender: str
    age: str
    visits_predicted: int


class HourPrediction(BaseModel):
    hour: int
    camera: str
    profile: list[ProfileEntry]
    total_visits: int


class PredictionResponse(BaseModel):
    date: str
    predictions: list[HourPrediction]


# ---------------------------------------------------------------------------
# Helpers météo
# ---------------------------------------------------------------------------

def assign_weather_category_enc(temp_max: float, precip: float) -> int:
    """
    Encode la catégorie météo de manière cohérente avec l'entraînement :
    cold=0, hot=1, mild=2, rainy=3, stormy=4, very_hot=5
    (ordre alphabétique du LabelEncoder sklearn).
    """
    if precip > 5:
        return 4   # stormy
    elif precip > 0.5:
        return 3   # rainy
    elif temp_max > 38:
        return 5   # very_hot
    elif temp_max > 30:
        return 1   # hot
    elif temp_max < 15:
        return 0   # cold
    else:
        return 2   # mild


def compute_weather_features(temperature: float, wind_speed: float) -> dict:
    """
    Dérive toutes les features météo attendues par le modèle
    à partir des deux champs Open-Meteo (temp actuelle + vent).
    """
    # Approximations raisonnables pour temp_min / temp_range
    temp_max   = temperature
    temp_min   = max(temperature - 8, 5)    # Δ typique Sfax ≈ 8°C
    temp_range = temp_max - temp_min

    precip     = 0.0   # Open-Meteo current ne fournit pas les précipitations
    humidity   = max(30, min(85, 75 - temperature * 0.5))  # estimation
    is_rainy   = 0
    heat_stress = 1 if temperature > 35 else 0

    # comfort = 100 − |temp_max − 22| * 2 − wind * 0.5 − precip * 5
    comfort    = max(0, 100 - abs(temp_max - 22) * 2 - wind_speed * 0.5)

    weather_cat_enc = assign_weather_category_enc(temp_max, precip)

    return {
        "temp_max_c":            temp_max,
        "temp_min_c":            temp_min,
        "temp_range_c":          temp_range,
        "precipitation_mm":      precip,
        "wind_kmh":              wind_speed,
        "humidity_pct":          humidity,
        "is_rainy":              is_rainy,
        "heat_stress":           heat_stress,
        "weather_comfort_score": comfort,
        "weather_category_enc":  weather_cat_enc,
    }


def compute_calendar_features(target_date: date_type, type_jour: str) -> dict:
    """
    Dérive les features calendaires depuis la date + type_jour (Nager.Date).
    """
    dow          = target_date.weekday()   # 0=Mon … 6=Sun
    is_weekend   = 1 if dow >= 5 else 0
    month        = target_date.month
    week_of_year = target_date.isocalendar()[1]
    quarter      = (month - 1) // 3 + 1

    is_ferie     = 1 if type_jour == "ferie" else 0

    # Heuristiques simples pour les flags annexes
    is_pre_holiday       = 0   # Non connu à l'avance via Nager
    is_post_holiday      = 0
    is_school_holiday    = 0
    pre_holiday_name_enc = 0   # "none" → 0 (LabelEncoder)
    days_to_next_holiday = 7   # valeur neutre
    days_since_last_holiday = 7

    return {
        "day_of_week":           dow,
        "is_weekend":            is_weekend,
        "month":                 month,
        "week_of_year":          week_of_year,
        "quarter":               quarter,
        "is_pre_holiday":        is_pre_holiday,
        "is_post_holiday":       is_post_holiday,
        "is_school_holiday":     is_school_holiday,
        "pre_holiday_name_enc":  pre_holiday_name_enc,
        "days_to_next_holiday":  days_to_next_holiday,
        "days_since_last_holiday": days_since_last_holiday,
        # Pas dans LGBM_FEATURES mais conservé pour la répartition profils
        "is_ferie":              is_ferie,
    }


# ---------------------------------------------------------------------------
# Prédiction
# ---------------------------------------------------------------------------

def distribute_to_hourly(total_daily: int, target_date: date_type) -> list[HourPrediction]:
    """
    Redistribue le total journalier prédit par LightGBM
    sur les heures, caméras et profils via des poids statistiques.
    """
    predictions = []
    for hour in OPENING_HOURS:
        hour_total = total_daily * HOUR_WEIGHTS.get(hour, 1 / len(OPENING_HOURS))
        for camera in CAMERAS:
            cam_total = hour_total * CAMERA_WEIGHTS[camera]
            profile_entries = []
            for gender in GENDERS:
                for age in AGES:
                    w = PROFILE_WEIGHTS.get((gender, age), 0.01)
                    visits = max(0, round(cam_total * w))
                    profile_entries.append(ProfileEntry(
                        gender=gender,
                        age=age,
                        visits_predicted=visits,
                    ))
            predictions.append(HourPrediction(
                hour=hour,
                camera=camera,
                profile=profile_entries,
                total_visits=int(round(cam_total)),
            ))

    predictions.sort(key=lambda p: (p.hour, p.camera))
    return predictions


def run_daily_prediction(
    target_date: date_type,
    temperature: float,
    wind_speed: float,
    type_jour: str,
) -> PredictionResponse:
    """Prédit le total journalier avec LightGBM puis redistribue par heure/caméra/profil."""
    weather  = compute_weather_features(temperature, wind_speed)
    calendar = compute_calendar_features(target_date, type_jour)

    row = {**weather, **calendar}
    df_input = pd.DataFrame([row])[LGBM_FEATURES]

    raw_pred = model.predict(df_input)[0]
    total_daily = max(0, int(round(raw_pred)))

    predictions = distribute_to_hourly(total_daily, target_date)

    return PredictionResponse(date=target_date.isoformat(), predictions=predictions)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/", tags=["Info"])
def root():
    return {
        "message": "Visitor Daily Prediction API (LightGBM)",
        "docs": "/docs",
        "predict_endpoint": "POST /predict — body: {date, temperature, wind_speed, type_jour}",
    }


@app.get("/health", tags=["Info"])
def health():
    return {"status": "ok", "model_loaded": model is not None}


@app.post("/predict", response_model=PredictionResponse, tags=["Prediction"])
def predict(req: PredictRequest):
    if model is None:
        raise HTTPException(
            status_code=503,
            detail=f"Modèle non chargé. Vérifiez que '{MODEL_PATH}' existe.",
        )

    # Validation date
    try:
        target_date = pd.Timestamp(req.date).date()
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail="Format de date invalide. Utilisez YYYY-MM-DD (ex: 2026-06-25).",
        )

    # Valeurs par défaut si météo absente (fallback Sfax été)
    temperature = req.temperature if req.temperature is not None else 32.0
    wind_speed  = req.wind_speed  if req.wind_speed  is not None else 15.0
    type_jour   = req.type_jour   if req.type_jour   is not None else "normal"

    return run_daily_prediction(target_date, temperature, wind_speed, type_jour)