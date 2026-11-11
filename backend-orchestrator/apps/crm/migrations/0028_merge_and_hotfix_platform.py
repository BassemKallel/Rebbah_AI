"""
Merge migration: resolves conflicting leaf nodes from two branches merged into dev.

Leaf nodes:
  - 0026_lead_status_remove_prospect (from dev branch)
  - 0027_lead_status_remove_prospect (from feat/auth-llm-switcher branch)

Both remove the PROSPECT status from Lead — the one that runs second is a no-op
since the field choices are identical after the first runs.

Also includes the hotfix: ADD COLUMN IF NOT EXISTS for platform, in case
the column was never created on some DB instances.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0026_lead_status_remove_prospect'),
        ('crm', '0027_lead_status_remove_prospect'),
    ]

    operations = [
        # Safety net: ensure platform column exists regardless of which
        # branch's 0026/0025 migrations ran on this DB instance.
        migrations.RunSQL(
            sql="""
                ALTER TABLE crm_conversation
                ADD COLUMN IF NOT EXISTS platform VARCHAR(20)
                NOT NULL DEFAULT 'messenger';
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS crm_conversation_platform_idx
                ON crm_conversation (platform);
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
