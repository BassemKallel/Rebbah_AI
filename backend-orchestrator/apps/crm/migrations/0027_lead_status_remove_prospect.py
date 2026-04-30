from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0026_conversation_platform'),
    ]

    operations = [
        # Migrate any existing PROSPECT leads to ENGAGED before changing the field
        migrations.RunSQL(
            sql="UPDATE crm_lead SET lead_status = 'ENGAGED' WHERE lead_status = 'PROSPECT';",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AlterField(
            model_name='lead',
            name='lead_status',
            field=models.CharField(
                choices=[
                    ('ENGAGED', "Engagé — intention d'achat détectée, entités en cours de collecte"),
                    ('QUALIFIED', 'Qualifié — pré-commande créée, en attente agent'),
                ],
                db_index=True,
                default='ENGAGED',
                max_length=20,
            ),
        ),
    ]
