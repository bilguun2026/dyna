# Generated by Django 5.1.5 on 2025-01-31 06:00

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rest', '0006_alter_cell_value'),
    ]

    operations = [
        migrations.AddField(
            model_name='tableapi',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='rest.tableapi'),
        ),
    ]
