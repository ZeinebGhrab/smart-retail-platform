# `hooks/` — Hooks React transverses

Hooks utilisés indépendamment d'un écran précis. À distinguer des hooks spécifiques à un seul domaine (ex. `useSSEPrediction.ts`, utilisé uniquement par le Dashboard, qui vit dans `../features/dashboard/`).

## `useFirebaseMessaging.ts`

Hook qui enregistre l'appareil pour les notifications push **Firebase Cloud Messaging (FCM)** et écoute les notifications reçues au premier plan. Appelé dans `../app/App.tsx` (une seule fois au démarrage) et dans `../features/auth/Login.tsx` (après connexion).

```ts
useFirebaseMessaging();
```

Aucune valeur retournée — effet de bord uniquement (enregistrement + listeners).

**Fonctionnement :** détecte la plateforme via `Capacitor.isNativePlatform()` et choisit l'un des deux chemins suivants :

| Plateforme | Chemin | Dépendances |
|---|---|---|
| Android natif (APK installé) | `@capacitor-firebase/messaging` — demande la permission, récupère le token natif, l'envoie au backend via `../services/fcm.ts::saveFCMToken`, puis écoute `notificationReceived` et `notificationActionPerformed` | `frontend/android/app/google-services.json` |
| Navigateur classique (`npm run dev`) | SDK Firebase Web (`firebase/messaging`) — best effort, non bloquant | `VITE_FIREBASE_VAPID_KEY` + un fichier `public/firebase-messaging-sw.js` (non fourni par défaut dans ce repo) |

Procédure complète de configuration FCM (récupération des clés, `google-services.json`, Service Account backend) : voir [`frontend/README_APK_Android.md` section 4](../../README_APK_Android.md#4-configuration-fcm-firebase-cloud-messaging).

