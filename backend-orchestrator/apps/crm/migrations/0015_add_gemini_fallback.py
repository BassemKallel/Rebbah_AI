from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0014_seed_response_templates'),
    ]

    operations = [
        # Add is_fallback to Message
        migrations.AddField(
            model_name='message',
            name='is_fallback',
            field=models.BooleanField(default=False, help_text='True si Gemini fallback a ete utilise'),
        ),
        # Create NLUFallbackLog
        migrations.CreateModel(
            name='NLUFallbackLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('original_text', models.TextField(help_text="Message brut de l'utilisateur")),
                ('tunbert_intent', models.CharField(blank=True, max_length=50, null=True)),
                ('tunbert_confidence', models.FloatField(blank=True, null=True)),
                ('tunbert_entities', models.JSONField(blank=True, default=list, help_text='raw_entities retournees par GLiNER')),
                ('gemini_intent', models.CharField(max_length=50)),
                ('gemini_confidence', models.FloatField(blank=True, null=True)),
                ('gemini_entities', models.JSONField(blank=True, default=list, help_text='Entites extraites par Gemini')),
                ('trigger_reason', models.CharField(choices=[('LOW_CONFIDENCE', 'TunBERT confiance basse'), ('SERVICE_DOWN', 'NLU service indisponible'), ('ALWAYS_VERIFY', 'Intent destructif verifie')], max_length=20)),
                ('intent_changed', models.BooleanField(default=False, help_text="True si Gemini a corrige l'intent de TunBERT")),
                ('reviewed', models.BooleanField(default=False, help_text='Reviewed par un humain')),
                ('review_label', models.CharField(blank=True, help_text="Label final valide par l'humain", max_length=50, null=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('message', models.OneToOneField(help_text='Message utilisateur qui a declenche le fallback', on_delete=django.db.models.deletion.CASCADE, related_name='fallback_log', to='crm.message')),
            ],
            options={
                'verbose_name': 'NLU Fallback Log',
                'verbose_name_plural': 'NLU Fallback Logs',
                'ordering': ['-created_at'],
            },
        ),
    ]
