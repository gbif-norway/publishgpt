# Generated by Django 5.0.2 on 2024-08-20 19:59

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0006_remove_task_additional_function_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='additional_functions',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=300, null=True), blank=True, null=True, size=None),
        ),
    ]
