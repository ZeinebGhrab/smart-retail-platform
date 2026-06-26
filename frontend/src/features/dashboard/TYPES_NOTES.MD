# `types/` — Types TypeScript partagés

## `dashboard.types.ts`

Types utilisés par `dashboard/Dashboard.tsx` et les composants associés (`dashboard/useSSEPrediction.ts`, `../components/Notifications.tsx`).

| Type | Description |
|---|---|
| `KPIData` | Indicateurs clés affichés en haut du Dashboard (visiteurs, chiffre d'affaires, taux de conversion, alertes), chacun avec sa variation vs période précédente |
| `IntradayPoint` | Un point du graphique de flux horaire (heure, valeur du jour, valeur hier) |
| `PredictionData` | Forme exacte du payload reçu via SSE (`/api/prediction/stream/`) — doit rester synchronisée avec le payload envoyé par le workflow N8N et reçu par `daily_report` côté Django (voir `backend/django_api/history/README.md`) |
| `AlertSeverity` | Union `'critical' \| 'warning' \| 'info'` — niveau de gravité d'une alerte |
| `AlertItem` | Une alerte affichée dans le panneau d'alertes du Dashboard |
| `NotifIconType` | Union de couleurs d'icône (`'red' \| 'amber' \| 'green' \| 'blue' \| ''`) |
| `NotificationItem` | Format générique d'une notification affichée côté Dashboard (distinct du type `Notification` interne à `../components/Notifications.tsx`, plus détaillé) |

> Les types métier de l'historique/analytics (`VisitorHistoryResponse`, `SummaryResponse`, etc.) ne sont **pas** ici : ils sont colocalisés avec leurs fonctions dans `services/api.ts`. Ce dossier ne contient que les types réutilisés à travers plusieurs fichiers sans fonction associée évidente.
