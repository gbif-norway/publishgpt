# Generated by Django 5.0.2 on 2024-07-23 13:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_alter_message_content'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='structure_notes',
            field=models.CharField(blank=True, default='', max_length=2000),
        ),
    ]