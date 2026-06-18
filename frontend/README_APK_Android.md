# 📱 AnavidApp — Guide de Génération APK Android & Configuration FCM

> **Projet :** Anavid Store 360 / ShopAnalytics — Kiabi
> **Stack :** Ionic React + Vite + Capacitor 6
> **App ID :** `com.anavid.shopanalytics`
> **Backend :** Django REST API (Docker)

---

## Sommaire

1. [Prérequis](#1-prérequis)
2. [Structure du projet](#2-structure-du-projet)
3. [Configuration initiale](#3-configuration-initiale)
4. [Configuration FCM (Firebase Cloud Messaging)](#4-configuration-fcm-firebase-cloud-messaging)
5. [Réseau Android — appels HTTP vers le backend](#5-réseau-android--appels-http-vers-le-backend)
6. [Build et génération APK](#6-build-et-génération-apk)
7. [Lancement direct sur téléphone (sans APK)](#7-lancement-direct-sur-téléphone-sans-apk)
8. [Démarrer le backend](#8-démarrer-le-backend)
9. [Workflow de mise à jour rapide](#9-workflow-de-mise-à-jour-rapide)
10. [APK Release (production)](#10-apk-release-production)
11. [Plugins Capacitor installés](#11-plugins-capacitor-installés)
12. [Résolution des problèmes courants](#12-résolution-des-problèmes-courants)
13. [Informations de build](#13-informations-de-build)

---

## 1. Prérequis

| Outil | Version | Rôle |
|-------|---------|------|
| Node.js | v20 ou v22 (LTS) | Runtime JavaScript |
| npm | v10.x | Gestionnaire de paquets |
| JDK | 17 | Compilation Android |
| Android Studio | Hedgehog (2023.1) ou plus récent | Build APK / émulateur |
| Docker Desktop | Dernière | Backend Django + Ollama |
| @capacitor/cli | 6.x (installé en local via `npm install`) | Sync Android |
| Compte Firebase | — | Notifications push (FCM) |

> Le projet contient déjà le dossier `frontend/android/` (généré par Capacitor). Il n'est donc **pas nécessaire** de refaire `cap add android` sauf si ce dossier est supprimé.

---

## 2. Structure du projet

```
smart-retail-platform/
├── frontend/                          ← App Ionic React (Vite)
│   ├── src/
│   │   ├── hooks/useFirebaseMessaging.ts   ← Enregistrement token FCM + listeners
│   │   └── services/fcm.ts                 ← Appels HTTP vers /api/fcm-token/ et /api/send-fcm/
│   ├── android/                       ← Projet Android natif (généré par Capacitor)
│   │   └── app/
│   │       ├── google-services.json   ← À AJOUTER (voir §4) — non versionné
│   │       └── src/main/AndroidManifest.xml
│   ├── dist/                          ← Build web (généré par `npm run build`)
│   ├── capacitor.config.ts            ← Config Capacitor (déjà en place, voir §5)
│   └── .env                           ← Variables d'environnement — À CRÉER (non versionné)
└── backend/
    ├── django_api/                    ← API REST Django (lit FCM_* depuis l'environnement)
    └── docker-compose.yml             ← Variables FCM_* injectées depuis le .env racine
```

---

## 3. Configuration initiale

### 3.1 Fichier `frontend/capacitor.config.ts` (déjà présent)

Ce fichier existe déjà dans le repo et ne nécessite **aucune modification** pour builder l'APK :

```typescript
import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.anavid.shopanalytics',
  appName: 'anavidApp',
  webDir: 'dist',
  // L'app sert son contenu local en http:// au lieu de https://
  // pour que les appels fetch() vers le backend Django en http://
  // ne soient plus bloqués par la politique "Mixed Content" du WebView Android.
  server: {
    androidScheme: 'http',
  },
  android: {
    allowMixedContent: true,
  },
};

export default config;
```

> ⚠️ Ce fichier ne pointe **pas** vers une IP de développement (pas de `server.url`). L'app embarque le build web (`dist/`) directement dans l'APK : c'est `VITE_API_URL` dans le `.env` qui détermine l'adresse du backend appelée au runtime (voir §3.2).

### 3.2 Créer le fichier `frontend/.env`

Ce fichier n'existe pas par défaut (il est listé dans `.gitignore`, jamais commité). Le créer à la racine de `frontend/` :

```env
# ============================================================
# frontend/.env — Variables d'environnement (NE JAMAIS COMMITER)
# ============================================================

# ── URL du backend Django ────────────────────────────────────
# Remplacer par l'IP LAN réelle du PC qui héberge Docker
# (PAS localhost / 127.0.0.1 — le téléphone ne peut pas s'y connecter)
VITE_API_URL=http://192.168.100.14:8000/api

# ── Firebase / FCM (notifications push) — voir section 4 ────
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=...
VITE_FIREBASE_PROJECT_ID=...
VITE_FIREBASE_STORAGE_BUCKET=...
VITE_FIREBASE_MESSAGING_SENDER_ID=...
VITE_FIREBASE_APP_ID=...
VITE_FIREBASE_MEASUREMENT_ID=...
VITE_FIREBASE_VAPID_KEY=...
```

> Un exemple complet et commenté est fourni dans `frontend/.env.example` (voir §4 pour le détail de chaque variable Firebase).

### 3.3 Trouver l'IP locale du PC

**Windows :**
```cmd
ipconfig
```
Chercher **"Carte réseau sans fil Wi-Fi"** → **Adresse IPv4** (ex. `192.168.100.14`).

**macOS / Linux :**
```bash
ipconfig getifaddr en0   # macOS, Wi-Fi
# ou
hostname -I               # Linux
```

> ⚠️ Le mobile et le PC doivent être connectés au **même réseau Wi-Fi**. Si l'IP du PC change (redémarrage, autre réseau), il faut mettre à jour `VITE_API_URL` dans `frontend/.env` puis refaire un build (§6).

---

## 4. Configuration FCM (Firebase Cloud Messaging)

Les notifications push utilisent **deux jeux de clés Firebase distincts** : des clés **côté frontend** (publiques, pour que l'app reçoive les notifications) et un **Service Account côté backend** (privé, pour que Django puisse envoyer des notifications via l'API FCM v1). Les deux sont nécessaires.

### 4.1 Créer / ouvrir le projet Firebase

1. Aller sur [console.firebase.google.com](https://console.firebase.google.com)
2. Créer un projet (ou ouvrir le projet existant, ex. `shop-analytics-anavid`)
3. Activer **Cloud Messaging** : `Paramètres du projet` (⚙️) → onglet **Cloud Messaging**

### 4.2 Ajouter l'application Android au projet Firebase

1. Dans `Paramètres du projet` → onglet **Général** → section **Vos applications** → **Ajouter une application** → icône Android
2. Renseigner le **nom de package Android** exactement : `com.anavid.shopanalytics`
3. Télécharger le fichier généré **`google-services.json`**
4. Placer ce fichier dans :
   ```
   frontend/android/app/google-services.json
   ```
   > Ce fichier est listé dans `.gitignore` (`frontend/android/app/google-services.json`) — il ne doit **jamais** être commité car il identifie le projet Firebase. Chaque développeur doit le télécharger lui-même depuis la Console Firebase.

5. Vérifier que `frontend/android/app/build.gradle` applique bien le plugin Google Services (déjà configuré dans le repo) :
   ```gradle
   try {
       def servicesJSON = file('google-services.json')
       if (servicesJSON.text) {
           apply plugin: 'com.google.gms.google-services'
       }
   } catch(Exception e) {
       logger.info("google-services.json not found, google-services plugin not applied.")
   }
   ```
   Si ce fichier est absent, l'app compile quand même mais **FCM ne fonctionnera pas** (le plugin n'est pas appliqué).

### 4.3 Récupérer les clés Web Firebase (variables `VITE_FIREBASE_*`)

Ces clés alimentent le SDK Firebase Web utilisé par `frontend/src/hooks/useFirebaseMessaging.ts` :

1. `Paramètres du projet` → **Général** → section **Vos applications** → ajouter une application **Web** (`</>`) si ce n'est pas déjà fait (nom libre, ex. `anavidApp-web`)
2. Firebase affiche un objet de config JavaScript — en extraire les valeurs vers `frontend/.env` :

| Variable `.env` | Provient de (objet `firebaseConfig`) |
|---|---|
| `VITE_FIREBASE_API_KEY` | `apiKey` |
| `VITE_FIREBASE_AUTH_DOMAIN` | `authDomain` |
| `VITE_FIREBASE_PROJECT_ID` | `projectId` |
| `VITE_FIREBASE_STORAGE_BUCKET` | `storageBucket` |
| `VITE_FIREBASE_MESSAGING_SENDER_ID` | `messagingSenderId` |
| `VITE_FIREBASE_APP_ID` | `appId` |
| `VITE_FIREBASE_MEASUREMENT_ID` | `measurementId` |

### 4.4 Générer la clé VAPID (`VITE_FIREBASE_VAPID_KEY`)

1. `Paramètres du projet` → onglet **Cloud Messaging**
2. Section **Configuration Web** → **Certificats Web Push** → **Générer une paire de clés**
3. Copier la clé générée dans `VITE_FIREBASE_VAPID_KEY`

> Cette clé n'est utilisée que par le chemin **navigateur web** (`registerWeb()` dans `useFirebaseMessaging.ts`). Sur l'APK Android natif, c'est le plugin `@capacitor-firebase/messaging` qui gère le token via `google-services.json` — la VAPID key n'intervient pas dans ce chemin, mais il est recommandé de la renseigner quand même pour que le mode `npm run dev` (test navigateur) fonctionne aussi.

### 4.5 Générer le Service Account (côté backend — `FCM_*`)

Le backend Django a besoin d'un compte de service pour pouvoir **envoyer** des notifications (endpoint `POST /api/send-fcm/`), distinct des clés ci-dessus qui ne servent qu'à **recevoir**.

1. `Paramètres du projet` → onglet **Comptes de service**
2. **Générer une nouvelle clé privée** → confirmer → un fichier JSON est téléchargé, de la forme :
   ```json
   {
     "type": "service_account",
     "project_id": "shop-analytics-anavid",
     "private_key_id": "...",
     "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
     "client_email": "firebase-adminsdk-fbsvc@shop-analytics-anavid.iam.gserviceaccount.com",
     ...
   }
   ```
3. Reporter trois champs de ce JSON dans le fichier **`.env` à la racine du projet** (celui lu par `docker compose`, pas `frontend/.env`) :

| Variable `.env` (racine) | Provient du JSON Service Account |
|---|---|
| `FCM_PROJECT_ID` | `project_id` |
| `FCM_CLIENT_EMAIL` | `client_email` |
| `FCM_PRIVATE_KEY` | `private_key` (voir format ci-dessous) |

**Format de `FCM_PRIVATE_KEY` dans le `.env`** — la clé doit rester sur **une seule ligne**, avec les retours à la ligne encodés en `\n` littéral, entourée de guillemets doubles :

```env
FCM_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgw...\n-----END PRIVATE KEY-----\n"
```

> Le backend (`backend/django_api/history/views.py`) fait `FCM_PRIVATE_KEY.replace("\\n", "\n")` au chargement pour reconstituer le format PEM attendu par la librairie de signature JWT. Si la clé est copiée-collée avec de **vrais** retours à la ligne au lieu de `\n` littéraux, Docker Compose tronquera la variable et l'authentification FCM échouera (`FCM_PRIVATE_KEY invalide ou mal formatée`).

4. **Ne jamais committer ce fichier JSON ni le `.env`.** Le `.gitignore` du projet exclut déjà `backend/django_api/firebase-credentials.json` et tous les `.env*` sauf `.env.example`.

### 4.6 Variables FCM — résumé complet

| Fichier | Variable | Usage | Qui la lit |
|---|---|---|---|
| `frontend/.env` | `VITE_FIREBASE_API_KEY` | Identifie le projet Firebase côté client | SDK Firebase Web (`useFirebaseMessaging.ts`) |
| `frontend/.env` | `VITE_FIREBASE_AUTH_DOMAIN` | Domaine d'auth Firebase | idem |
| `frontend/.env` | `VITE_FIREBASE_PROJECT_ID` | ID du projet Firebase | idem |
| `frontend/.env` | `VITE_FIREBASE_STORAGE_BUCKET` | Bucket de stockage | idem |
| `frontend/.env` | `VITE_FIREBASE_MESSAGING_SENDER_ID` | Sender ID FCM | idem |
| `frontend/.env` | `VITE_FIREBASE_APP_ID` | ID de l'app Firebase Web | idem |
| `frontend/.env` | `VITE_FIREBASE_MEASUREMENT_ID` | Google Analytics (optionnel) | idem |
| `frontend/.env` | `VITE_FIREBASE_VAPID_KEY` | Clé Web Push (chemin navigateur uniquement) | `registerWeb()` |
| `.env` (racine) | `FCM_PROJECT_ID` | ID projet pour l'API FCM v1 | `history/views.py::_get_fcm_access_token` |
| `.env` (racine) | `FCM_CLIENT_EMAIL` | E-mail du Service Account | idem |
| `.env` (racine) | `FCM_PRIVATE_KEY` | Clé privée pour signer le JWT OAuth2 | idem |
| `frontend/android/app/google-services.json` | — (fichier entier) | Active le plugin natif Capacitor FCM | `@capacitor-firebase/messaging` |

### 4.7 Vérifier que le backend a bien chargé la config FCM

```bash
docker compose up django_api
docker compose logs django_api | grep -i fcm
```

Tester l'envoi d'une notification (au moins un token doit avoir été enregistré au préalable depuis l'app, via `POST /api/fcm-token/`) :

```bash
curl -X POST http://localhost:8000/api/send-fcm/ \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "body": "Notification de test", "data": {}}'
```

Réponse attendue si tout est bien configuré :
```json
{ "sent": 1, "errors": [] }
```

Si la configuration FCM est incomplète, l'API renvoie une erreur explicite mentionnant la ou les variables manquantes (`FCM_PROJECT_ID`, `FCM_CLIENT_EMAIL`, `FCM_PRIVATE_KEY`).

### 4.8 Comportement de l'app selon la plateforme

Le hook `useFirebaseMessaging.ts` choisit automatiquement le bon chemin :

```
Capacitor.isNativePlatform() === true   (APK installé sur Android)
        │
        ▼
registerNative()
  → @capacitor-firebase/messaging
  → nécessite google-services.json (§4.2)
  → fonctionne dès l'installation de l'APK, sans VAPID key

Capacitor.isNativePlatform() === false  (npm run dev, navigateur)
        │
        ▼
registerWeb()
  → SDK Firebase Web (firebase/messaging)
  → nécessite VITE_FIREBASE_VAPID_KEY (§4.4)
  → nécessite un fichier public/firebase-messaging-sw.js (non fourni
    par défaut dans ce repo — à créer séparément si le test FCM
    depuis un navigateur classique est nécessaire ; sans ce fichier,
    registerWeb() échoue silencieusement avec un avertissement console,
    sans bloquer le reste de l'application)
```

> En résumé : pour tester les notifications push, **le chemin fiable est l'APK Android natif** (§4.2 avec `google-services.json`). Le chemin navigateur est fourni en best-effort dans le code mais demande une pièce supplémentaire (`firebase-messaging-sw.js`) non présente dans ce repo.

---

## 5. Réseau Android — appels HTTP vers le backend

Le projet est **déjà configuré** pour autoriser le trafic HTTP en clair (le backend Django tourne en `http://`, pas `https://`) :

- `capacitor.config.ts` définit `server.androidScheme: 'http'` et `android.allowMixedContent: true` (§3.1)
- `frontend/android/app/src/main/AndroidManifest.xml` définit `android:usesCleartextTraffic="true"` sur la balise `<application>`

**Aucune action manuelle n'est requise** sur ce point (pas besoin de créer un fichier `network_security_config.xml` séparé) : ces deux réglages suffisent à autoriser les appels `fetch()`/`axios` vers `http://192.168.100.14:8000` depuis la WebView.

Seule la variable `VITE_API_URL` dans `frontend/.env` doit pointer vers la bonne IP (§3.2).

---

## 6. Build et génération APK

### 6.1 Installer les dépendances

```bash
cd frontend
npm install
```

### 6.2 Vérifier la présence des fichiers de configuration

Avant de builder, s'assurer que ces deux fichiers existent (non versionnés, créés manuellement) :

- [ ] `frontend/.env` (§3.2)
- [ ] `frontend/android/app/google-services.json` (§4.2)

### ──────────────────────────────────────────────
### Étape 4 — Rebuild APK (procédure standard)
### ──────────────────────────────────────────────

À chaque modification du code frontend, ou pour générer l'APK pour la première fois :

```bash
cd frontend
npm run build
cap sync android
cap open android
```

Détail de chaque commande :

| Commande | Effet |
|---|---|
| `npm run build` | Compile TypeScript (`tsc`) puis génère le build de production Vite dans `frontend/dist/` |
| `cap sync android` | Copie `dist/` dans `android/app/src/main/assets/public/`, met à jour les plugins natifs (`google-services.json`, dépendances Gradle) |
| `cap open android` | Ouvre le projet `frontend/android/` dans Android Studio |

> ⚠️ `cap sync android` doit être relancé **à chaque fois** que `dist/` change (donc après chaque `npm run build`), sinon l'APK contiendra une version périmée du frontend.

Puis, **dans Android Studio** :

1. Attendre la fin du **Gradle sync** (barre de progression en bas de la fenêtre)
2. Menu **Build → Build Bundle(s) / APK(s) → Build APK(s)**
3. Attendre la fin du build (notification en bas à droite : *"APK(s) generated successfully"*)
4. Cliquer sur **locate** dans la notification, ou récupérer l'APK directement dans :
   ```
   frontend/android/app/build/outputs/apk/debug/app-debug.apk
   ```

Cet APK debug peut être transféré sur un téléphone Android (câble USB, lien de partage, etc.) et installé directement (activer "Sources inconnues" si nécessaire dans les paramètres Android).

### 6.3 Initialiser Capacitor (uniquement si `frontend/android/` est absent)

Cette étape n'est **pas nécessaire** dans l'état actuel du repo (le dossier `android/` existe déjà). À ne faire que si ce dossier est supprimé ou pour un nouveau projet :

```bash
npm install -g @capacitor/cli
cap init anavidApp com.anavid.shopanalytics --web-dir dist
cap add android
```

---

## 7. Lancement direct sur téléphone (sans APK)

Utile pour itérer rapidement sans regénérer d'APK à chaque fois.

### 7.1 Activer le débogage USB sur le téléphone

1. **Paramètres → À propos du téléphone**
2. Appuyer **7 fois** sur **"Numéro de build"** (active les options développeur)
3. **Paramètres → Options développeur → Activer le débogage USB**
4. Brancher le câble USB → Accepter la popup d'autorisation sur le téléphone

### 7.2 Vérifier la détection ADB

```bash
adb devices
```

Résultat attendu :
```
List of devices attached
XXXXXXXX    device
```

### 7.3 Lancer depuis Android Studio

En haut de la fenêtre Android Studio :

```
[app ▼]  [Nom du téléphone ▼]  ▶ Run
```

Sélectionner le téléphone dans la liste déroulante → cliquer sur **▶ (triangle vert)**.

---

## 8. Démarrer le backend

```bash
# Depuis la racine du projet
docker compose up django_api ollama postgres
```

Vérifier l'accès depuis le navigateur du PC (et idéalement depuis le navigateur du téléphone, sur le même Wi-Fi) :
```
http://192.168.100.14:8000/api/docs/
```
→ Doit afficher l'interface Swagger.

### Ouvrir le port 8000 dans le firewall Windows (si nécessaire)

```cmd
:: CMD en mode Administrateur
netsh advfirewall firewall add rule name="Django 8000" dir=in action=allow protocol=TCP localport=8000
```

---

## 9. Workflow de mise à jour rapide

À chaque modification du code frontend, pour mettre à jour l'APK ou l'app lancée en debug :

```bash
cd frontend
npm run build
cap sync android
# Puis dans Android Studio : Build → Build APK(s)  ou  ▶ Run
```

Si seul le `.env` a changé (nouvelle IP backend, nouvelles clés Firebase), il faut **aussi** refaire `npm run build` : Vite injecte les variables `VITE_*` au moment du build, pas à l'exécution.

---

## 10. APK Release (production)

Dans Android Studio :

```
Build → Generate Signed Bundle / APK → APK
```

1. Créer un **keystore JKS** (première fois) — **à conserver précieusement**, il sera nécessaire pour toutes les mises à jour futures de l'app sur le même appareil/store
2. Renseigner le mot de passe du keystore + alias
3. Sélectionner le build type `release`
4. APK généré dans :
   ```
   frontend/android/app/build/outputs/apk/release/app-release.apk
   ```

> Pour la production, le bloc `server` dans `capacitor.config.ts` reste tel quel (`androidScheme: 'http'`) puisque le front est bundlé dans l'APK (pas de `server.url` pointant vers un poste de dev). Vérifier en revanche que `VITE_API_URL` dans `frontend/.env` pointe vers l'URL **définitive** du backend de production avant de lancer `npm run build`.

---

## 11. Plugins Capacitor installés

| Plugin | Version | Fonction |
|--------|---------|----------|
| `@capacitor/android` | ^6.2.1 | Plateforme Android |
| `@capacitor/app` | ^6.0.3 | Gestion du cycle de vie de l'app |
| `@capacitor/haptics` | ^6.0.3 | Retour haptique |
| `@capacitor/keyboard` | ^6.0.4 | Gestion du clavier virtuel |
| `@capacitor/status-bar` | ^6.0.3 | Barre de statut |
| `@capacitor-firebase/messaging` | ^6.3.1 | Notifications push FCM (chemin natif) |
| `firebase` (SDK JS) | ^11.10.0 | Notifications push FCM (chemin navigateur, best-effort) |

---

## 12. Résolution des problèmes courants

| Erreur | Cause | Solution |
|--------|-------|----------|
| `tsc not recognized` | `node_modules` absent | `npm install` |
| `npx cap: could not determine executable` | CLI Capacitor non installée | `npm install` (CLI déjà en dépendance locale) ou `npm install -g @capacitor/cli` |
| Notifications absentes sur l'APK installé | `google-services.json` manquant ou non synchronisé | Vérifier sa présence dans `frontend/android/app/`, puis refaire `cap sync android` |
| `FCM_PRIVATE_KEY invalide ou mal formatée` (backend) | Clé privée mal échappée dans `.env` | Vérifier le format `\n` littéral, voir §4.5 |
| `Aucun token FCM enregistré` lors de `/api/send-fcm/` | Aucun appareil n'a encore appelé `/api/fcm-token/` | Installer l'APK, ouvrir l'app, accepter la permission de notification |
| Notifications reçues sur navigateur web mais pas sur APK (ou inversement) | Chemin natif / web mal configuré | Voir §4.8 — chaque chemin a ses propres prérequis |
| `Cannot find module 'axios'` | Dépendance manquante | `npm install axios` |
| Page blanche dans l'app après installation | Build `dist/` absent ou périmé | `npm run build` puis `cap sync android` puis rebuild l'APK |
| Connexion refusée depuis le mobile vers l'API | Mauvaise IP dans `VITE_API_URL`, ou firewall, ou réseaux Wi-Fi différents | Vérifier l'IP (§3.3), ouvrir le port 8000 (§8), même réseau Wi-Fi |
| Téléphone non détecté par `adb devices` | Débogage USB désactivé | Activer dans Options développeur (§7.1) |
| Gradle sync échoue | JDK manquant ou mauvaise version | Installer JDK 17 |
| `VITE_API_URL` ou clés Firebase ignorées après modification du `.env` | Vite injecte les variables au build, pas à l'exécution | Refaire `npm run build` puis `cap sync android` |

---

## 13. Informations de build

| Paramètre | Valeur |
|-----------|--------|
| App Name | anavidApp |
| App ID | `com.anavid.shopanalytics` |
| Web Dir | `dist/` |
| Backend URL (dev, exemple) | `http://192.168.100.14:8000/api` |
| Capacitor version | 6.x |
| Android min SDK | 24 |
| Android compile/target SDK | 36 |
| Projet Firebase (exemple) | `shop-analytics-anavid` |

---

*Document généré pour le projet Anavid Store 360 — Kiabi*