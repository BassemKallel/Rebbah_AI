import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Adds Human Handoff fields missing on feat/auth-llm-switcher.
    These were in 0022_add_human_handoff on feat/human-handoff but not here.
    """

    dependencies = [
        ('crm', '0021_nlufallbacklog_message_nullable'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── BotConfiguration — global bot toggle ──────────────────────────────
        migrations.AddField(
            model_name='botconfiguration',
            name='bot_enabled',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='botconfiguration',
            name='bot_disabled_at',
            field=models.DateTimeField(blank=True, null=True),
        ),

        # ── Conversation — per-conversation human takeover ────────────────────
        migrations.AddField(
            model_name='conversation',
            name='is_human_controlled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='conversation',
            name='human_takeover_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='conversation',
            name='human_agent',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='controlled_conversations',
                to=settings.AUTH_USER_MODEL,
            ),
        ),

        # ── Message — flag messages sent by a human agent ─────────────────────
        migrations.AddField(
            model_name='message',
            name='is_human_agent',
            field=models.BooleanField(default=False),
        ),
    ]
