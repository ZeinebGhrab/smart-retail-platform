# `hooks/` — Hooks React personnalisés

## `useSSEPrediction.ts`

Hook qui ouvre et maintient une connexion **Server-Sent Events (SSE)** vers le backend Django pour recevoir en temps réel les rapports prédictifs générés chaque matin par le workflow N8N.

```ts
const { prediction, isConnected, lastReceivedAt, error } = useSSEPrediction();
```

| Valeur retournée | Type | Description |
|---|---|---|
| `prediction` | `PredictionData \| null` | Dernier rapport reçu (voir `types/dashboard.types.ts`) |
| `isConnected` | `boolean` | État de la connexion SSE |
| `lastReceivedAt` | `Date \| null` | Horodatage de la dernière réception |
| `error` | `string \| null` | Message d'erreur si la connexion échoue |

**Fonctionnement :**
1. Ouvre une connexion `EventSource` vers `GET ${VITE_API_URL}/prediction/stream/`.
2. Écoute l'événement nommé `llm_report` (et non l'événement par défaut `message`) — voir la note dans le code source qui souligne ce point, car une erreur fréquente est d'utiliser `onmessage` au lieu de `addEventListener('llm_report', ...)`.
3. Le serveur (Django, `history/views.py::sse_stream`) émet un heartbeat de connexion puis un `keepalive` toutes les 30 secondes ; le payload `llm_report` n'arrive que lorsque N8N poste sur `POST /api/daily-report/`.

**Consommé par :** `pages/Dashboard.tsx`, pour afficher la prévision de fréquentation et les alertes du jour sans rechargement de page.

---

## `useFirebaseMessaging.ts`

Hook qui enregistre l'appareil pour les notifications push **Firebase Cloud Messaging (FCM)** et écoute les notifications reçues au premier plan. Appelé une seule fois dans `App.tsx`.

```ts
useFirebaseMessaging();
```

Aucune valeur retournée — effet de bord uniquement (enregistrement + listeners).

**Fonctionnement :** détecte la plateforme via `Capacitor.isNativePlatform()` et choisit l'un des deux chemins suivants :

| Plateforme | Chemin | Dépendances |
|---|---|---|
| Android natif (APK installé) | `@capacitor-firebase/messaging` — demande la permission, récupère le token natif, l'envoie au backend via `services/fcm.ts::saveFCMToken`, puis écoute `notificationReceived` et `notificationActionPerformed` | `frontend/android/app/google-services.json` |
| Navigateur classique (`npm run dev`) | SDK Firebase Web (`firebase/messaging`) — best effort, non bloquant | `VITE_FIREBASE_VAPID_KEY` + un fichier `public/firebase-messaging-sw.js` (non fourni par défaut dans ce repo) |

Procédure complète de configuration FCM (récupération des clés, `google-services.json`, Service Account backend) : voir [`frontend/README_APK_Android.md` section 4](../../README_APK_Android.md#4-configuration-fcm-firebase-cloud-messaging).