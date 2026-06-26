# `history/visitors/` — Analytics Visiteurs

Fournit les données d'affluence du magasin à partir du CSV source (`shoppingclub_2025_2026.csv`).  
Toutes les vues sont en lecture seule, sans authentification requise.

---

## Endpoints

| Méthode | URL | Description |
|---|---|---|
| `GET` | `/api/history/visitors/` | Historique paginé des passages |
| `GET` | `/api/history/visitors/count/` | Nombre de visiteurs pour une date |
| `GET` | `/api/history/visitors/hourly/` | Flux horaire (24 points max) |
| `GET` | `/api/history/visitors/forecast/` | Prévision pour une date future |
| `GET` | `/api/history/summary/` | Résumé global des données |
| `GET` | `/api/history/cameras/` | Liste des caméras disponibles |

---

## Paramètres communs

| Paramètre | Type | Description |
|---|---|---|
| `start_date` | `YYYY-MM-DD` | Borne de début (optionnel) |
| `end_date` | `YYYY-MM-DD` | Borne de fin (optionnel) |
| `date` | `YYYY-MM-DD` | Date précise (pour `count`, `hourly`, `forecast`) |
| `camera` | `string` | Filtrer par caméra : `Porte_nord` ou `Porte_sud` |

---

## Pagination — `GET /api/history/visitors/`

```
GET /api/history/visitors/?start_date=2026-05-01&end_date=2026-05-31&limit=14&offset=0
```

**Réponse :**
```json
{
  "start_date": "2026-05-01",
  "end_date": "2026-05-31",
  "camera": null,
  "count": 62,
  "limit": 14,
  "offset": 0,
  "results": [
    {
      "date": "2026-05-01",
      "Porte_nord": 120,
      "Porte_sud": 98,
      "total": 218
    }
  ]
}
```

| Paramètre | Défaut |
|---|---|
| `limit` | `14` |
| `offset` | `0` |

---

## Flux horaire — `GET /api/history/visitors/hourly/`

Retourne jusqu'à 24 points (une entrée par heure de la journée).  
Pas de pagination — volume fixe et borné.

```
GET /api/history/visitors/hourly/?date=2026-05-30&camera=Porte_nord
```

**Réponse :**
```json
{
  "date": "2026-05-30",
  "camera": "Porte_nord",
  "hourly": [
    { "hour": 9, "count": 34 },
    { "hour": 10, "count": 67 }
  ]
}
```

---

## Prévision — `GET /api/history/visitors/forecast/`

Prévision basée sur les données historiques du CSV.

```
GET /api/history/visitors/forecast/?date=2026-07-01&camera=Porte_sud
```

**Réponse :**
```json
{
  "date": "2026-07-01",
  "camera": "Porte_sud",
  "forecast": 143,
  "confidence": "medium"
}
```

---

## Fichiers

| Fichier | Rôle |
|---|---|
| `views.py` | Vues API (lecture seule) |
| `data.py` | Chargement et traitement du CSV source |
| `urls.py` | Routage sous `history/` (namespace `visitors`) |