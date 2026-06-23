/*import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.anavid.shopanalytics',
  appName: 'anavidApp',
  webDir: 'dist',
  // L'app sert son contenu local en http:// au lieu de https://
  // pour que les appels fetch() vers le backend Django en http://
  // (ex: http://192.168.100.14:8000) ne soient plus bloqués par
  // la politique "Mixed Content" du WebView Android.
  server: {
    androidScheme: 'http',
  },
  android: {
    allowMixedContent: true,
  },
};

export default config;*/

import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.anavid.shopanalytics',
  appName: 'anavidApp',
  webDir: 'dist',
  // Pointe vers le backend de déploiement (Azure VM).
  // En développement local, commenter server.url et utiliser
  // VITE_API_URL=http://localhost:8000/api dans frontend/.env
  server: {
    androidScheme: 'http',
    // URL du serveur de déploiement — l'APK chargera le bundle Vite
    // depuis ce serveur au lieu du contenu embarqué local.
    // Retirer cette ligne pour générer un APK standalone (bundle embarqué).
    // url: 'http://40.76.124.14:5173',
    cleartext: true,   // autorise HTTP (non-TLS) vers 40.76.124.14
  },
  android: {
    allowMixedContent: true,
  },
};

export default config;