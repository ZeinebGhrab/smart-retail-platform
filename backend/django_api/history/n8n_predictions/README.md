# `history/n8n_predictions/` — Prédictions N8N & Notifications

Reçoit les rapports quotidiens générés par le workflow **N8N + Llama 3.2**,  
les persiste en base, les diffuse en temps réel (SSE) et les envoie en push (FCM).

---

## Modèles

### `PredictionNotification` — Notification de prédiction

| Champ | Type | Description |
|---|---|---|
| `notification_uuid` | `CharField` | UUID unique (généré par N8N ou auto) |
| `type` | `CharField` | `prediction` · `report` · `alert` · `custom` |
| `title` | `CharField` | Titre (auto-généré si absent) |
| `message` | `TextField` | Corps du rapport LLM |
| `date` | `DateField` | Date concernée par la prédiction |
| `visiteurs_prevus` | `IntegerField` | Nombre de visiteurs prévus |
| `profil_dominant` | `CharField` | Ex : `"Femmes 25-35"` |
| `niveau_affluence` | `CharField` | `low` · `medium` · `high` · `very_high` |
| `heure_pointe` | `CharField` | Ex : `"14h30"` |
| `model` | `CharField` | Modèle LLM utilisé |
| `confidence_score` | `FloatField` | Score de confiance (0–1, nullable) |
| `is_read` | `BooleanField` | Lu / non lu |
| `generated_at` | `DateTimeField` | Timestamp de réception |
| `tags` | `CharField` | Tags séparés par virgule |
| `metadata` | `JSONField` | Données additionnelles libres |

### `FCMToken` — Token Firebase
Stocke les tokens FCM des appareils pour les notifications push.

| Champ | Description |
|---|---|
| `token` | Token FCM unique (max 255 chars) |
| `device_info` | OS et version de l'appareil |
| `is_active` | Actif ou révoqué |

### `PushNotificationLog` — Journal d'envoi FCM
Trace chaque envoi push avec statut, compteurs et erreurs.

---

## Endpoints

### Notifications

| Méthode | URL | Auth | Description |
|---|---|---|---|
| `GET` | `/api/notifications/latest/` | Non | Dernière notification reçue |
| `GET` | `/api/notifications/history/` | Non | Historique paginé |
| `GET` | `/api/notifications/<id>/` | Non | Détail d'une notification |
| `POST` | `/api/notifications/<id>/mark-read/` | Non | Marquer comme lue |
| `POST` | `/api/notifications/mark-all-read/` | Non | Tout marquer comme lu |
| `GET` | `/api/notifications/unread-count/` | Non | Nombre de non lues |

---

### Pagination — `GET /api/notifications/history/`

```
GET /api/notifications/history/?limit=20&offset=0&type=report&is_read=false
```

**Réponse :**
```json
{
  "count": 87,
  "limit": 20,
  "offset": 0,
  "results": [...]
}
```

**Filtres disponibles :**

| Paramètre | Valeurs | Description |
|---|---|---|
| `type` | `prediction` · `report` · `alert` · `custom` | Filtrer par type |
| `is_read` | `true` · `false` | Filtrer par statut de lecture |
| `limit` | entier (défaut `50`, max `200`) | Taille de page |
| `offset` | entier (défaut `0`) | Décalage |

---

### Réception depuis N8N — `POST /api/predictions/daily-report/`

Webhook appelé par N8N pour envoyer un rapport quotidien. Ne nécessite pas d'authentification.

**Payload minimal :**
```json
{
  "type": "llm_report",
  "date": "2026-06-26",
  "message": "Texte du rapport généré par Llama 3.2...",
  "prediction": {
    "visiteurs_prevus": 150,
    "profil_dominant": "Femmes 25-35",
    "niveau_affluence": "Élevé",
    "heure_pointe": "14h30"
  }
}
```

> Le champ `title` est optionnel — généré automatiquement (`"Rapport IA – 2026-06-26"`).  
> `niveau_affluence` accepte les valeurs françaises (`Élevé`, `Faible`, `Modéré`) ou anglaises (`high`, `low`, `medium`).

**Réponse :**
```json
{
  "status": "ok",
  "clients_notified": 3,
  "notification_id": 42,
  "notification_uuid": "uuid-...",
  "notification": { ... }
}
```

---

### SSE — Streaming temps réel

| Méthode | URL | Description |
|---|---|---|
| `GET` | `/api/prediction/stream/` | Flux SSE — connexion persistante |
| `GET` | `/api/predictions/stream/` | Même endpoint (namespace `predictions`) |

Le client reçoit un événement à chaque nouveau rapport N8N :

```
event: llm_report
data: {"type": "report", "date": "2026-06-26", "message": "...", ...}

event: prediction
data: {"type": "prediction", ...}
```

Keep-alive automatique toutes les **30 secondes** pour maintenir la connexion.

---

### FCM — Notifications Push

| Méthode | URL | Description |
|---|---|---|
| `POST` | `/api/predictions/fcm/register/` | Enregistrer un token FCM |
| `POST` | `/api/predictions/fcm/send/` | Envoyer une notification push |

**Enregistrement d'un token :**
```json
{
  "token": "fcm_token_unique_...",
  "device_info": "iOS-17.2"
}
```

**Envoi d'une notification :**
```json
{
  "title": "Nouveau rapport disponible",
  "body": "Prévision du 2026-06-27 : 180 visiteurs attendus.",
  "data": { "notification_id": "42" }
}
```

---

### Statistiques

| Méthode | URL | Description |
|---|---|---|
| `GET` | `/api/predictions/stats/` | Compteurs globaux (types, affluence, confiance) |

**Réponse :**
```json
{
  "total": 124,
  "unread_count": 8,
  "by_type": {
    "prediction": 60,
    "report": 55,
    "alert": 6,
    "custom": 3
  },
  "by_affluence": {
    "low": 12,
    "medium": 48,
    "high": 50,
    "very_high": 14
  },
  "recent_avg_confidence": 0.812
}
```

---

## Normalisation des payloads N8N

Le backend normalise automatiquement les valeurs envoyées par N8N :

| Valeur N8N | Valeur stockée |
|---|---|
| `llm_report` | `report` |
| `Élevé` / `eleve` | `high` |
| `Modéré` / `modere` | `medium` |
| `Faible` | `low` |
| `Très élevé` / `tres eleve` | `very_high` |

---

## Fichiers

| Fichier | Rôle |
|---|---|
| `models.py` | `PredictionNotification`, `FCMToken`, `PushNotificationLog` |
| `views.py` | Toutes les vues (notifications, SSE, FCM, stats, webhook N8N) |
| `serializers.py` | Sérialisation list / detail / create / update |
| `fcm_service.py` | Envoi Firebase Cloud Messaging |
| `urls.py` | Routage sous `predictions/` (namespace `n8n_predictions`) |
| `admin.py` | Interface d'administration Django |