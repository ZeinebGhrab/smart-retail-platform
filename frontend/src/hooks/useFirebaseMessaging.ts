// ============================================================
// frontend/src/hooks/useFirebaseMessaging.ts
// Hook pour enregistrer le token FCM et recevoir les notifications
// ============================================================

import { useEffect } from 'react';
import { initializeApp, getApps } from 'firebase/app';
import { getMessaging, getToken, onMessage } from 'firebase/messaging';

const firebaseConfig = {
  apiKey:            import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain:        import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId:         import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket:     import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId:             import.meta.env.VITE_FIREBASE_APP_ID,
  measurementId:     import.meta.env.VITE_FIREBASE_MEASUREMENT_ID,
};

// Initialiser Firebase une seule fois (évite les doublons en HMR Vite)
const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];

export const useFirebaseMessaging = () => {
  useEffect(() => {
    const initializeMessaging = async () => {
      try {
        if (!('serviceWorker' in navigator)) {
          console.warn('Service Workers non supportés dans ce navigateur.');
          return;
        }

        // Enregistrer le Service Worker FCM (obligatoire pour getToken)
        const registration = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
        console.log('Service Worker FCM enregistré:', registration.scope);

        const messaging = getMessaging(app);

        // Demander la permission de notification
        const permission = await Notification.requestPermission();
        if (permission !== 'granted') {
          console.warn('Permission de notification refusée');
          return;
        }

        // Obtenir le token FCM
        const token = await getToken(messaging, {
          vapidKey: import.meta.env.VITE_FIREBASE_VAPID_KEY,
          serviceWorkerRegistration: registration,
        });

        if (token) {
          console.log('FCM Token:', token);
          await fetch(`${import.meta.env.VITE_API_URL}/fcm-token/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token }),
          });
          console.log('Token FCM enregistré sur le backend');
        } else {
          console.warn("Impossible d'obtenir le token FCM. Vérifier la VAPID key et le Service Worker.");
        }

        // Écouter les messages reçus en foreground
        onMessage(messaging, (payload) => {
          console.log('Message FCM reçu (foreground):', payload);
          if (Notification.permission === 'granted') {
            new Notification(payload.notification?.title || 'ShopAnalytics', {
              body: payload.notification?.body || '',
              icon: '/favicon.png',
              tag: 'fcm-notification',
              data: payload.data,
            });
          }
        });

      } catch (error) {
        console.error('Erreur Firebase Messaging:', error);
      }
    };

    initializeMessaging();
  }, []);
};

export default useFirebaseMessaging;