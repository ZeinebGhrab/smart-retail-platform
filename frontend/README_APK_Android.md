# 📱 AnavidApp — Guide de Génération APK Android

> **Projet :** Anavid Store 360 / ShopAnalytics — Kiabi  
> **Stack :** Ionic React + Vite + Capacitor 6  
> **App ID :** `com.anavid.shopanalytics`  
> **Backend :** Django REST API (Docker)

---

## Prérequis

| Outil | Version | Rôle |
|-------|---------|------|
| Node.js | v22.x (LTS) | Runtime JavaScript |
| npm | v10.x | Gestionnaire de paquets |
| JDK | 17 | Compilation Android |
| Android Studio | Hedgehog+ | Build APK / émulateur |
| Docker Desktop | Dernière | Backend Django + Ollama |
| @capacitor/cli | 6.x (global) | Sync Android |

---

## Structure du projet

```
anavid-smart-retail-platform/
├── frontend/                    ← App Ionic React (Vite)
│   ├── src/
│   ├── android/                 ← Projet Android (généré par Capacitor)
│   ├── dist/                    ← Build web (généré par Vite)
│   ├── capacitor.config.ts      ← Config Capacitor
│   └── .env                     ← Variables d'environnement (non versionné)
└── backend/
    ├── django_api/              ← API REST Django
    └── docker-compose.yml
```

---

## 1. Configuration initiale

### 1.1 Fichier `capacitor.config.ts`

Créer dans `frontend/capacitor.config.ts` :

```typescript
import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.anavid.shopanalytics',
  appName: 'AnavidApp',
  webDir: 'dist',
  server: {
    // Mode développement uniquement — pointer vers l'IP locale du PC
    // Supprimer ce bloc pour un APK de production (le front sera bundlé)
    url: 'http://192.168.100.14:8000',
    cleartext: true
  }
};

export default config;
```

### 1.2 Fichier `frontend/.env`

```env
# URL du backend Django — remplacer par l'IP réelle du PC (pas localhost)
VITE_API_URL=http://192.168.100.14:8000/api

# Firebase / FCM (notifications push)
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=...
VITE_FIREBASE_PROJECT_ID=...
VITE_FIREBASE_STORAGE_BUCKET=...
VITE_FIREBASE_MESSAGING_SENDER_ID=...
VITE_FIREBASE_APP_ID=...
VITE_FIREBASE_MEASUREMENT_ID=...
VITE_FIREBASE_VAPID_KEY=...
```

> ⚠️ Ce fichier ne doit **jamais** être versionné. Il est listé dans `.gitignore`.

### 1.3 Trouver l'IP locale du PC (Windows)

```cmd
ipconfig
```

Chercher **"Carte réseau sans fil Wi-Fi"** → **Adresse IPv4**  
Exemple : `192.168.100.14`

> ⚠️ Le mobile et le PC doivent être sur le **même réseau Wi-Fi**.

---

## 2. Configuration réseau Android (Mixed Content)

Capacitor sert l'app en `https://localhost`. Les requêtes vers `http://` sont bloquées par défaut sur Android (Mixed Content). Il faut autoriser le trafic HTTP vers l'IP du backend.

### 2.1 Créer le fichier de sécurité réseau

Créer `frontend/android/app/src/main/res/xml/network_security_config.xml` :

```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="true">192.168.100.14</domain>
    </domain-config>
</network-security-config>
```

> Remplacer `192.168.100.14` par l'IP réelle du PC si elle change.

### 2.2 Référencer dans `AndroidManifest.xml`

Fichier : `frontend/android/app/src/main/AndroidManifest.xml`

Dans la balise `<application>`, ajouter :

```xml
<application
    android:networkSecurityConfig="@xml/network_security_config"
    android:label="@string/app_name"
    ... >
```

---

## 3. Build et génération APK

### 3.1 Installer les dépendances

```cmd
cd frontend
npm install
npm install axios
```

### 3.2 Build web

```cmd
npm run build
```

✅ Vérifie que le dossier `dist/` est bien créé avec `index.html`.

### 3.3 Initialiser Capacitor (première fois uniquement)

```cmd
npm install -g @capacitor/cli
cap init anavidApp com.anavid.shopanalytics --web-dir dist
cap add android
```

### 3.4 Synchroniser le projet Android

```cmd
cap sync android
```

À refaire **à chaque modification** du code front.

### 3.5 Ouvrir dans Android Studio

```cmd
cap open android
```

Attendre la fin du **Gradle sync** (barre de progression en bas d'Android Studio).

### 3.6 Générer l'APK debug

Dans Android Studio :

```
Build → Build Bundle(s) / APK(s) → Build APK(s)
```

APK généré dans :
```
frontend/android/app/build/outputs/apk/debug/app-debug.apk
```

---

## 4. Lancement direct sur téléphone (sans APK)

### 4.1 Activer le débogage USB sur le téléphone

1. **Paramètres → À propos du téléphone**
2. Appuyer **7 fois** sur **"Numéro de build"**
3. **Paramètres → Options développeur → Activer le débogage USB**
4. Brancher le câble USB → Accepter la popup sur le téléphone

### 4.2 Lancer depuis Android Studio

En haut d'Android Studio :

```
[app ▼]  [Nom du téléphone ▼]  ▶ Run
```

Sélectionner le téléphone → Cliquer sur **▶ (triangle vert)**.

### 4.3 Vérifier la détection ADB

```cmd
adb devices
```

Résultat attendu :
```
List of devices attached
XXXXXXXX    device
```

---

## 5. Démarrer le backend

```cmd
# Depuis la racine du projet
docker compose up django_api
```

Vérifier l'accès depuis le navigateur PC :
```
http://192.168.100.14:8000/api/auth/login/
```
→ Doit retourner une réponse JSON Django.

### Ouvrir le port 8000 dans le firewall Windows (si nécessaire)

```cmd
# CMD en mode Administrateur
netsh advfirewall firewall add rule name="Django 8000" dir=in action=allow protocol=TCP localport=8000
```

---

## 6. Workflow de mise à jour

À chaque modification du code frontend :

```cmd
cd frontend
npm run build
cap sync android
# Puis dans Android Studio → Build APK ou ▶ Run
```

---

## 7. APK Release (production)

Dans Android Studio :

```
Build → Generate Signed Bundle / APK → APK
```

1. Créer un **keystore JKS** (à conserver précieusement)
2. Signer l'APK
3. APK généré : `app-release.apk`

> ⚠️ Pour la production, supprimer le bloc `server` dans `capacitor.config.ts` — le front sera bundlé dans l'APK.

---

## 8. Plugins Capacitor installés

| Plugin | Version | Fonction |
|--------|---------|----------|
| `@capacitor/android` | 6.2.1 | Plateforme Android |
| `@capacitor/app` | 6.0.3 | Gestion lifecycle |
| `@capacitor/haptics` | 6.0.3 | Retour haptique |
| `@capacitor/keyboard` | 6.0.4 | Gestion clavier |
| `@capacitor/status-bar` | 6.0.3 | Barre de statut |
| `@capacitor-firebase/messaging` | 6.3.1 | Notifications push FCM |

---

## 9. Résolution des problèmes courants

| Erreur | Cause | Solution |
|--------|-------|----------|
| `tsc not recognized` | `node_modules` absent | `npm install` |
| `npx cap: could not determine executable` | CLI non installé | `npm install -g @capacitor/cli` |
| `Mixed Content blocked` | HTTP depuis HTTPS | Ajouter `network_security_config.xml` |
| `Cannot find module 'axios'` | Dépendance manquante | `npm install axios` |
| Téléphone non détecté | Débogage USB désactivé | Activer dans Options développeur |
| Connexion refusée depuis mobile | Mauvaise IP ou firewall | Vérifier IP + ouvrir port 8000 |
| Gradle sync échoue | JDK manquant ou mauvaise version | Installer JDK 17 |

---

## 10. Informations de build

| Paramètre | Valeur |
|-----------|--------|
| App Name | AnavidApp |
| App ID | `com.anavid.shopanalytics` |
| Web Dir | `dist/` |
| Backend URL (dev) | `http://192.168.100.14:8000/api` |
| Capacitor version | 6.x |
| Android min SDK | 22 |
| Target SDK | 36 |

---

*Document généré pour le projet Anavid Store 360 — Sprint 0 — Kiabi*
