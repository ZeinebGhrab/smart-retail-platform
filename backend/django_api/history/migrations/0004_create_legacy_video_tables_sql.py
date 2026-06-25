# ============================================================
# 0004_load_legacy_video_tables_from_dump.py
#
# La migration 0003_notificationsspace_notificationsvideo (auto-générée)
# ne fait QUE déclarer l'état Django de NotificationsSpace et
# NotificationsVideo. Comme ces modèles ont Meta.managed = False, le
# CreateModel correspondant n'exécute AUCUN SQL en base -> les tables
# n'ont jamais existé dans MySQL, d'où :
# ProgrammingError: (1146, "Table 'shop-anavid-int.notifications_video' doesn't exist")
#
# Cette migration charge le SCHÉMA RÉEL ET LES DONNÉES depuis les vrais
# dumps phpMyAdmin de production (notifications_space.sql,
# notifications_video.sql, notifications_telegramaction.sql, copiés dans
# ce dossier de migrations) plutôt que de reconstruire un schéma
# approximatif à la main.
#
# Idempotence : chaque table n'est (re)créée que si elle n'existe pas déjà,
# pour permettre de rejouer `migrate` sans erreur (les dumps contiennent
# des ALTER TABLE ADD PRIMARY KEY / AUTO_INCREMENT qui ne peuvent être
# exécutés qu'une seule fois).
# ============================================================

from pathlib import Path

from django.db import migrations

MIGRATIONS_DIR = Path(__file__).resolve().parent

SQL_FILES = [
    ("notifications_space", MIGRATIONS_DIR / "notifications_space.sql"),
    ("notifications_video", MIGRATIONS_DIR / "notifications_video.sql"),
    ("notifications_telegramaction", MIGRATIONS_DIR / "notifications_telegramaction.sql"),
]


def _table_exists(cursor, table_name):
    cursor.execute("SHOW TABLES LIKE %s", [table_name])
    if cursor.fetchone() is None:
        return False
    cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
    return cursor.fetchone()[0] > 0

def _strip_comment_lines(sql_text):
    """
    Retire les lignes de commentaires phpMyAdmin (commençant par --, en
    ignorant les espaces de tête) avant tout découpage en instructions.
    Les guillemets/backticks n'apparaissent jamais en début de ligne dans
    ces dumps, donc il est sûr de filtrer ligne par ligne ici.
    """
    kept_lines = [
        line for line in sql_text.splitlines()
        if not line.strip().startswith("--")
    ]
    return "\n".join(kept_lines)


def _split_statements(sql_text):
    """
    Découpe le dump SQL (déjà nettoyé de ses commentaires --) en
    instructions exécutables, en gérant les points-virgules à l'intérieur
    des chaînes (par ex. le JSON de la colonne metadata).
    """
    sql_text = _strip_comment_lines(sql_text)
    statements = []
    current = []
    in_string = False
    string_char = ""
    i = 0
    n = len(sql_text)
    while i < n:
        char = sql_text[i]
        current.append(char)
        if in_string:
            if char == "\\":
                # caractère échappé suivant : on le copie tel quel
                if i + 1 < n:
                    current.append(sql_text[i + 1])
                    i += 2
                    continue
            elif char == string_char:
                in_string = False
        else:
            if char in ("'", '"'):
                in_string = True
                string_char = char
            elif char == ";":
                statement = "".join(current).strip()
                if statement:
                    statements.append(statement)
                current = []
        i += 1
    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return statements


def load_legacy_tables(apps, schema_editor):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        for table_name, sql_path in SQL_FILES:
            if _table_exists(cursor, table_name):
                continue  # déjà chargée (migration rejouée) : on ne touche pas aux données existantes

            sql_text = sql_path.read_text(encoding="utf-8")
            for statement in _split_statements(sql_text):
                # on ignore les directives de réglage de session phpMyAdmin
                stripped = statement.strip()
                if stripped.startswith("--") or stripped.startswith("/*"):
                    continue
                if stripped.upper().startswith(("SET ", "START TRANSACTION", "COMMIT")):
                    continue
                cursor.execute(statement)


def noop_reverse(apps, schema_editor):
    # on ne supprime pas des données de production lors d'un rollback accidentel
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('history', '0003_notificationsspace_notificationsvideo'),
    ]

    operations = [
        migrations.RunPython(load_legacy_tables, noop_reverse),
    ]