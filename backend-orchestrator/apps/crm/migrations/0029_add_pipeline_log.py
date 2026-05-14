"""
Migration 0029: Add PipelineLog table for AI pipeline monitoring.

Logs every pipeline execution (NLU and LLM mode) with:
- Message content (user_text, bot_text)
- State transitions (state_before, state_after)
- Error tracking (has_error, error_type, error_detail)
- Performance (duration_ms)
"""
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0028_merge_and_hotfix_platform'),
    ]

    operations = [
        migrations.CreateModel(
            name='PipelineLog',
            fields=[
                ('id',              models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('shop_id',         models.CharField(db_index=True, max_length=100)),
                ('sender_id',       models.CharField(max_length=255)),
                ('mode',            models.CharField(choices=[('nlu', 'NLU (TunBERT)'), ('llm', 'LLM (Gemini Direct)')], default='nlu', max_length=10)),
                ('user_text',       models.TextField()),
                ('bot_text',        models.TextField(blank=True, default='')),
                ('detected_intent', models.CharField(blank=True, default='', max_length=50)),
                ('has_image',       models.BooleanField(default=False)),
                ('state_before',    models.CharField(blank=True, default='', max_length=50)),
                ('state_after',     models.CharField(blank=True, default='', max_length=50)),
                ('order_created',   models.BooleanField(default=False)),
                ('has_error',       models.BooleanField(db_index=True, default=False)),
                ('error_type',      models.CharField(
                    choices=[
                        ('none',         'Aucune erreur'),
                        ('json_parse',   'JSON Parse Error (Gemini)'),
                        ('api_error',    'Gemini API Error'),
                        ('no_api_key',   'Clé API manquante'),
                        ('import_error', 'Package manquant'),
                        ('vision_error', 'Vision Service Error'),
                        ('order_error',  'Erreur création commande'),
                        ('timeout',      'Timeout'),
                        ('other',        'Autre'),
                    ],
                    default='none',
                    max_length=20,
                )),
                ('error_detail',    models.TextField(blank=True, default='')),
                ('duration_ms',     models.IntegerField(blank=True, null=True)),
                ('created_at',      models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
            ],
            options={
                'verbose_name':        'Pipeline Log',
                'verbose_name_plural': 'Pipeline Logs',
                'ordering':            ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='pipelinelog',
            index=models.Index(fields=['shop_id', '-created_at'], name='crm_pipelinelog_shop_created_idx'),
        ),
        migrations.AddIndex(
            model_name='pipelinelog',
            index=models.Index(fields=['has_error', '-created_at'], name='crm_pipelinelog_error_created_idx'),
        ),
    ]
