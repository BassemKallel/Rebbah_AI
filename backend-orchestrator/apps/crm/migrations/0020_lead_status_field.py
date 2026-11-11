from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0019_company_dashboard_token_alter_company_gemini_api_key_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='lead_status',
            field=models.CharField(
                choices=[
                    ('PROSPECT', "Prospect — conversation démarrée, pas d'intention d'achat"),
                    ('ENGAGED', 'Engagé — produit identifié, entités en cours de collecte'),
                    ('QUALIFIED', 'Qualifié — pré-commande créée, en attente agent'),
                ],
                db_index=True,
                default='PROSPECT',
                max_length=20,
            ),
        ),
    ]
