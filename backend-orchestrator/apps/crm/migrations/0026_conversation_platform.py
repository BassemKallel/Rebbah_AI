from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Adds 'platform' field to Conversation.

    Uses RunSQL with IF NOT EXISTS to be idempotent:
    safe to apply even if the column already exists in the DB
    (e.g. when the column was created by a previous migration on another branch).
    """

    dependencies = [
        ('crm', '0025_conversation_lead_nullable'),
    ]

    operations = [
        # Step 1 — Add column safely (no-op if already exists)
        migrations.RunSQL(
            sql="""
                ALTER TABLE crm_conversation
                ADD COLUMN IF NOT EXISTS platform VARCHAR(20)
                NOT NULL DEFAULT 'messenger';
            """,
            reverse_sql="""
                ALTER TABLE crm_conversation
                DROP COLUMN IF EXISTS platform;
            """,
        ),
        # Step 2 — Add index safely (no-op if already exists)
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS crm_conversation_platform_idx
                ON crm_conversation (platform);
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS crm_conversation_platform_idx;
            """,
        ),
        # Step 3 — Tell Django ORM about the field (state only, no DB op)
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='conversation',
                    name='platform',
                    field=models.CharField(
                        choices=[
                            ('messenger', 'Messenger'),
                            ('instagram', 'Instagram'),
                            ('poc',       'POC / Test'),
                        ],
                        default='messenger',
                        db_index=True,
                        max_length=20,
                    ),
                ),
            ],
            database_operations=[],  # Already done above via RunSQL
        ),
    ]
