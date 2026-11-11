from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0023_refactor_helptext'),
    ]

    operations = [
        migrations.AlterField(
            model_name='conversation',
            name='lead',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='conversations',
                to='crm.lead',
            ),
        ),
    ]
