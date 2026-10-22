from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('api', '0038_taxon_name_decisions')]
    operations = [
        migrations.AddField(
            model_name='taxonnamematch', name='review_meta',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
