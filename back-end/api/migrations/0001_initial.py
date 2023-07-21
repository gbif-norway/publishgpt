# Generated by Django 4.2.2 on 2023-07-21 06:00

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
                ('created', models.DateTimeField(auto_now_add=True)),
                ('completed', models.DateTimeField(blank=True, null=True)),
                ('_functions', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=500), size=None)),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'created',
            },
        ),
        migrations.CreateModel(
            name='Dataset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('orcid', models.CharField(blank=True, max_length=50)),
                ('file', models.FileField(upload_to='user_files')),
                ('dwc_core', models.CharField(blank=True, choices=[('event_occurrences', 'Event'), ('occurrence', 'Occurrence'), ('taxonomy', 'Taxonomy')], max_length=30)),
                ('dwc_extensions', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(choices=[('simple_multimedia', 'Simple Multimedia'), ('measurement_or_fact', 'Measurement Or Fact'), ('gbif_releve', 'Gbif Releve')], max_length=500), blank=True, null=True, size=None)),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'created',
            },
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=300, unique=True)),
                ('system_message_template', models.CharField(max_length=5000)),
                ('per_datasetframe', models.BooleanField()),
            ],
        ),
        migrations.CreateModel(
            name='Metadata',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('title', models.CharField(blank=True, max_length=500)),
                ('description', models.CharField(blank=True, max_length=2000)),
                ('dataset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.dataset')),
            ],
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('content', models.CharField(blank=True, max_length=9000)),
                ('function_name', models.CharField(blank=True, max_length=200)),
                ('role', models.CharField(choices=[('user', 'User'), ('system', 'System'), ('assistant', 'Assistant'), ('function', 'Function')], max_length=10)),
                ('agent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.agent')),
            ],
            options={
                'ordering': ['created'],
                'get_latest_by': 'created',
            },
        ),
        migrations.CreateModel(
            name='DatasetFrame',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('title', models.CharField(blank=True, max_length=200)),
                ('df', picklefield.fields.PickledObjectField(editable=False)),
                ('description', models.CharField(blank=True, max_length=2000)),
                ('problems', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=500), blank=True, null=True, size=None)),
                ('deleted', models.DateTimeField(blank=True, null=True)),
                ('dataset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.dataset')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='api.datasetframe')),
            ],
        ),
        migrations.CreateModel(
            name='AgentDatasetFrame',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('agent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.agent')),
                ('dataset_frame', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.datasetframe')),
            ],
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
