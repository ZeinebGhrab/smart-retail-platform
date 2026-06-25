// ============================================================
// frontend/src/hooks/useFirebaseMessaging.ts
// Enregistre le token FCM auprès du backend (POST /api/fcm-token/)
// et écoute les notifications reçues au premier plan.
//
// — Sur Android natif (build Capacitor) : utilise le plugin natif
//   @capacitor-firebase/messaging. C'est le chemin fiable, celui
//   qui fonctionne réellement dans la WebView de l'app installée.
// — Dans un navigateur classique (npm run dev) : utilise le SDK
//   web Firebase (best effort, nécessite VITE_FIREBASE_VAPID_KEY
//   + un fichier public/firebase-messaging-sw.js — à mettre en
//   place séparément si le test depuis un navigateur est utile).
// ============================================================

import { useEffect } from 'react';
import { Capacitor } from '@capacitor/core';
import { FirebaseMessaging } from '@capacitor-firebase/messaging';
import { initializeApp, getApps } from 'firebase/app';
import { getMessaging, getToken, onMessage } from 'firebase/messaging';
import { saveFCMToken } from '../services/fcm';
import { getAccessToken } from '../services/auth';
const firebaseConfig = {
  apiKey:            import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain:        import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId:         import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket:     import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId:             import.meta.env.VITE_FIREBASE_APP_ID,
  measurementId:     import.meta.env.VITE_FIREBASE_MEASUREMENT_ID,
};

// ------------------------------------------------------------
// Chemin natif (Android via Capacitor) — chemin principal de l'app.
// Nécessite frontend/android/app/google-services.json (à récupérer
// depuis Firebase Console → Paramètres du projet → App Android).
// ------------------------------------------------------------
async function registerNative(): Promise<void> {
  const { receive } = await FirebaseMessaging.requestPermissions();
  if (receive !== 'granted') {
    console.warn('Permission de notification refusée (natif).');
    return;
  }

  const { token } = await FirebaseMessaging.getToken();
  if (!token) {
    console.warn("Impossible d'obtenir le token FCM natif.");
    return;
  }

  console.log('FCM Token (natif) :', token);
  await saveFCMToken(token);

  // Notification reçue quand l'app est au PREMIER PLAN
  await FirebaseMessaging.addListener('notificationReceived', (event) => {
    console.log('Notification FCM reçue (foreground, natif) :', event);
  });

  // Notification tappée depuis l'ARRIÈRE-PLAN ou app killed
  await FirebaseMessaging.addListener('notificationActionPerformed', (event) => {
    console.log('Notification tappée (background/killed) :', event);
    // Optionnel : navigation selon le type de notif
    // const action = event.notification.data?.action;
    // if (action === 'view_report') { /* navigate('/dashboard') */ }
    // if (action === 'view_forecast') { /* navigate('/predictions') */ }
  });
}

// ------------------------------------------------------------
// Chemin web (navigateur classique) — best effort, non bloquant.
// ------------------------------------------------------------
async function registerWeb(): Promise<void> {
  if (!('serviceWorker' in navigator)) {
    console.warn('Service Workers non supportés dans ce navigateur.');
    return;
  }

  const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
  const registration = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
  const messaging = getMessaging(app);

  const permission = await Notification.requestPermission();
  if (permission !== 'granted') {
    console.warn('Permission de notification refusée (web).');
    return;
  }

  const token = await getToken(messaging, {
    vapidKey: import.meta.env.VITE_FIREBASE_VAPID_KEY,
    serviceWorkerRegistration: registration,
  });

  if (token) {
    console.log('FCM Token (web) :', token);
    await saveFCMToken(token);
  } else {
    console.warn("Impossible d'obtenir le token FCM web. Vérifier la VAPID key.");
  }

  onMessage(messaging, (payload) => {
    console.log('Message FCM reçu (foreground, web) :', payload);
    if (Notification.permission === 'granted') {
      new Notification(payload.notification?.title || 'ShopAnalytics', {
        body: payload.notification?.body || '',
        icon: '/favicon.png',
        tag: 'fcm-notification',
        data: payload.data,
      });
    }
  });
}

// export const useFirebaseMessaging = () => {
//   useEffect(() => {
//     const initializeMessaging = async () => {
//       try {
//         if (Capacitor.isNativePlatform()) {
//           await registerNative();
//         } else {
//           await registerWeb();
//         }
//       } catch (error) {
//         console.error('Erreur Firebase Messaging:', error);
//       }
//     };

//     initializeMessaging();
//   }, []);
// };
export const useFirebaseMessaging = () => {
  const initializeMessaging = async () => {
    try {
      if (Capacitor.isNativePlatform()) {
        await registerNative();
      } else {
        await registerWeb();
      }
    } catch (error) {
      console.error('Erreur Firebase Messaging:', error);
    }
  };

  // Auto-run au démarrage UNIQUEMENT si déjà connecté
  useEffect(() => {
    
    if (getAccessToken()) {
      initializeMessaging();
    }
  }, []);

  return { initializeMessaging }; // ← exposer pour Login.tsx
};
export default useFirebaseMessaging;