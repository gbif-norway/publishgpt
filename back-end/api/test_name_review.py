"""Cross-workflow contracts: source evidence, decisions, previews and written values agree."""
import copy
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from api import conversion_names, name_review, taxon_matching, taxon_review
from api.models import Agent, CustomUser, Dataset, Table, Task, TaxonNameMatch


def usage(name='Larus', rank='genus', authorship=None, **extra):
    return {'id': 'col-1', 'scientificName': name, 'taxonRank': rank,
            'scientificNameAuthorship': authorship, 'classification': {'kingdom': 'Animalia', 'genus': 'Larus'}, **extra}


class WorkflowParityTests(TestCase):
    def setUp(self):
        self.dataset = Dataset.objects.create(title='Name review parity')

    def reviews(self, frame, matched=None, parsed=None):
        match = {'matchType': 'EXACT', 'status': 'exact', 'usage': matched or usage(), 'alternatives': []}
        with patch.object(taxon_matching, 'match_col', return_value=[match]), \
                patch.object(taxon_matching, 'parse_names', side_effect=lambda labels, **kw: [parsed or {'usable': False} for _ in labels]), \
                patch.object(taxon_matching, 'col_release', return_value={}), \
                patch.object(taxon_matching, 'review_aids', return_value={}):
            rows, finished = taxon_matching.record_matches(self.dataset, 'identification', frame, 'verbatimIdentification')
        self.assertTrue(finished)
        columns = [c for c in frame if c != 'verbatimIdentification']
        review = name_review.collect_records([('identification', columns, frame[columns].values.tolist())])
        for record in review['labels']:
            chat = next(row for row in rows if row.verbatim_label == record['label'])
            record.update(match=copy.deepcopy(chat.match), parsed=copy.deepcopy(chat.parsed))
        return rows, review

    def test_same_choices_and_written_values_for_every_decision(self):
        cases = [
            ('Larus', {'decision': 'col'}, None),
            ('Larus', {'decision': 'mine'}, None),
            ('Larus', {'decision': 'empty'}, None),
            ('Larus', {'decision': 'corrected', 'scientificName': 'Larus corrected'}, None),
            ('Larus Smith, 1900', {'decision': 'mine'}, {'usable': True, 'lossless': True, 'canonical': 'Larus', 'authorship': 'Smith, 1900', 'rank': 'genus'}),
            ('Larus sp.', {'decision': 'stem'}, None),
            ('Larus cf. argentatus', {'decision': 'col', 'confirm_coarser': True}, None),
        ]
        for label, spec, parsed in cases:
            with self.subTest(label=label, decision=spec['decision']):
                TaxonNameMatch.objects.filter(dataset=self.dataset).delete()
                frame = pd.DataFrame({'verbatimIdentification': [label], 'scientificName': [label],
                                      'scientificNameAuthorship': [pd.NA], 'taxonRank': [pd.NA]})
                matched = usage('Larus argentatus', 'species') if 'cf.' in label else usage()
                rows, conversion = self.reviews(frame, matched, parsed)
                row = rows[0]
                taxon_review.change(rows, {'name_decisions': {str(row.id): spec}})
                name_review.set_decisions(conversion, {label: spec})
                table = Table.objects.create(dataset=self.dataset, title='identification', df=frame.copy())
                taxon_matching.apply_decisions(self.dataset, table, 'verbatimIdentification')
                converted, _ = conversion_names.apply_name_decisions({'identification': frame.copy()}, conversion,
                    {'identification': [{'name': label, 'authorship': pd.NA, 'rank': pd.NA}]})
                actual = table.df.fillna('').reindex(sorted(table.df.columns), axis=1)
                expected = converted['identification'].fillna('').reindex(sorted(converted['identification'].columns), axis=1)
                pd.testing.assert_frame_equal(actual, expected)
                self.assertEqual(taxon_matching.decision_preview(row), name_review.decision_preview(conversion['labels'][0], conversion['decisions'][label]))

    def test_each_rows_qualifier_is_used_in_both_flows(self):
        frame = pd.DataFrame({'verbatimIdentification': ['Larus'] * 3, 'scientificName': ['Larus'] * 3,
                              'identificationQualifier': ['sp.', 'spp.', ''], 'taxonFormula': ['', 'existing', '']})
        rows, conversion = self.reviews(frame)
        taxon_review.initialize(rows)
        name_review.auto_accept(conversion)
        self.assertEqual(rows[0].decided_usage['decision'], 'stem')
        table = Table.objects.create(dataset=self.dataset, title='identification', df=frame.copy())
        taxon_matching.apply_decisions(self.dataset, table, 'verbatimIdentification')
        converted, _ = conversion_names.apply_name_decisions({'identification': frame}, conversion,
            {'identification': [{'name': 'Larus', 'qualifier': value} for value in frame.identificationQualifier]})
        self.assertEqual(list(table.df.taxonFormula), ['A sp.', 'existing', ''])
        self.assertEqual(list(table.df.taxonFormula), list(converted['identification'].taxonFormula))

    def test_homonyms_and_source_rank_conflicts_have_the_same_defaults(self):
        for extra in ({'taxonRank': ['order']}, {'kingdom': ['Plantae']}, {}):
            with self.subTest(extra=extra):
                TaxonNameMatch.objects.filter(dataset=self.dataset).delete()
                frame = pd.DataFrame({'verbatimIdentification': ['Larus'], 'scientificName': ['Larus'], **extra})
                rows, conversion = self.reviews(frame)
                alternative = usage(authorship='Another author', id='col-2')
                rows[0].match['alternatives'] = [alternative]
                rows[0].save()
                conversion['labels'][0]['match']['alternatives'] = [alternative]
                taxon_review.initialize(rows)
                name_review.auto_accept(conversion)
                chat = taxon_review.state(rows)
                self.assertEqual(name_review.classify(chat['labels'][0]), name_review.classify(conversion['labels'][0]))
                self.assertEqual([x['decision'] for x in chat['decisions'].values()], [x['decision'] for x in conversion['decisions'].values()])

    def test_interpreted_labels_are_never_auto_accepted(self):
        row = TaxonNameMatch.objects.create(dataset=self.dataset, source_table='identification', record_count=1,
            verbatim_label='Gull', query={'scientificName': 'Larus'}, match={'matchType': 'EXACT', 'usage': usage()}, matched_at=timezone.now())
        taxon_review.initialize([row])
        self.assertEqual(row.decision, 'pending')
        self.assertEqual(taxon_review.section([row])['summary']['groups'][0]['id'], 'check:interpretation')

    def test_missing_optional_columns_are_not_added_as_empty_columns(self):
        for kind in ('mine', 'corrected', 'empty', 'col'):
            with self.subTest(kind=kind):
                TaxonNameMatch.objects.filter(dataset=self.dataset).delete()
                frame = pd.DataFrame({'verbatimIdentification': ['Larus'], 'scientificName': ['Larus']})
                rows, conversion = self.reviews(frame)
                spec = {'decision': kind, 'scientificName': 'Larus corrected'}
                taxon_review.change(rows, {'name_decisions': {str(rows[0].id): spec}})
                name_review.set_decisions(conversion, {'Larus': spec})
                table = Table.objects.create(dataset=self.dataset, title='identification', df=frame.copy())
                taxon_matching.apply_decisions(self.dataset, table, 'verbatimIdentification')
                converted, _ = conversion_names.apply_name_decisions({'identification': frame}, conversion, {'identification': ['Larus']})
                self.assertEqual(set(table.df.columns), set(converted['identification'].columns))
                self.assertNotIn('scientificNameAuthorship', table.df)

    def test_changed_source_context_reopens_and_rematches_the_name(self):
        frame = pd.DataFrame({'verbatimIdentification': ['Larus'], 'scientificName': ['Larus'], 'kingdom': ['Animalia']})
        rows, _ = self.reviews(frame)
        taxon_review.initialize(rows)
        self.assertEqual(rows[0].decision, 'accepted')
        frame.kingdom = 'Plantae'
        rows, _ = self.reviews(frame)
        self.assertEqual(rows[0].decision, 'pending')
        self.assertEqual(rows[0].query['kingdom'], 'Plantae')
        taxon_review.initialize(rows)
        self.assertEqual(rows[0].decision, 'pending')

    def test_legacy_bulk_accept_uses_the_shared_homonym_and_context_checks(self):
        row = TaxonNameMatch.objects.create(dataset=self.dataset, source_table='identification', record_count=1,
            verbatim_label='Larus', query={'scientificName': 'Larus'},
            match={'matchType': 'EXACT', 'usage': usage(), 'alternatives': []}, matched_at=timezone.now())
        self.assertTrue(taxon_matching.bulk_acceptable(row))
        row.match['alternatives'] = [usage(id='col-2', authorship='Another author')]
        row.save(update_fields=['match'])
        self.assertFalse(taxon_matching.bulk_acceptable(row))
        self.assertEqual(taxon_matching.accept_exact_matches(self.dataset), [])
        row.match['alternatives'] = []
        row.supplied = {'hints': {'kingdom': 'Plantae'}}
        self.assertFalse(taxon_matching.bulk_acceptable(row))
        row.supplied = {'source_qualifiers': ['cf.'], 'source_qualifier_rows': 1}
        self.assertFalse(taxon_matching.bulk_acceptable(row))


class GroupedReviewApiTests(TestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(username='name-owner')
        self.dataset = Dataset.objects.create(title='Grouped review', user=self.owner)
        self.rows = [TaxonNameMatch.objects.create(dataset=self.dataset, source_table='identification', record_count=1,
            verbatim_label='Larus', context_key=context, query={'scientificName': 'Larus'},
            parsed={'usable': True, 'lossless': True, 'canonical': 'Larus', 'rank': 'genus'},
            match={'matchType': 'EXACT', 'status': 'exact', 'usage': usage()}, matched_at=timezone.now()) for context in ('first', 'second')]
        self.agent = Agent.objects.create(dataset=self.dataset, task=Task.objects.create(name='Name review', text='x'))
        self.agent.pause_for_taxon_review('Review names', {'source_table': 'identification', 'context_column': ''})
        self.client = APIClient()
        self.client.force_authenticate(self.owner)
        self.url = f'/api/taxon-matches/review/?dataset={self.dataset.id}&source_table=identification'

    def post(self, **payload):
        return self.client.post(self.url, {'dataset': self.dataset.id, 'source_table': 'identification', **payload}, format='json')

    def test_context_keys_stay_separate_and_group_actions_protect_user_choices(self):
        first, second = self.rows
        response = self.post(name_decisions={str(first.id): {'decision': 'corrected', 'scientificName': 'Larus corrected'}})
        self.assertEqual(response.status_code, 200, response.content)
        response = self.post(group_choice={'group': 'auto', 'choice': 'mine'})
        self.assertEqual(response.status_code, 200, response.content)
        first.refresh_from_db(); second.refresh_from_db()
        self.assertEqual(first.decided_usage['scientificName'], 'Larus corrected')
        self.assertEqual(second.decided_usage['decision'], 'parsed')
        response = self.client.get(self.url + '&names_view=group&names_group=auto&names_limit=1')
        self.assertEqual(response.json()['name_review']['page']['total'], 2)
        self.assertEqual(len(response.json()['name_review']['labels']), 1)

    def test_undo_and_manual_review_survive_reopening(self):
        taxon_review.initialize(self.rows)
        first = self.rows[0]
        self.assertEqual(self.post(name_decisions={str(first.id): None}).status_code, 200)
        self.assertEqual(self.post(group_choice={'group': 'auto', 'choice': 'manual'}).status_code, 200)
        rows = list(TaxonNameMatch.objects.filter(dataset=self.dataset))
        taxon_review.initialize(rows)
        self.assertEqual([row.decision for row in rows], ['pending', 'pending'])
        self.assertTrue(all(row.review_meta['auto_declined'] for row in rows))

    def test_foreign_datasets_and_closed_reviews_are_protected(self):
        self.client.force_authenticate(CustomUser.objects.create_user(username='not-name-owner'))
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.post(group_choice={'group': 'auto', 'choice': 'mine'}).status_code, 404)
        self.client.force_authenticate(self.owner)
        self.agent.completed_at = timezone.now(); self.agent.save()
        self.assertEqual(self.post(group_choice={'group': 'auto', 'choice': 'mine'}).status_code, 409)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_invalid_requests_do_not_partially_save(self):
        first = self.rows[0]
        response = self.post(name_decisions={str(first.id): {'decision': 'empty'}, 'unknown': {'decision': 'keep'}})
        self.assertEqual(response.status_code, 400)
        first.refresh_from_db()
        self.assertEqual(first.decision, 'pending')

    def test_manual_choice_also_declines_pending_automatic_defaults(self):
        self.assertEqual(self.post(group_choice={'group': 'auto', 'choice': 'manual'}).status_code, 200)
        rows = list(TaxonNameMatch.objects.filter(dataset=self.dataset))
        taxon_review.initialize(rows)
        self.assertTrue(all(row.decision == 'pending' for row in rows))

    def test_group_controls_preserve_the_author_of_an_existing_manual_decision(self):
        first = self.rows[0]
        taxon_review.change(self.rows, {'name_decisions': {str(first.id): {'decision': 'empty'}}}, self.owner)
        taxon_review.change(self.rows, {'group_choice': {'group': 'auto', 'choice': 'mine'}})
        first.refresh_from_db()
        self.assertEqual(first.decided_by_id, self.owner.id)

    def test_paging_is_bounded_and_invalid_datasets_are_rejected(self):
        response = self.client.get(self.url + '&names_offset=junk&names_limit=99999')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name_review']['page']['offset'], 0)
        self.assertEqual(response.json()['name_review']['page']['limit'], 500)
        self.assertEqual(self.client.get('/api/taxon-matches/review/?dataset=invalid').status_code, 400)
