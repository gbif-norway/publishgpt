from django.test import SimpleTestCase

from api.dwca_conversion import SAMPLE_SIZE, SAMPLING_PROTOCOL, build_plan, convert
from api.dwca_humboldt import ECO
from api.dwca_import import DWC, ConversionError, read_inputs
from api.dwca_value_ledger import build_value_disposition_ledger

# Shaped like production dataset 590: survey events with a sampling protocol and the area fished,
# per-fish measurements and per-site habitat scores in eMoF.
EVENTS = (b'eventID,eventDate,samplingProtocol,sampleSizeValue,sampleSizeUnit\n'
          b'e1,2020-10-01,Electric fishing,187.05,square meters\n'
          b'e2,2020-10-02,Electric fishing,323,square meters\n'
          b'e3,2020-10-03,Electric fishing | Kick net,400,square meters\n'
          b'e4,2020-10-04,,,\n')
OCCURRENCES = (b'eventID,occurrenceID,scientificName,occurrenceStatus\n'
               b'e1,o1,Salmo trutta,present\ne2,o2,Salmo trutta,present\n')
FACTS = (b'eventID,occurrenceID,measurementType,measurementValue,measurementUnit,measurementMethod\n'
         b'e1,o1,fork length,25.5,cm,\n'
         b'e2,o2,weight,151.8,g,\n'
         b'e1,,Refuge index,4.75,,"Garcia De Jalon et al. (1993) Principios y tecnicas de gestion de la pesca"\n')


def archive(events=EVENTS, *extra):
    return read_inputs([('event.csv', events), ('occurrence.csv', OCCURRENCES), ('extendedmeasurementorfact.csv', FACTS), *extra])


def answers(plan, **chosen):
    return {**{item['id']: item['options'][0]['value'] for item in plan['issues']}, **chosen}


def column(plan, term, table=0):
    return next(item for item in plan['columns'] if item['table'] == table and item['term'] == term)


def disposition(report, term, source_table='event.csv'):
    return next(item for item in report['columns'] if item['source_table'] == source_table and item['term'] == term)


def rows(frame, **match):
    return frame[(frame[list(match)] == list(match.values())).all(axis=1)]


class SamplingContextTests(SimpleTestCase):
    def test_survey_events_keep_protocols_and_sample_size(self):
        source = archive()
        plan = build_plan(source)
        for term in (SAMPLING_PROTOCOL, *SAMPLE_SIZE):
            item = column(plan, term)
            self.assertEqual(item['default'], 'derive')
            self.assertNotIn('unmapped', item)
            self.assertNotIn(item['id'], {issue['id'] for issue in plan['issues']})
            self.assertEqual(next(choice for choice in plan['automatic_choices'] if choice['id'] == item['id'])['family'], 'events')
        frames, report = convert(source, plan, answers(plan, **{'event-category': 'survey'}))
        self.assertTrue(report['validation']['valid'])
        events = frames['event'].set_index('eventID')['event_pk']

        protocols = frames['protocol'].set_index('protocolName')['protocol_pk']
        self.assertEqual(sorted(protocols.index), ['Electric fishing', 'Kick net'])
        links = {(event, protocol) for event, protocol in zip(frames['event-protocol']['event_fk'], frames['event-protocol']['protocol_fk'])}
        self.assertEqual(links, {(events[e], protocols['Electric fishing']) for e in ('e1', 'e2', 'e3')} | {(events['e3'], protocols['Kick net'])})

        surveys = frames['survey'].set_index('event_fk')
        self.assertEqual(set(surveys.index), {events['e1'], events['e2'], events['e3']})
        self.assertEqual((surveys.loc[events['e1'], 'sampleSizeValue'], surveys.loc[events['e1'], 'sampleSizeUnit']), ('187.05', 'square meters'))
        self.assertEqual(surveys.loc[events['e1'], 'samplingProtocol_fk'], protocols['Electric fishing'])
        # A list keeps its full text on the survey; no single protocol stands for it.
        self.assertEqual(surveys.loc[events['e3'], 'samplingProtocol'], 'Electric fishing | Kick net')
        self.assertEqual(surveys.loc[events['e3'], 'samplingProtocol_fk'], '')
        self.assertNotIn('sampleSizeValue', set(frames['event-assertion']['assertionType']))

        protocol_column = disposition(report, SAMPLING_PROTOCOL)
        self.assertEqual((protocol_column['disposition'], protocol_column['mapped_rows'], protocol_column['retained_only_rows']), ('derived', 3, 0))
        self.assertEqual(protocol_column['target_counts'],
                         {'event-protocol.protocol_fk': 3, 'protocol.protocolName': 3, 'survey.samplingProtocol': 3})
        self.assertEqual(disposition(report, SAMPLE_SIZE[0])['target_counts'], {'survey.sampleSizeValue': 3})
        self.assertEqual(disposition(report, SAMPLE_SIZE[1])['target_counts'], {'survey.sampleSizeUnit': 3})
        ledger = {entry['source_term']: entry for entry in build_value_disposition_ledger(plan, report, frames)['source_terms']
                  if entry['source_table'] == 'event.csv'}
        self.assertEqual((ledger[SAMPLE_SIZE[0]]['derived_values'], ledger[SAMPLE_SIZE[0]]['originals_only_values']), (3, 0))
        self.assertEqual(ledger[SAMPLE_SIZE[0]]['output_fields'], ['survey.sampleSizeValue'])

    def test_assertion_type_is_filled_from_the_supplied_type_and_methods_stay_text(self):
        source = archive()
        plan = build_plan(source)
        frames, report = convert(source, plan, answers(plan))
        for name in ('occurrence-assertion', 'event-assertion'):
            facts = frames[name][frames[name]['verbatimAssertionType'] != '']
            self.assertTrue(len(facts))
            self.assertEqual(facts['assertionType'].tolist(), facts['verbatimAssertionType'].tolist())
        self.assertEqual(sorted(frames['occurrence-assertion']['assertionType']), ['fork length', 'weight'])
        refuge = rows(frames['event-assertion'], assertionType='Refuge index').iloc[0]
        self.assertTrue(refuge['assertionProtocols'].startswith('Garcia De Jalon'))
        self.assertEqual(refuge.get('assertionProtocol_fk', ''), '')
        self.assertNotIn('Garcia', ' '.join(frames['protocol'].get('protocolName', [])))
        measurement_type = disposition(report, DWC + 'measurementType', 'extendedmeasurementorfact.csv')
        self.assertEqual(measurement_type['also_copied_to'], 'declared assertion subject → assertionType')

    def test_other_events_get_a_sample_size_assertion_and_unpaired_values_stay_in_originals(self):
        events = (b'eventID,eventDate,sampleSizeValue,sampleSizeUnit\n'
                  b'e1,2020-10-01,187.05,square meters\ne2,2020-10-02,50,\n')
        source = archive(events)
        plan = build_plan(source)
        frames, report = convert(source, plan, answers(plan, **{'event-category': 'occurrence'}))
        self.assertTrue(report['validation']['valid'])
        self.assertNotIn('survey', frames)
        event_keys = frames['event'].set_index('eventID')['event_pk']
        sizes = rows(frames['event-assertion'], assertionType='sampleSizeValue')
        self.assertEqual(len(sizes), 1)
        self.assertEqual(sizes.iloc[0][['event_fk', 'assertionTypeIRI', 'assertionValue', 'assertionUnit']].tolist(),
                         [event_keys['e1'], DWC + 'sampleSizeValue', '187.05', 'square meters'])
        withheld = [item for item in report['withheld_values'] if item['term'] == SAMPLE_SIZE[0]]
        self.assertEqual([(item['source_row'], item['value']) for item in withheld], [(2, '50')])
        value_column = disposition(report, SAMPLE_SIZE[0])
        self.assertEqual((value_column['mapped_rows'], value_column['retained_only_rows']), (1, 1))
        self.assertEqual(value_column['target_counts'], {'event-assertion.assertionValue': 1})
        ledger = next(entry for entry in build_value_disposition_ledger(plan, report, frames)['source_terms'] if entry['source_term'] == SAMPLE_SIZE[0])
        self.assertEqual((ledger['derived_values'], ledger['withheld_invalid_values']), (1, 1))

    def test_keeping_the_columns_in_originals_creates_no_sampling_records(self):
        source = archive()
        plan = build_plan(source)
        kept = {column(plan, term)['id']: 'preserve' for term in (SAMPLING_PROTOCOL, *SAMPLE_SIZE)}
        frames, report = convert(source, plan, answers(plan, **kept))
        self.assertTrue(report['validation']['valid'])
        self.assertFalse({'protocol', 'event-protocol', 'survey'} & set(frames))
        self.assertEqual(disposition(report, SAMPLING_PROTOCOL)['disposition'], 'retained-unmapped')

    def test_events_with_humboldt_surveys_keep_the_core_sample_size_as_an_assertion(self):
        events = (b'eventID,eventCategory,samplingProtocol,sampleSizeValue,sampleSizeUnit\n'
                  b'e1,survey,Electric fishing,187.05,square meters\ne2,survey,Electric fishing,323,square meters\n')
        source = read_inputs([('event.csv', events), ('humboldt.csv', b'eventID,' + ECO.encode() + b'siteCount\ne1,3\n')])
        plan = build_plan(source)
        frames, report = convert(source, plan, answers(plan))
        self.assertTrue(report['validation']['valid'])
        event_keys = frames['event'].set_index('eventID')['event_pk']
        surveys = frames['survey'].set_index('event_fk')
        self.assertEqual(surveys.loc[event_keys['e1'], 'siteCount'], '3')
        self.assertEqual(surveys.loc[event_keys['e1'], 'sampleSizeValue'], '')
        self.assertEqual(surveys.loc[event_keys['e2'], 'sampleSizeValue'], '323')
        self.assertEqual(rows(frames['event-assertion'], assertionType='sampleSizeValue')['event_fk'].tolist(), [event_keys['e1']])
        self.assertEqual(disposition(report, SAMPLE_SIZE[0])['target_counts'],
                         {'survey.sampleSizeValue': 1, 'event-assertion.assertionValue': 1})

    def test_combined_occurrence_events_must_agree_on_sampling(self):
        occurrences = (b'occurrenceID,eventID,eventDate,scientificName,occurrenceStatus,samplingProtocol\n'
                       b'o1,e1,2020-10-01,Salmo trutta,present,Electric fishing\n'
                       b'o2,e1,2020-10-01,Salmo trutta,present,Kick net\n')
        source = read_inputs([('occurrence.csv', occurrences)])
        plan = build_plan(source)
        with self.assertRaises(ConversionError) as raised:
            convert(source, plan, answers(plan, **{'event-grain': 'by_id'}))
        self.assertEqual(raised.exception.category, 'conflict')
        self.assertIn('event-grain', raised.exception.decision_ids)
        self.assertIn(column(plan, SAMPLING_PROTOCOL)['id'], raised.exception.decision_ids)
        frames, report = convert(source, plan, answers(plan, **{'event-grain': 'per_row'}))
        self.assertTrue(report['validation']['valid'])
        self.assertEqual(len(frames['event-protocol']), 2)
        self.assertEqual(len(set(frames['event-protocol']['event_fk'])), 2)

    def test_depth_children_hold_the_sampling_of_their_depth(self):
        occurrences = (b'occurrenceID,eventID,eventDate,minimumDepthInMeters,maximumDepthInMeters,scientificName,occurrenceStatus,samplingProtocol\n'
                       b'o1,cast-1,2020-10-01,0,10,Calanus finmarchicus,present,Net haul\n'
                       b'o2,cast-1,2020-10-01,0,10,Calanus finmarchicus,present,Net haul\n'
                       b'o3,cast-1,2020-10-01,50,60,Calanus finmarchicus,present,Water bottle\n')
        source = read_inputs([('occurrence.csv', occurrences)])
        plan = build_plan(source)
        frames, report = convert(source, plan, answers(plan, **{'event-grain': 'by_id_depth'}))
        self.assertTrue(report['validation']['valid'])
        events = frames['event']
        children = events[events['parentEvent_fk'] != ''].set_index('minimumDepthInMeters')['event_pk']
        protocols = frames['protocol'].set_index('protocol_pk')['protocolName']
        links = {(event, protocols[protocol]) for event, protocol in zip(frames['event-protocol']['event_fk'], frames['event-protocol']['protocol_fk'])}
        self.assertEqual(links, {(children['0'], 'Net haul'), (children['50'], 'Water bottle')})
        self.assertEqual(set(frames['occurrence']['event_fk']), set(children))

    def test_a_separator_without_protocols_stays_in_originals(self):
        source = archive(b'eventID,eventDate,samplingProtocol\ne1,2020-10-01, | \ne2,2020-10-02,Electric fishing\n'
                         b'e3,2020-10-03,https://example.org/method \n')
        plan = build_plan(source)
        frames, report = convert(source, plan, answers(plan))
        self.assertEqual(frames['protocol']['protocolName'].tolist(), ['Electric fishing', ''])
        self.assertEqual(frames['protocol']['protocolReferences'].tolist(), ['', 'https://example.org/method '])
        self.assertEqual(len(frames['event-protocol']), 2)
        self.assertEqual([(item['source_row'], item['value']) for item in report['withheld_values'] if item['term'] == SAMPLING_PROTOCOL],
                         [(1, ' | ')])
        protocol_column = disposition(report, SAMPLING_PROTOCOL)
        self.assertEqual((protocol_column['mapped_rows'], protocol_column['retained_only_rows']), (2, 1))

    def test_nested_taxon_occurrence_tables_keep_separate_protocol_keys(self):
        from api.test_dwca_taxon import manifest_archive
        terms = [DWC + 'occurrenceID', DWC + 'occurrenceStatus', SAMPLING_PROTOCOL]
        source = read_inputs(manifest_archive([
            ('first.csv', DWC + 'Occurrence', terms, [['join-a', 'occ-1', 'present', 'Net haul']]),
            ('second.csv', DWC + 'Occurrence', terms, [['join-a', 'occ-2', 'present', 'Net haul']]),
        ]).items())
        plan = build_plan(source)
        frames, report = convert(source, plan, answers(plan))
        self.assertTrue(report['validation']['valid'])
        self.assertEqual(frames['protocol']['protocol_pk'].nunique(), 2)
        self.assertEqual(frames['protocol']['protocolName'].tolist(), ['Net haul', 'Net haul'])
