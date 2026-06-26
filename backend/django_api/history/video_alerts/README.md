# `history/video_alerts/` — Alertes Vidéo

Gère les alertes de détection de vol générées par le système de vidéosurveillance.  
Chaque alerte est liée à un **espace** (magasin/caméra) et peut être qualifiée manuellement par un opérateur.

---

## Modèles

### `AlertSpace` — Espace de surveillance
Mappe la table `notifications_space` (table externe, `managed = False`).

| Champ | Type | Description |
|---|---|---|
| `name` | `CharField` | Nom du magasin |
| `code` | `CharField` | Code identifiant |
| `organization_id` | `BigIntegerField` | ID de l'organisation parente |
| `address`, `city`, `country` | `CharField` | Localisation |
| `telegram_chat_id` | `CharField` | Chat Telegram pour les alertes |
| `token_web_connector` | `CharField` | Token connecteur web |

### `VideoTheftAlert` — Alerte vidéo
Mappe la table `notifications_video` (table externe, `managed = False`).

| Champ | Type | Valeurs possibles |
|---|---|---|
| `status` | `CharField` | `PENDING` · `APPROVED` · `REJECTED` |
| `qualification` | `CharField` | `vol` · `suspicious` · `false_alarm` · `null` |
| `probability` | `FloatField` | Score de confiance du modèle (0–1) |
| `approval_result` | `CharField` | `TP` · `TN` · `FP` · `FN` |
| `recording_date` | `DateTimeField` | Date/heure de l'enregistrement |
| `space` | `ForeignKey` | Lien vers `AlertSpace` |

---

## Endpoints

### Espaces de surveillance

| Méthode | URL | Description |
|---|---|---|
| `GET` | `/api/video-alerts/spaces/` | Liste tous les espaces |
| `GET` | `/api/video-alerts/spaces/<space_id>/` | Détail d'un espace |

> Pas de pagination sur `spaces/` — référentiel statique (nombre d'espaces faible et fixe).

---

### Alertes vidéo

| Méthode | URL | Description |
|---|---|---|
| `GET` | `/api/video-alerts/all/` | Toutes les alertes approuvées |
| `GET` | `/api/video-alerts/space/<space_id>/` | Alertes d'un espace |
| `GET` | `/api/video-alerts/organization/<organization_id>/` | Alertes d'une organisation |
| `GET` | `/api/video-alerts/<video_id>/` | Détail d'une alerte |
| `PATCH` | `/api/video-alerts/<video_id>/qualify/` | Qualifier une alerte |

**Alias frontend** (URLs historiques conservées) :

| Méthode | URL | Redirige vers |
|---|---|---|
| `GET` | `/api/videos/all/` | `list_all_video_alerts` |
| `GET` | `/api/videos/spaces/` | `list_alert_spaces` |
| `GET` | `/api/videos/space/<space_id>/` | `videos_by_space` |
| `GET` | `/api/videos/organisation/<id>/` | `videos_by_organization` |
| `PATCH` | `/api/videos/<id>/qualify/` | `qualify_video_alert` |

---

### Statistiques

| Méthode | URL | Description |
|---|---|---|
| `GET` | `/api/video-alerts/stats/` | Compteurs globaux par statut et qualification |

**Réponse :**
```json
{
  "total": 320,
  "by_status": {
    "approved": 210,
    "pending": 85,
    "rejected": 25
  },
  "qualified": 195,
  "by_qualification": {
    "vol": 80,
    "suspicious": 70,
    "false_alarm": 45
  }
}
```

---

## Pagination

Les endpoints de liste supportent `limit` / `offset` (via `get_pagination_params` dans `history/utils.py`) :

```
GET /api/videos/all/?limit=20&offset=40
GET /api/video-alerts/space/3/?limit=10&offset=0&qualification=vol
```

**Réponse standard :**
```json
{
  "count": 210,
  "limit": 20,
  "offset": 40,
  "results": [...]
}
```

| Paramètre | Défaut | Max |
|---|---|---|
| `limit` | `50` | `200` |
| `offset` | `0` | — |

---

## Filtres disponibles

| Paramètre | Valeurs | Endpoints concernés |
|---|---|---|
| `status` | `PENDING` · `APPROVED` · `REJECTED` | `videos_by_space`, `videos_by_organization` |
| `qualification` | `vol` · `suspicious` · `false_alarm` · `null` | tous les endpoints liste |

---

## Qualification manuelle — `PATCH /api/video-alerts/<id>/qualify/`

Corps de la requête (tous les champs sont optionnels) :

```json
{
  "status": "APPROVED",
  "qualification": "vol",
  "comment": "Comportement confirmé par l'opérateur",
  "assigned_to": "operateur@boutique.com",
  "approval_result": "TP"
}
```

**Réponse :**
```json
{
  "status": "ok",
  "message": "Alerte vidéo mise à jour avec succès",
  "alert": { ... }
}
```

---

## Fichiers

| Fichier | Rôle |
|---|---|
| `models.py` | `AlertSpace` et `VideoTheftAlert` (tables externes) |
| `views.py` | Toutes les vues API (liste, détail, qualification, stats) |
| `serializers.py` | Sérialisation list / detail / qualification |
| `urls.py` | Routage sous `video-alerts/` (namespace `video_alerts`) |
| `admin.py` | Interface d'administration Django |