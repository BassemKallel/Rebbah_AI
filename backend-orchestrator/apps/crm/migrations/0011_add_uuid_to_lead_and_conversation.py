import uuid
from django.db import migrations, models


def populate_lead_uuids(apps, schema_editor):
    """Generate a unique UUID for each existing Lead."""
    Lead = apps.get_model('crm', 'Lead')
    for lead in Lead.objects.all():
        lead.uuid = uuid.uuid4()
        lead.save(update_fields=['uuid'])


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0010_add_conversation_state_to_message'),
    ]

    operations = [
        # Step 1: Add uuid field (not unique yet, nullable to allow insertion)
        migrations.AddField(
            model_name='lead',
            name='uuid',
            field=models.UUIDField(null=True, blank=True, editable=False,
                                   help_text='Stable public identifier for this lead'),
        ),

        # Step 2: Populate unique UUIDs for all existing rows
        migrations.RunPython(populate_lead_uuids, migrations.RunPython.noop),

        # Step 3: Make it non-nullable and unique
        migrations.AlterField(
            model_name='lead',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False,
                                   help_text='Stable public identifier for this lead'),
        ),

        # ── Conversation: add sender_id and lead_uuid ──
        migrations.AddField(
            model_name='conversation',
            name='sender_id',
            field=models.CharField(blank=True, null=True, max_length=255,
                                   help_text='Denormalized platform_id of the sender'),
        ),
        migrations.AddField(
            model_name='conversation',
            name='lead_uuid',
            field=models.UUIDField(blank=True, null=True,
                                   help_text='Denormalized lead UUID for direct querying'),
        ),
    ]
