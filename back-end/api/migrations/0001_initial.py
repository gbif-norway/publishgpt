# Generated by Django 4.2.2 on 2024-01-31 19:09

import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
import picklefield.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Agent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'ordering': ['created_at'],
                'get_latest_by': 'created_at',
            },
        ),
        migrations.CreateModel(
            name='Dataset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('orcid', models.CharField(blank=True, max_length=50)),
                ('file', models.FileField(upload_to='user_files')),
                ('dwc_core', models.CharField(blank=True, choices=[('event_occurrences', 'Event'), ('occurrence', 'Occurrence'), ('taxonomy', 'Taxonomy')], max_length=30)),
                ('dwc_extensions', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(choices=[('simple_multimedia', 'Simple Multimedia'), ('measurement_or_fact', 'Measurement Or Fact'), ('gbif_releve', 'Gbif Releve')], max_length=500), blank=True, null=True, size=None)),
            ],
            options={
                'ordering': ['created_at'],
                'get_latest_by': 'created_at',
            },
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=300, unique=True)),
                ('text', models.CharField(max_length=5000)),
                ('per_table', models.BooleanField()),
            ],
            options={
                'ordering': ['id'],
                'get_latest_by': 'id',
            },
        ),
        migrations.CreateModel(
            name='Table',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('title', models.CharField(blank=True, max_length=200)),
                ('df', picklefield.fields.PickledObjectField(editable=False)),
                ('description', models.CharField(blank=True, max_length=2000)),
                ('dataset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.dataset')),
            ],
        ),
        migrations.CreateModel(
            name='Metadata',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('title', models.CharField(blank=True, max_length=500)),
                ('description', models.CharField(blank=True, max_length=2000)),
                ('dataset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.dataset')),
            ],
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('content', models.CharField(blank=True, max_length=10000)),
                ('faked', models.BooleanField(default=False)),
                ('role', models.CharField(choices=[('user', 'User'), ('system', 'System'), ('assistant', 'Assistant'), ('function', 'Function')], max_length=10)),
                ('function_name', models.CharField(blank=True, max_length=200)),
                ('function_id', models.CharField(blank=True, max_length=200)),
                ('agent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.agent')),
            ],
            options={
                'ordering': ['created_at'],
                'get_latest_by': 'created_at',
            },
        ),
        migrations.AddField(
            model_name='agent',
            name='dataset',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.dataset'),
        ),
        migrations.AddField(
            model_name='agent',
            name='task',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.task'),
        ),
    ]
