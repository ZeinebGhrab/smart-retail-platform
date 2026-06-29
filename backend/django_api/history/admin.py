# ============================================================
# history/admin.py
# Point d'entrée admin pour l'app "history".
#
# n8n_predictions et video_alerts sont des sous-apps
# Django (AppConfig.name = "history.n8n_predictions" / "history.
# video_alerts") mais ELLES NE SONT PAS LISTÉES DANS INSTALLED_APPS
# (seule "history" y figure). Django ne charge automatiquement que
# le fichier admin.py de chaque app listée dans INSTALLED_APPS — il
# ne va donc jamais lire n8n_predictions/admin.py ni
# video_alerts/admin.py tout seul, même si ces fichiers existent et
# contiennent des décorateurs @admin.register(...).
#
# Résultat avant ce correctif : FCMToken, PushNotificationLog,
# PredictionNotification, VideoTheftAlert, AlertSpace n'apparaissent
# JAMAIS dans /admin/, malgré que leurs tables existent en base
# (migrées sous l'app "history").
#
# En importcentral ici les modules admin des sous-dossiers, leurs
# @admin.register(...) s'exécutent au chargement de history.admin,
# qui LUI est bien découvert automatiquement par Django (app listée
# dans INSTALLED_APPS).
# ============================================================

from .n8n_predictions import admin as _n8n_predictions_admin  # noqa: F401
from .video_alerts import admin as _video_alerts_admin  # noqa: F401