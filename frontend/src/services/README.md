# `services/` — Clients HTTP vers le backend

Couche d'accès réseau : fonctions `fetch` typées, sans aucune logique d'affichage. Les écrans et composants n'appellent jamais `fetch()` directement (sauf cas isolés documentés dans `features/README.md`) — ils passent par ces services ou par les fichiers `*.api.ts` locaux à un domaine (voir `features/`).

## `api.ts` — Client analytics

Définit `API_BASE_URL` (lu depuis `VITE_API_URL`, voir `.env`) et expose les fonctions consommant les endpoints `/api/history/*` :

| Fonction | Endpoint |
|---|---|
| `getVisitorHistory()` | `GET /api/history/visitors/` |
| `getVisitorCount()` | `GET /api/history/visitors/count/` |
| `getHourlyFlow()` | `GET /api/history/visitors/hourly/` |
| `getForecast()` | `GET /api/history/visitors/forecast/` |
| `getSummary()` | `GET /api/history/summary/` |
| `getCameras()` | `GET /api/history/cameras/` |

Toutes les réponses sont typées (`VisitorHistoryResponse`, `SummaryResponse`, etc.) et exportées pour être réutilisées dans `features/dashboard/` et `features/historique/`.

## `auth.ts` — Client authentification + session locale

Consomme les endpoints `/api/auth/*` et gère la persistance de session côté client.

| Fonction | Rôle |
|---|---|
| `register(fields)` | `POST /api/auth/register/` |
| `login(email, password, remember)` | `POST /api/auth/login/`, puis sauvegarde la session via `saveSession()` |
| `logout()` | `POST /api/auth/logout/` (blackliste le refresh token), puis `clearSession()` |
| `getMe()` | `GET /api/auth/me/` |
| `requestPasswordReset(email)` | `POST /api/auth/password-reset/request/` |
| `verifyResetCode(email, code)` | `POST /api/auth/password-reset/verify/` |
| `confirmPasswordReset(...)` | `POST /api/auth/password-reset/confirm/` |
| `isAuthenticated()` | Vrai si un token d'accès est présent localement |
| `saveSession()` / `clearSession()` | Écrit/efface `anavid_access_token`, `anavid_refresh_token`, `anavid_user` |

**Stockage de session :** si `remember = true` (case cochée sur `Login.tsx`), les tokens sont écrits dans `localStorage` (persistent après fermeture du navigateur) ; sinon dans `sessionStorage` (effacés à la fermeture de l'onglet). Les deux storages sont systématiquement nettoyés avant chaque nouvelle écriture pour éviter un état incohérent.

Les erreurs API sont normalisées via la classe `AuthApiError`, qui convertit les clés d'erreur du backend (`snake_case`, ex. `first_name`) en clés `camelCase` (`firstName`) directement utilisables dans le state des formulaires React.


## `fcm.ts` — Client notifications push (FCM)

Consomme les endpoints `/api/fcm-token/` et `/api/send-fcm/` côté backend.

| Fonction | Endpoint / rôle |
|---|---|
| `saveFCMToken(token)` | `POST /api/fcm-token/` — enregistre le token de l'appareil après obtention via `hooks/useFirebaseMessaging.ts` |
| `sendFCMNotification(title, body, data?)` | `POST /api/send-fcm/` — envoie une notification push à tous les appareils enregistrés |
| `notifyReportGenerated(reportDate, summary)` | Raccourci : notification "📊 Nouveau Rapport" |
| `notifyForecastAvailable(date, visitorCount)` | Raccourci : notification "🔮 Prévision Disponible" |
| `sendAlert(alertType, message)` | Raccourci : notification "⚠️ Alerte ShopAnalytics" |

Configuration complète (clés Firebase frontend, Service Account backend, `google-services.json`) : voir [`frontend/README_APK_Android.md` section 4](../../README_APK_Android.md#4-configuration-fcm-firebase-cloud-messaging).