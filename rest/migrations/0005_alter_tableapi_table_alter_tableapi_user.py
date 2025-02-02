# Generated by Django 5.1.5 on 2025-01-30 17:21

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rest', '0004_alter_tableapi_table'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tableapi',
            name='table',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='table_apis', to='rest.table'),
        ),
        migrations.AlterField(
            model_name='tableapi',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='table_apis', to=settings.AUTH_USER_MODEL),
        ),
    ]
