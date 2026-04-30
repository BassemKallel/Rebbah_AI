from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0024_conversation_lead_nullable'),
    ]

    operations = [
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
    ]
