from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0039_billingwallet_average_cost_per_message_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='botconfiguration',
            name='ai_agent_name',
            field=models.CharField(default='Rebbah AI', max_length=255),
        ),
    ]
