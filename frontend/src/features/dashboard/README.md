# `features/dashboard/` — Tableau de bord

Écran d'accueil après connexion (route `/dashboard`, protégée par `PrivateRoute`).

## `Dashboard.tsx` + `Dashboard.css`

Combine :
- KPIs (visiteurs, taux de conversion, alertes) et graphique de flux horaire (Chart.js `Line`)
- Prévision de fréquentation du jour reçue en temps réel via `useSSEPrediction()` (flux SSE)
- Cloche de notifications (`../../components/Notifications.tsx`)

> ⚠️ La variable CSS `--db-bg` définie dans `Dashboard.css` doit rester synchronisée avec `--ion-background-color` dans `../../theme/variables.css` — les deux représentent le même fond global et sont dupliquées pour des raisons de portée CSS.

## `useSSEPrediction.ts`

Hook qui ouvre et maintient une connexion **Server-Sent Events (SSE)** vers le backend Django pour recevoir en temps réel les rapports prédictifs générés chaque matin par le workflow N8N.

```ts
const { prediction, isConnected, lastReceivedAt, error } = useSSEPrediction();
```

| Valeur retournée | Type | Description |
|---|---|---|
| `prediction` | `PredictionData \| null` | Dernier rapport reçu (voir `dashboard.types.ts`) |
| `isConnected` | `boolean` | État de la connexion SSE |
| `lastReceivedAt` | `Date \| null` | Horodatage de la dernière réception |
| `error` | `string \| null` | Message d'erreur si la connexion échoue |

**Fonctionnement :**
1. Ouvre une connexion `EventSource` vers `GET ${VITE_API_URL}/prediction/stream/`.
2. Écoute l'événement nommé `llm_report` (et non l'événement par défaut `message`) — une erreur fréquente est d'utiliser `onmessage` au lieu de `addEventListener('llm_report', ...)`.
3. Le serveur (Django, `history/views.py::sse_stream`) émet un heartbeat de connexion puis un `keepalive` toutes les 30 secondes ; le payload `llm_report` n'arrive que lorsque N8N poste sur `POST /api/daily-report/`.

Utilisé uniquement par `Dashboard.tsx`.

## `dashboard.types.ts`

Types utilisés par `Dashboard.tsx`, `useSSEPrediction.ts`, et indirectement par `../../components/Notifications.tsx`.

| Type | Description |
|---|---|
| `KPIData` | Indicateurs clés affichés en haut du Dashboard (visiteurs, chiffre d'affaires, taux de conversion, alertes), chacun avec sa variation vs période précédente |
| `IntradayPoint` | Un point du graphique de flux horaire (heure, valeur du jour, valeur hier) |
| `PredictionData` | Forme exacte du payload reçu via SSE (`/api/prediction/stream/`) — doit rester synchronisée avec le payload envoyé par le workflow N8N et reçu par `daily_report` côté Django (voir `backend/django_api/history/README.md`) |
| `AlertSeverity` | Union `'critical' \| 'warning' \| 'info'` — niveau de gravité d'une alerte |
| `AlertItem` | Une alerte affichée dans le panneau d'alertes du Dashboard |
| `NotifIconType` | Union de couleurs d'icône (`'red' \| 'amber' \| 'green' \| 'blue' \| ''`) |
| `NotificationItem` | Format générique d'une notification affichée côté Dashboard (distinct du type `Notification` interne à `components/Notifications.tsx`, plus détaillé) |

> Les types métier de l'historique/analytics (`VisitorHistoryResponse`, `SummaryResponse`, etc.) ne sont **pas** ici : ils sont colocalisés avec leurs fonctions dans `../../services/api.ts`. Ce fichier ne contient que les types réutilisés à travers plusieurs fichiers sans fonction associée évidente.

## Pourquoi ces 3 fichiers forment un domaine

`useSSEPrediction.ts` et `dashboard.types.ts` n'ont qu'un seul consommateur réel (`Dashboard.tsx`) — les coupler dans le même dossier évite d'avoir à chercher dans `hooks/` et `types/` séparés pour comprendre un seul écran.