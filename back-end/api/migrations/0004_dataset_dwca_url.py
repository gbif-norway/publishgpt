# Generated by Django 5.0.2 on 2024-08-07 20:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_dataset_structure_notes'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='dwca_url',
            field=models.CharField(blank=True, max_length=50),
        ),
    ]