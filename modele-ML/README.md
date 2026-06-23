# 🤖 Modèle ML — Visitor Profile Prediction API

Microservice FastAPI exposant le modèle XGBoost de prédiction du nombre de visiteurs par heure, caméra, genre et tranche d'âge pour le **ShoppingClub Sfax**.

---

## 📁 Structure du dossier

```
modele-ML/
├── main.py                      # API FastAPI (endpoints + logique de prédiction)
├── requirements.txt             # Dépendances Python
├── Dockerfile                   # Image Docker du microservice
└── xgboost_visitor_mvp.pkl      # Modèle XGBoost sérialisé (joblib)
```

---

## ⚙️ Fonctionnement

Le modèle prédit, pour une **date donnée**, le nombre de visiteurs pour chaque combinaison :

| Dimension    | Valeurs                                               |
|--------------|-------------------------------------------------------|
| **Heures**   | 7h → 23h (17 créneaux)                                |
| **Caméras**  | `Cam_porte1`, `Cam_porte2`                            |
| **Genre**    | `Female`, `Male`                                      |
| **Âge**      | `0-9`, `10-17`, `18-29`, `30-39`, `40-49`, `60-100`  |

### Features d'entrée

```
camera_enc, gender_enc, age_enc,
hour, month_num, day_of_week_num, is_weekend,
dow_Friday, dow_Monday, dow_Saturday, dow_Sunday,
dow_Thursday, dow_Tuesday, dow_Wednesday
```

---

## 🚀 Déploiement

### Prérequis

- Docker ≥ 24.x
- Le fichier `xgboost_visitor_mvp.pkl` doit être présent dans le dossier avant le build

---

### Option 1 — Docker standalone

#### 1. Build de l'image

```bash
cd modele-ML/
docker build -t visitor-ml-api:latest .
```

#### 2. Lancement du conteneur

```bash
docker run -d \
  --name visitor_ml_api \
  -p 8000:8000 \
  visitor-ml-api:latest
```

#### 3. Vérification

```bash
# Health check
curl http://localhost:8000/health
# → {"status":"ok","model_loaded":true}

# Prédiction pour aujourd'hui
curl "http://localhost:8000/predict"

# Prédiction pour une date spécifique
curl "http://localhost:8000/predict?date=2026-07-01"
```

#### 4. Documentation Swagger interactive

Ouvrir dans le navigateur : [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Option 2 — Via Docker Compose (intégration Anavid stack)

Le service est déclaré dans le `docker-compose.yml` racine du projet sous le nom `visitor_ml_api`.

```bash
# Depuis la racine du projet
docker compose up -d visitor_ml_api

# Logs en temps réel
docker compose logs -f visitor_ml_api
```

Le service est accessible depuis les autres conteneurs via :

```
http://visitor_ml_api:8000
```

> ⚠️ **Ne pas utiliser `localhost`** depuis un autre conteneur Docker — utiliser le nom de service `visitor_ml_api`.

---

### Option 3 — Lancement local (sans Docker)

```bash
cd modele-ML/

# Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate        # Linux/Mac
# .venv\Scripts\activate         # Windows

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'API
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 📡 Endpoints

| Méthode | Route       | Description                                           |
|---------|-------------|-------------------------------------------------------|
| `GET`   | `/`         | Informations générales sur l'API                      |
| `GET`   | `/health`   | Statut de santé + vérification du chargement modèle   |
| `GET`   | `/predict`  | Prédictions pour une date (`?date=YYYY-MM-DD`)        |
| `GET`   | `/docs`     | Documentation Swagger UI interactive                  |

### Exemple de réponse `/predict`

```json
{
  "date": "2026-07-01",
  "predictions": [
    {
      "hour": 7,
      "camera": "Cam_porte1",
      "profile": [
        { "gender": "Female", "age": "18-29", "visits_predicted": 12 },
        { "gender": "Male",   "age": "30-39", "visits_predicted": 9  }
      ],
      "total_visits": 21
    }
  ]
}
```

---

## 🔄 Mise à jour du modèle

Pour déployer une nouvelle version du modèle `.pkl` :

1. Remplacer `xgboost_visitor_mvp.pkl` par la nouvelle version
2. Rebuilder l'image Docker :

```bash
docker build -t visitor-ml-api:latest .
docker compose up -d --build visitor_ml_api
```

> Le modèle est chargé **une seule fois au démarrage** (`joblib.load`). Un simple redémarrage du conteneur suffit si l'image n'a pas changé.

---

## 🐛 Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| `"model_loaded": false` | `.pkl` absent du conteneur | Vérifier que `xgboost_visitor_mvp.pkl` est dans `modele-ML/` avant le build |
| `503 Service Unavailable` | Modèle non chargé | Voir ci-dessus + consulter `docker logs visitor_ml_api` |
| `400 Bad Request` | Format de date invalide | Utiliser le format `YYYY-MM-DD` (ex: `2026-07-01`) |
| Port 8000 déjà utilisé | Conflit de port | Changer le port hôte : `-p 8001:8000` |

---

## 📦 Dépendances

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
joblib==1.4.2
numpy==1.26.4
pandas==2.2.2
xgboost==2.1.1
pydantic==2.9.2
```
