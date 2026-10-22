import test from 'node:test'
import assert from 'node:assert/strict'

import { formatName } from './nameReview.mjs'
import { chatChoices, chatDecisionBody, decidedKind, decisionResult, filterRows, statusInfo } from './taxonReview.mjs'

const rows = [
  { verbatim_label: 'N_silvestris', decision: 'pending', record_count: 55,
    query: { scientificName: 'Nothrus silvestris' }, match: { status: 'exact' } },
  { verbatim_label: 'Pająki', decision: 'accepted', record_count: 87,
    query: { scientificName: 'Araneae' }, match: { status: 'exact', usage: { scientificName: 'Araneae' } } },
  { verbatim_label: 'Zieminek', decision: 'keep_original', record_count: 87, match: { status: 'none' } },
  { verbatim_label: 'Neodiscopoma splendida', decision: 'corrected', record_count: 149,
    match: { status: 'higher_rank' } },
]

test('filters by review state and searches labels and interpretations', () => {
  assert.deepEqual(filterRows(rows).map((row) => row.verbatim_label), ['N_silvestris'])
  assert.equal(filterRows(rows, { view: 'reviewed' }).length, 3)
  assert.deepEqual(
    filterRows(rows, { view: 'all', query: 'nothrus' }).map((row) => row.verbatim_label),
    ['N_silvestris'],
  )
  assert.deepEqual(
    filterRows(rows, { view: 'all', query: 'araneae' }).map((row) => row.verbatim_label),
    ['Pająki'],
  )
})

test('formats names and statuses', () => {
  assert.equal(formatName({ scientificName: 'Nothrus silvestris', scientificNameAuthorship: 'Nicolet, 1855' }),
    'Nothrus silvestris Nicolet, 1855')
  assert.equal(formatName(null), '')
  assert.equal(statusInfo({ match: { status: 'higher_rank' } }).label, 'Higher rank only')
  assert.equal(statusInfo({}).label, 'No match')
})

test('chat rows offer the shared choices and send them as decide requests', () => {
  const row = {
    record_count: 3,
    match: { usage: { id: 'D', scientificName: 'Dinychus' }, alternatives: [
      { id: 'D2', scientificName: 'Dinychus', taxonRank: 'subgenus' }, { id: 'U', scientificName: 'Uropoda', taxonRank: 'genus' }] },
    choice_checks: {
      suggestion: { replaces: null, authorship_differs: false, rank_change: null },
      alternatives: { D2: { replaces: null, authorship_differs: true, rank_change: null }, U: { replaces: { text: 'replaces your genus' } } },
    },
  }
  const choices = chatChoices(row)
  assert.deepEqual([choices.main.text, choices.main.warning], ['Use Dinychus', ''])
  assert.deepEqual(choices.sameName.map((choice) => [choice.text, choice.usageId]), [['Use Dinychus · subgenus', 'D2']])
  // A different authorship needs the same confirmation as in the conversion.
  assert.match(choices.sameName[0].warning, /^Catalogue of Life writes the authorship of “Dinychus”/)
  assert.deepEqual(choices.others.map((choice) => choice.warning),
    ['“Uropoda” replaces your genus on 3 rows. Your text stays in verbatimIdentification.'])
  assert.deepEqual(chatDecisionBody({ decision: 'col' }), { decision: 'accepted' })
  assert.deepEqual(chatDecisionBody({ decision: 'alternative', usageId: 'U', confirmCoarser: true }),
    { decision: 'accepted', usage_id: 'U', confirm_coarser: true })
  assert.deepEqual(chatDecisionBody({ decision: 'search', usageId: 'S' }), { decision: 'accepted', usage_id: 'S', confirm_coarser: true })
  assert.deepEqual(chatDecisionBody({ decision: 'keep' }), { decision: 'keep_original' })
  assert.deepEqual(chatDecisionBody({ decision: 'corrected', scientificName: 'Dinychus' }), { decision: 'corrected', scientificName: 'Dinychus' })
  assert.deepEqual(chatDecisionBody({ decision: 'empty' }), { decision: 'empty' })
})

test('chat decisions are summarised like the conversion\'s', () => {
  assert.equal(decidedKind({ decision: 'keep_original', decided_usage: {} }), 'keep')
  assert.equal(decidedKind({ decision: 'pending' }), null)
  assert.equal(decisionResult({ decision: 'keep_original', decided_usage: { kind: 'parsed', scientificName: 'Aus bus', scientificNameAuthorship: 'L.', taxonRank: 'species' } }),
    'Aus bus L. (species)')
  assert.equal(decisionResult({ decision: 'keep_original', decided_usage: { kind: 'keep' } }), 'Your text as written')
  assert.equal(decisionResult({ decision: 'empty', decided_usage: {} }), 'No name published')
  assert.equal(decisionResult({ decision: 'pending', decided_usage: {} }), '')
})
