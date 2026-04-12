"""
One-time script: add missing columns with IF NOT EXISTS, then fake-apply
migrations 0022-0024 so Django considers them done.
Safe to re-run. Remove this file after the server is fixed.
"""
import django, os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.db import connection

ADD_COLUMN_SQL = [
    # 0022: BotConfiguration
    "ALTER TABLE crm_botconfiguration ADD COLUMN IF NOT EXISTS bot_enabled boolean DEFAULT true NOT NULL",
    "ALTER TABLE crm_botconfiguration ADD COLUMN IF NOT EXISTS bot_disabled_at timestamp with time zone",
    # 0022: Conversation
    "ALTER TABLE crm_conversation ADD COLUMN IF NOT EXISTS is_human_controlled boolean DEFAULT false NOT NULL",
    "ALTER TABLE crm_conversation ADD COLUMN IF NOT EXISTS human_takeover_at timestamp with time zone",
    "ALTER TABLE crm_conversation ADD COLUMN IF NOT EXISTS human_agent_id integer REFERENCES auth_user(id) ON DELETE SET NULL",
    # 0022: Message
    "ALTER TABLE crm_message ADD COLUMN IF NOT EXISTS is_human_agent boolean DEFAULT false NOT NULL",
]

FAKE_MIGRATIONS = [
    "0022_add_human_handoff_fields",
    "0023_refactor_helptext",
    "0024_add_company_llm_fields",
]

with connection.cursor() as cursor:
    # Step 1: Add missing columns (idempotent)
    for sql in ADD_COLUMN_SQL:
        cursor.execute(sql)
        print(f"  OK: {sql.split('ADD COLUMN IF NOT EXISTS ')[1].split()[0]}")

    # Step 2: Purge stale migration records
    placeholders = ",".join(["%s"] * len(FAKE_MIGRATIONS))
    cursor.execute(
        f"DELETE FROM django_migrations WHERE app='crm' AND name IN ({placeholders})",
        FAKE_MIGRATIONS,
    )
    print(f"Purged {cursor.rowcount} stale migration record(s)")

    # Step 3: Mark them as applied (fake)
    for name in FAKE_MIGRATIONS:
        cursor.execute(
            "INSERT INTO django_migrations (app, name, applied) VALUES ('crm', %s, NOW())",
            [name],
        )
    print(f"Fake-applied {len(FAKE_MIGRATIONS)} migrations")

print("Done — columns exist and migrations are marked as applied.")
