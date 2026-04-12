from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0020_remove_company_tiktak_api_token'),
    ]

    operations = [
        migrations.AlterField(
            model_name='nlufallbacklog',
            name='message',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='fallback_log',
                to='crm.message',
                help_text='Message utilisateur qui a declenche le fallback (NULL si message supprime)',
            ),
        ),
    ]
