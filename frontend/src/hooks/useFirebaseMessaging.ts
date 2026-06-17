// ============================================================
// frontend/src/hooks/useFirebaseMessaging.ts
// Hook pour enregistrer le token FCM et recevoir les notifications
// ============================================================

import { useEffect } from 'react';

/**
 * Hook pour initialiser Firebase Messaging et enregistrer le token FCM
 * 
 * Installation requise:
 * npm install firebase
 * 
 * Utilisation:
 * import { useFirebaseMessaging } from './hooks/useFirebaseMessaging';
 * 
 * function MyComponent() {
 *   useFirebaseMessaging();
 *   // ...
 * }
 */
export const useFirebaseMessaging = () => {
  useEffect(() => {
    const initializeMessaging = async () => {
      try {
        // 1. Importer Firebase
        const { initializeApp } = await import('firebase/app');
        const { getMessaging, getToken, onMessage } = await import('firebase/messaging');

        // 2. Configuration Firebase
        const firebaseConfig = {
          apiKey: process.env.REACT_APP_FIREBASE_API_KEY || "AIzaSyC...",
          authDomain: process.env.REACT_APP_FIREBASE_AUTH_DOMAIN || "anavid-91d01.firebaseapp.com",
          projectId: process.env.REACT_APP_FIREBASE_PROJECT_ID || "anavid-91d01",
          storageBucket: process.env.REACT_APP_FIREBASE_STORAGE_BUCKET || "anavid-91d01.appspot.com",
          messagingSenderId: process.env.REACT_APP_FIREBASE_MESSAGING_SENDER_ID || "1234567890",
          appId: process.env.REACT_APP_FIREBASE_APP_ID || "1:1234567890:web:...",
        };

        // 3. Initialiser Firebase
        const app = initializeApp(firebaseConfig);

        // 4. Obtenir Messaging
        const messaging = getMessaging(app);

        // 5. Demander la permission et obtenir le token
        const permission = await Notification.requestPermission();
        
        if (permission === 'granted') {
          const token = await getToken(messaging, {
            vapidKey: process.env.REACT_APP_FIREBASE_VAPID_KEY || "BCxx...zz"
          });

          if (token) {
            // 6. Envoyer le token au backend
            await fetch('http://localhost:8000/api/fcm-token/', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ token })
            });

            console.log('FCM Token enregistré:', token);
          }
        } else {
          console.warn('Permission de notification refusée');
        }

        // 7. Écouter les messages en foreground
        onMessage(messaging, (payload) => {
          console.log('Message reçu:', payload);
          
          // Afficher une notification personnalisée
          if (Notification.permission === 'granted') {
            new Notification(payload.notification?.title || 'ShopAnalytics', {
              body: payload.notification?.body || '',
              icon: '/favicon.png',
              tag: 'fcm-notification',
              data: payload.data
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