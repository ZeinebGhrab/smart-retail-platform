# `history/migrations/` — Historique des migrations

Ce dossier contient toutes les migrations Django de l'app `history`.  
Les migrations gèrent deux types de modèles distincts :

- **Modèles managés** (`managed = True`) : Django crée et fait évoluer les tables — `FCMToken`, `PredictionNotification`, `PushNotificationLog`.
- **Modèles non-managés** (`managed = False`) : les tables existent déjà en production (`notifications_space`, `notifications_video`) — Django déclare uniquement leur structure pour l'ORM, sans toucher au schéma réel.

---

## Chaîne des migrations

```
0001_initial
    └── 0002_alter_fcmtoken_token
            └── 0003_notificationsspace_notificationsvideo
                    └── 0004_create_legacy_video_tables_sql
                            └── 0005_alertspace_videotheftalert_predictionnotification_and_more
                                    └── 0006_fix_fcmtoken_max_length  ← état actuel
```

---

## Détail de chaque migration

### `0001_initial` — 2026-06-24
**Création initiale des deux premiers modèles.**

| Modèle créé | Table | Champs notables |
|---|---|---|
| `FCMToken` | `history_fcmtoken` | `token` (CharField 512), `created_at`, `updated_at` |
| `Notification` | `history_notification` | Ancêtre de `PredictionNotification` — remplacé en `0005` |

> `Notification` était une version simplifiée sans UUID, titre, tags ni score de confiance.

---

### `0002_alter_fcmtoken_token` — 2026-06-25
**Élargissement du champ `token` de `FCMToken`.**

`token` passe de `CharField(max_length=512)` à `TextField()` (taille illimitée),  
pour accommoder les tokens FCM longs de certains appareils Android.  
Corrigé ensuite en `0006` avec un plafond plus raisonnable.

---

### `0003_notificationsspace_notificationsvideo`
**Déclaration ORM des tables de production externes.**

Déclare `NotificationsSpace` et `NotificationsVideo` avec `managed = False`  
pour que l'ORM puisse les interroger sans en contrôler le schéma.

> Ces modèles intermédiaires (`NotificationsSpace`, `NotificationsVideo`) sont  
> **supprimés en `0005`** et remplacés par `AlertSpace` et `VideoTheftAlert`,  
> qui exposent un schéma plus complet et des choix de champs typés.

---

### `0004_create_legacy_video_tables_sql`
**Chargement des tables de production depuis les dumps SQL.**

Migration `RunPython` qui exécute les dumps phpMyAdmin de production :

| Fichier SQL | Table chargée |
|---|---|
| `notifications_space.sql` | `notifications_space` |
| `notifications_video.sql` | `notifications_video` |
| `notifications_telegramaction.sql` | `notifications_telegramaction` |

**Comportement :**
- Vérifie si la table existe et contient des données avant d'exécuter le dump.
- **Idempotente** : peut être rejouée sans erreur (`migrate` sur une base déjà à jour ne fait rien).
- Le rollback (`reverse`) est un `noop` — on ne supprime jamais des données de production.
- Gère les points-virgules à l'intérieur des chaînes JSON (colonne `metadata`).
- Ignore les directives phpMyAdmin (`SET`, `START TRANSACTION`, `COMMIT`, commentaires `--`).

> ⚠️ Les fichiers `.sql` (`notifications_space.sql`, `notifications_video.sql`,  
> `notifications_telegramaction.sql`) doivent être présents dans ce dossier  
> pour que cette migration s'exécute correctement.

---

### `0005_alertspace_videotheftalert_predictionnotification_and_more` — 2026-06-26
**Refonte complète des modèles — migration la plus importante.**

**Modèles créés :**

| Modèle | Table | `managed` | Description |
|---|---|---|---|
| `AlertSpace` | `notifications_space` | `False` | Remplace `NotificationsSpace` — schéma complet (telegram, language, token_web_connector…) |
| `VideoTheftAlert` | `notifications_video` | `False` | Remplace `NotificationsVideo` — statuts typés, qualification, approval_result, ForeignKey vers `AlertSpace` |
| `PredictionNotification` | `history_predictionnotification` | `True` | Remplace `Notification` — UUID, title, tags, confidence_score, metadata JSON, indexes composites |
| `PushNotificationLog` | `history_pushnotificationlog` | `True` | Journal des envois FCM avec statuts et compteurs d'erreurs |

**Modèles supprimés :**
- `Notification` (remplacé par `PredictionNotification`)
- `NotificationsSpace` (remplacé par `AlertSpace`)
- `NotificationsVideo` (remplacé par `VideoTheftAlert`)

**Évolutions de `FCMToken` :**
- Ajout de `device_info` (CharField 255)
- Ajout de `is_active` (BooleanField, défaut `True`)
- `token` passe de `TextField` à `CharField(max_length=500, unique=True)`

**Index créés sur `PredictionNotification` :**

| Index | Champs | Usage |
|---|---|---|
| `history_pre_date_3cb4fd_idx` | `date`, `-generated_at` | Filtrage par date de prédiction |
| `history_pre_is_read_bf9e6c_idx` | `is_read`, `-generated_at` | Compteur non lus et filtrage |
| `history_pre_type_b4baf5_idx` | `type` | Filtrage par type de notification |

---

### `0006_fix_fcmtoken_max_length` — 2026-06-26
**Correction du plafond du champ `token` de `FCMToken`.**

`token` revient à `CharField(max_length=255, unique=True)`.  
La séquence complète des changements sur ce champ :

| Migration | Valeur |
|---|---|
| `0001` | `CharField(max_length=512)` |
| `0002` | `TextField()` (illimité) |
| `0005` | `CharField(max_length=500, unique=True)` |
| `0006` | `CharField(max_length=255, unique=True)` ← **état final** |

---

## Commandes utiles

```bash
# Appliquer toutes les migrations
python manage.py migrate

# Vérifier l'état des migrations
python manage.py showmigrations history

# Rejouer depuis zéro (dev uniquement)
python manage.py migrate history zero
python manage.py migrate history

# Générer une nouvelle migration après modification d'un modèle
python manage.py makemigrations history
```

---

## Notes importantes

- Les modèles `AlertSpace` et `VideoTheftAlert` ont `managed = False` : **Django ne crée ni ne modifie jamais leurs tables**. Toute évolution du schéma `notifications_space` ou `notifications_video` doit être faite directement en base ou via un nouveau dump SQL dans une migration `RunPython`.
- La migration `0004` dépend de la présence physique des fichiers `.sql` dans ce dossier. En cas de clone du dépôt sans ces fichiers, la migration échouera avec une `FileNotFoundError`.