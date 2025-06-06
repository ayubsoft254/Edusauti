# Generated by Django 5.2.1 on 2025-06-02 10:38

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ServiceConfiguration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_name', models.CharField(max_length=50, unique=True)),
                ('endpoint_url', models.URLField()),
                ('api_version', models.CharField(default='2024-02-01', max_length=20)),
                ('requests_per_minute', models.PositiveIntegerField(default=60)),
                ('requests_per_day', models.PositiveIntegerField(default=1000)),
                ('default_settings', models.JSONField(default=dict)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Service Configuration',
                'verbose_name_plural': 'Service Configurations',
            },
        ),
        migrations.CreateModel(
            name='AIServiceLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_id', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('service_type', models.CharField(choices=[('document_intelligence', 'Document Intelligence'), ('openai_chat', 'OpenAI Chat Completion'), ('openai_embedding', 'OpenAI Embeddings'), ('speech_synthesis', 'Speech Synthesis'), ('speech_recognition', 'Speech Recognition')], max_length=30)),
                ('endpoint', models.CharField(max_length=200)),
                ('method', models.CharField(default='POST', max_length=10)),
                ('request_size', models.PositiveIntegerField(help_text='Request size in bytes')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('success', 'Success'), ('failed', 'Failed'), ('timeout', 'Timeout')], default='pending', max_length=20)),
                ('response_size', models.PositiveIntegerField(blank=True, help_text='Response size in bytes', null=True)),
                ('response_time', models.PositiveIntegerField(help_text='Response time in milliseconds')),
                ('azure_request_id', models.CharField(blank=True, max_length=100)),
                ('azure_operation_id', models.CharField(blank=True, max_length=100)),
                ('tokens_used', models.PositiveIntegerField(blank=True, null=True)),
                ('characters_processed', models.PositiveIntegerField(blank=True, null=True)),
                ('estimated_cost', models.DecimalField(blank=True, decimal_places=6, max_digits=10, null=True)),
                ('error_code', models.CharField(blank=True, max_length=50)),
                ('error_message', models.TextField(blank=True)),
                ('additional_data', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'AI Service Log',
                'verbose_name_plural': 'AI Service Logs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AIServiceAnalytics',
            fields=[
            ],
            options={
                'verbose_name': 'AI Service Analytics',
                'verbose_name_plural': 'AI Service Analytics',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('ai_services.aiservicelog',),
        ),
        migrations.CreateModel(
            name='AIServiceUsage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=django.utils.timezone.now)),
                ('service_type', models.CharField(choices=[('document_intelligence', 'Document Intelligence'), ('openai_chat', 'OpenAI Chat Completion'), ('openai_embedding', 'OpenAI Embeddings'), ('speech_synthesis', 'Speech Synthesis'), ('speech_recognition', 'Speech Recognition')], max_length=30)),
                ('total_requests', models.PositiveIntegerField(default=0)),
                ('successful_requests', models.PositiveIntegerField(default=0)),
                ('failed_requests', models.PositiveIntegerField(default=0)),
                ('total_tokens', models.PositiveIntegerField(default=0)),
                ('total_characters', models.PositiveIntegerField(default=0)),
                ('total_response_time', models.PositiveIntegerField(default=0)),
                ('total_cost', models.DecimalField(decimal_places=6, default=0, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'AI Service Usage',
                'verbose_name_plural': 'AI Service Usage',
                'ordering': ['-date'],
                'unique_together': {('user', 'date', 'service_type')},
            },
        ),
    ]
