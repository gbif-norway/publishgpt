from django.db import migrations, models


def open_waiting_reviews(apps, schema_editor):
    """Reviews were open while the agent's last message was its review request; keep exactly those open."""
    Agent = apps.get_model('api', 'Agent')
    Message = apps.get_model('api', 'Message')
    paused = Message.objects.filter(openai_obj__has_key='taxon_review').values_list('agent_id', flat=True)
    for agent in Agent.objects.filter(id__in=paused, completed_at__isnull=True):
        last = Message.objects.filter(agent=agent).order_by('-created_at', '-id').first()
        scope = (last.openai_obj or {}).get('taxon_review') if last else None
        if isinstance(scope, dict):
            agent.open_taxon_review = {
                'source_table': scope.get('source_table') or '', 'context_column': scope.get('context_column') or '',
            }
            agent.save(update_fields=['open_taxon_review'])


class Migration(migrations.Migration):
    dependencies = [('api', '0039_taxon_review_meta')]
    operations = [
        migrations.AddField(
            model_name='agent', name='open_taxon_review',
            field=models.JSONField(
                blank=True, default=dict,
                help_text='Scope of the taxon review this agent asked for, until the user presses Done or Skip.',
            ),
        ),
        migrations.RunPython(open_waiting_reviews, migrations.RunPython.noop),
    ]
