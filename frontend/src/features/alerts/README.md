# `features/alerts/` — Alertes de sécurité (vidéo)

Écrans protégés affichant et qualifiant les alertes de vol/comportement suspect détectées par le modèle ML et relayées via un bot Telegram.

## `Alerts.tsx` + `Alerts.css` (route `/alerts`)

Liste paginée des alertes, avec filtres par statut (`tous`, `en_attente`, `vol_confirme_interpelle`, `comportement_suspect`, `fausse_alerte`).

## `AlertDetail.tsx` + `AlertDetail.css` (route `/alerts/:id`)

Détail d'une alerte : vidéo/miniature, métadonnées (caméra, lieu, confiance), et action de qualification manuelle (`qualifyAlert`) si elle n'a pas déjà été qualifiée depuis Telegram.

## `alert.model.ts` — Modèle de données

Types alignés sur le contenu envoyé par le bot Telegram (ex. tag brut `#Cam_23_MG_Ennasser_20260609-202622223137`) :

| Export | Description |
|---|---|
| `AlertStatus` | Union des 5 statuts possibles (`en_attente`, `vol_confirme_interpelle`, `vol_confirme_non_interpelle`, `comportement_suspect`, `fausse_alerte`), correspondant chacun à un bouton du bot Telegram |
| `SecurityAlert` | Forme complète d'une alerte côté frontend (caméra, lieu, confiance, vidéo, statut, qui l'a qualifiée...) |
| `ALERT_STATUS_LABELS` | Libellés français affichés pour chaque `AlertStatus` |


## `alerts.api.ts` — Client API

Appels HTTP vers le backend Django (`/api/history/video-alerts/...`), avec mapping des champs bruts de la base vers `SecurityAlert`.

| Export | Rôle |
|---|---|
| `AlertsPage` | Forme d'une réponse paginée (`count`, `limit`, `offset`, `results`) |
| `FILTER_TO_QUALIFICATION` | Table de correspondance filtre frontend (`tous`, `en_attente`, ...) → valeur `qualification` côté backend |
| `fetchAlerts(options)` | Récupère une page d'alertes, avec filtres optionnels (espace, organisation, statut) |
| `fetchAlertById(id)` | Récupère le détail d'une alerte |
| `qualifyAlert(id, status)` | Qualifie manuellement une alerte depuis l'app |
| `fetchSpaces()` | Liste les espaces/caméras disponibles (pour les filtres) |


## Dépendances transverses utilisées

- `../../services/auth.ts` — `getAccessToken()` (authentification des requêtes)

## Pourquoi `alert.model.ts` et `alerts.api.ts` sont colocalisés avec les écrans

Ces deux fichiers ne sont consommés que par `Alerts.tsx` et `AlertDetail.tsx` — aucun autre domaine ne les importe. Les regrouper dans `features/alerts/` évite d'avoir à chercher dans `services/` pour des fichiers qui ne concernent qu'un seul écran, et le renommage lève l'ambiguïté singulier/pluriel qui existait auparavant.