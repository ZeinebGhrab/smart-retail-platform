# ============================================================
# history/admin.py
# Point d'entrée admin pour l'app "history".
# AlertSpace n'apparaissent
# JAMAIS dans /admin/, malgré que leurs tables existent en base
# (migrées sous l'app "history").
#
# En importcentral ici les modules admin des sous-dossiers, leurs
# @admin.register(...) s'exécutent au chargement de history.admin,
# qui LUI est bien découvert automatiquement par Django (app listée
# dans INSTALLED_APPS).
# ============================================================

from .n8n_predictions import admin as _n8n_predictions_admin  # noqa: F401