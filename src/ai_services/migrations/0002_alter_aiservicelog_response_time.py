# Generated by Django 5.2.1 on 2025-06-06 07:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai_services', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aiservicelog',
            name='response_time',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
