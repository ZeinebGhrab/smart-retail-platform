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
  server: {
    androidScheme: 'http',
    url: 'http://40.76.124.14:5173',  
    cleartext: true,
  },
  android: {
    allowMixedContent: true,
  },
};

export default config;