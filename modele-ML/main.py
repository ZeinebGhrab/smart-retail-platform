"""
Visitor Profile Prediction API
--------------------------------
Expose le modèle XGBoost MVP via une API REST FastAPI.

Endpoint principal :
    GET /predict?date=YYYY-MM-DD

Retourne, pour chaque heure d'ouverture (7h-23h) et chaque caméra,
le nombre de visiteurs prédit par combinaison (genre, âge).
"""

from datetime import date as date_type
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration / constantes (doivent matcher l'entraînement du modèle)
# ---------------------------------------------------------------------------

MODEL_PATH = "xgboost_visitor_mvp.pkl"

OPENING_HOURS = list(range(7, 24))  # 7h à 23h inclus
CAMERAS = ["Cam_porte1", "Cam_porte2"]
GENDERS = ["Female", "Male"]
AGES = ["0-9", "10-17", "18-29", "30-39", "40-49", "60-100"]

CAMERA_ENC = {"Cam_porte1": 0, "Cam_porte2": 1}
GENDER_ENC = {"Female": 0, "Male": 1}
AGE_ENC = {"0-9": 0, "10-17": 1, "18-29": 2, "30-39": 3, "40-49": 4, "60-100": 5}

DOW_COLUMNS = [
    "dow_Friday", "dow_Monday", "dow_Saturday",
    "dow_Sunday", "dow_Thursday", "dow_Tuesday", "dow_Wednesday",
]

FEATURE_COLUMNS = [
    "camera_enc", "gender_enc", "age_enc",
    "hour", "month_num", "day_of_week_num", "is_weekend",
] + DOW_COLUMNS

# ---------------------------------------------------------------------------
# Chargement du modèle (une seule fois, au démarrage de l'API)
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Visitor Profile Prediction API",
    description="Prédiction du nombre de visiteurs par caméra, heure, genre et tranche d'âge.",
    version="1.0.0",
)

try:
    model = joblib.load(MODEL_PATH)
except FileNotFoundError:
    model = None


# ---------------------------------------------------------------------------
# Schémas de réponse (Pydantic) — définissent le format JSON retourné
# ---------------------------------------------------------------------------

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
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def build_feature_rows(target_date: date_type) -> pd.DataFrame:
    """
    Construit toutes les lignes de features nécessaires pour une date donnée :
    chaque heure d'ouverture x chaque caméra x chaque combinaison (genre, âge).
    """
    dow_name = target_date.strftime("%A")  # ex: "Saturday"
    day_of_week_num = target_date.weekday()
    is_weekend = 1 if day_of_week_num >= 5 else 0
    month_num = target_date.month

    rows = []
    for hour in OPENING_HOURS:
        for camera in CAMERAS:
            for gender in GENDERS:
                for age in AGES:
                    row = {
                        "hour": hour,
                        "camera": camera,
                        "gender": gender,
                        "age": age,
                        "camera_enc": CAMERA_ENC[camera],
                        "gender_enc": GENDER_ENC[gender],
                        "age_enc": AGE_ENC[age],
                        "month_num": month_num,
                        "day_of_week_num": day_of_week_num,
                        "is_weekend": is_weekend,
                    }
                    for col in DOW_COLUMNS:
                        row[col] = 1 if col == f"dow_{dow_name}" else 0
                    rows.append(row)

    return pd.DataFrame(rows)


def run_predictions(target_date: date_type) -> PredictionResponse:
    """Calcule les prédictions pour toutes les heures/caméras de la date donnée."""
    df_input = build_feature_rows(target_date)

    raw_preds = model.predict(df_input[FEATURE_COLUMNS])
    df_input["visits_predicted"] = np.maximum(raw_preds, 0).round().astype(int)

    predictions = []
    for (hour, camera), group in df_input.groupby(["hour", "camera"], sort=True):
        profile = [
            ProfileEntry(
                gender=r["gender"],
                age=r["age"],
                visits_predicted=int(r["visits_predicted"]),
            )
            for _, r in group.iterrows()
        ]
        predictions.append(
            HourPrediction(
                hour=int(hour),
                camera=camera,
                profile=profile,
                total_visits=int(group["visits_predicted"].sum()),
            )
        )

    # Tri par heure puis caméra pour un ordre de réponse stable
    predictions.sort(key=lambda p: (p.hour, p.camera))

    return PredictionResponse(date=target_date.isoformat(), predictions=predictions)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/", tags=["Info"])
def root():
    return {
        "message": "Visitor Profile Prediction API",
        "docs": "/docs",
        "predict_endpoint": "/predict?date=YYYY-MM-DD (optionnel, défaut = aujourd'hui)",
    }


@app.get("/health", tags=["Info"])
def health():
    return {"status": "ok", "model_loaded": model is not None}


@app.get("/predict", response_model=PredictionResponse, tags=["Prediction"])
def predict(
    date: Optional[str] = Query(
        default=None,
        description="Date au format YYYY-MM-DD. Si omis, la date du jour est utilisée.",
    )
):
    if model is None:
        raise HTTPException(
            status_code=503,
            detail=f"Modèle non chargé. Vérifiez que '{MODEL_PATH}' existe.",
        )

    if date is None:
        target_date = date_type.today()
    else:
        try:
            target_date = pd.Timestamp(date).date()
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400,
                detail="Format de date invalide. Utilisez YYYY-MM-DD (ex: 2026-06-20).",
            )

    return run_predictions(target_date)
