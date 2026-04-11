from django.db import migrations, models


def migrate_historical_lead_status(apps, schema_editor):
    """
    Rétro-remplit lead_status pour les leads existants :
      - has_pending_order=True  → QUALIFIED
      - product_id non nul      → ENGAGED
      - sinon                   → PROSPECT (déjà la valeur par défaut)
    """
    Lead = apps.get_model('crm', 'Lead')
    Lead.objects.filter(has_pending_order=True).update(lead_status='QUALIFIED')
    Lead.objects.filter(has_pending_order=False, product_id__isnull=False).exclude(product_id='').update(lead_status='ENGAGED')


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0019_remove_tiktak_api_token_state'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='lead_status',
            field=models.CharField(
                choices=[
                    ('PROSPECT',  "Prospect — conversation démarrée, pas d'intention d'achat"),
                    ('ENGAGED',   "Engagé — produit identifié, entités en cours de collecte"),
                    ('QUALIFIED', "Qualifié — pré-commande créée, en attente agent"),
                ],
                default='PROSPECT',
                db_index=True,
                max_length=20,
                help_text="Funnel : PROSPECT → ENGAGED (produit détecté) → QUALIFIED (pré-commande créée)",
            ),
        ),
        migrations.RunPython(
            migrate_historical_lead_status,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
