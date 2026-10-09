import test from 'node:test'
import assert from 'node:assert/strict'
import {
  DECISION_LABELS, GROUPS, PAGE_SIZE, ariaPressed, carriedMessage, checkMessage, choiceGroups, choiceLabel,
  classificationContext, classificationNotice, decisionBody, decisionResult, groupChoiceBody, groupExplanation,
  groupOptions, groupQuery, groupTitle, isChecking, isEditable, needsConfirmation, optionNote, pageCount, progress,
  reasonText, replacementWarning, rowStatus, selectedGroupChoice, skippedMessage, unconfirmedMessage,
} from './conversionNames.mjs'

test('group copy has the requested choices and plain explanations', () => {
  assert.deepEqual(GROUPS.check.buttons, { col: 'Use COL names', mine: 'Keep my names', manual: 'Review all manually' })
  assert.equal(GROUPS.uncertain.buttons.stem, 'Use the genus or family')
  for (const kind of Object.keys(GROUPS)) {
    assert.ok(groupTitle({ kind }))
    if (kind !== 'check') assert.ok(groupExplanation({ kind }))
    assert.deepEqual(Object.keys(GROUPS[kind].buttons), kind === 'uncertain' ? ['stem', 'mine', 'manual'] : ['col', 'mine', 'manual'])
  }
  for (const code of ['kingdom', 'mixed', 'lineage', 'rank', 'id', 'name']) {
    assert.ok(groupExplanation({ kind: 'check', signature: { code, yours: 'A', col: 'B', text: 'Mixed kingdoms.' } }))
  }
  assert.equal(groupExplanation({ kind: 'check', signature: { code: 'mixed', reason: 'Rows list two kingdoms.' } }), 'Rows list two kingdoms.')
  // The server reports the choice, the automatic one included; "Review all manually" is a choice too.
  assert.equal(selectedGroupChoice({ kind: 'auto', choice: 'col' }), 'col')
  assert.equal(selectedGroupChoice({ kind: 'auto', choice: 'manual' }), 'manual')
  assert.equal(selectedGroupChoice({ kind: 'check' }), '')
  assert.equal(selectedGroupChoice({ kind: 'check', choice: 'mine' }), 'mine')
  assert.equal(ariaPressed('col', 'col'), true)
  assert.equal(ariaPressed('col', 'mine'), false)
  assert.doesNotMatch(JSON.stringify(GROUPS), /for all|Accept all|Apply to/i)
})

test('group titles distinguish every review kind and check signature', () => {
  assert.equal(groupTitle({ kind: 'check', signature: { code: 'name' } }), 'Catalogue of Life has a different name')
  assert.equal(groupTitle({ kind: 'check', signature: { code: 'rank' } }), 'Rank differs from Catalogue of Life')
  assert.equal(groupTitle({ kind: 'check', signature: { code: 'lineage' } }), 'May be another taxon with the same name')
  assert.equal(groupTitle({ kind: 'check', signature: { code: 'kingdom' } }), 'Kingdom differs from Catalogue of Life')
  assert.equal(groupTitle({ kind: 'check', signature: { code: 'mixed', yours: 'kingdom' } }), 'Listed under two kingdoms')
  assert.equal(groupTitle({ kind: 'check', signature: { code: 'mixed', yours: 'rank' } }), 'Listed at two ranks')
  assert.equal(groupTitle({ kind: 'check', signature: { code: 'id' } }), 'Your identifier points to another name')
  assert.equal(groupTitle({ kind: 'unconfirmed' }), 'Not found exactly in Catalogue of Life')
  assert.equal(groupTitle({ kind: 'spelling' }), 'Spelling differs from Catalogue of Life')
  assert.equal(groupTitle({ kind: 'uncertain' }), 'Identified to genus or family (sp.)')
  assert.equal(groupTitle({ kind: 'auto' }), 'Matched exactly')
})

test('group choice body uses the names action contract', () => {
  assert.deepEqual(groupChoiceBody('p1', { id: 'check:name' }, 'col'), {
    action: 'names', plan_id: 'p1', group_choice: { group: 'check:name', choice: 'col' },
  })
})

test('option notes include singular, plural, all count types, and omit zero counts', () => {
  assert.equal(optionNote({ broader: 1, different: 2, kept: 1, authorship: 4 }),
    '1 of these would become a broader group · 2 would change name · 1 has no COL name and keeps yours · 4 would replace your authorship')
  assert.equal(optionNote({ broader: 3, different: 1, kept: 2 }),
    '3 of these would become a broader group · 1 would change name · 2 have no COL name and keep yours')
  assert.equal(optionNote({ spelling: 31 }), "31 would get COL's spelling")
  assert.equal(optionNote({ different: 2, spelling: 31 }), "2 would change name · 31 would get COL's spelling")
  assert.equal(optionNote({ broader: 0, different: 0, kept: 0, authorship: 0 }), '')
  assert.equal(optionNote(null), '')
})

test('classification notice distinguishes mixed source systems', () => {
  assert.equal(classificationNotice({ classification_notice: null }), '')
  assert.equal(classificationNotice({ classification_notice: { names: 4, mixed: false, examples: [{ yours: 'Magnoliophyta / Eudicots', col: 'Tracheophyta / Magnoliopsida' }] } }),
    'Your file uses other higher-group names than Catalogue of Life for 4 names (e.g. Magnoliophyta / Eudicots where COL has Tracheophyta / Magnoliopsida). Only names are published, so this changes nothing.')
  assert.equal(classificationNotice({ classification_notice: { names: 2, mixed: true, examples: [{ yours: 'A / B', col: 'C / D' }] } }),
    'Your file uses two sets of higher-group names for 2 names (e.g. A / B where COL has C / D). Only names are published, so this changes nothing.')
  assert.equal(classificationNotice({ classification_notice: { names: 3, mixed: true } }), 'Your file uses two sets of higher-group names for 3 names.')
})

test('group options preserve the server counts and title lookup works', () => {
  const options = [{ decision: 'col', eligible: 5, broader: 2, different: 1, kept: 1, authorship: 1 }]
  assert.deepEqual(groupOptions({ options }), options)
  assert.equal(groupOptions({ options: [{ decision: 'mine' }] })[0].eligible, 0)
  assert.equal(groupTitle({ kind: 'auto' }), 'Matched exactly')
  assert.equal(groupTitle(null), '')
})

test('row choice, formatting, and confirmation helpers cover alternatives and warnings', () => {
  const main = { decision: 'col', usage: { id: 1, scientificName: 'Aus bus', scientificNameAuthorship: 'L.' } }
  const same = { decision: 'alternative', same_name: true, replaces: null, usage: { id: 2, scientificName: 'Aus bus' } }
  const other = { decision: 'alternative', same_name: false, usage: { id: 3, scientificName: 'Aus cus' } }
  assert.deepEqual(choiceGroups({ col_choices: [main, same, other] }), { main, sameName: [same], others: [other] })
  assert.equal(choiceLabel({ usage: { scientificName: 'Aus bus', taxonRank: 'species', classification: { kingdom: 'Plantae' } } }), 'Aus bus · species · Plantae')
  assert.equal(classificationContext({ classification: { kingdom: 'Animalia', phylum: 'Chordata', class: 'Mammalia' } }), 'Animalia › Chordata › Mammalia')
  assert.equal(DECISION_LABELS.stem, 'Published without “sp.”')
  assert.equal(needsConfirmation({ replaces: { text: 'changes genus' } }), true)
  assert.equal(needsConfirmation({ authorship_differs: true }), true)
  assert.equal(needsConfirmation({ rank_change: 'makes your genus an order' }), true)
  assert.equal(needsConfirmation(main), false)
  assert.equal(replacementWarning({ usage: { scientificName: 'Anura' }, rank_change: 'makes your genus an order' }, 2), '“Anura” makes your genus an order on 2 rows. It may be a different taxon with the same name.')
  assert.match(replacementWarning({ usage: { scientificName: 'Aus bus', scientificNameAuthorship: 'Jones' }, authorship_differs: true }, 1), /replace yours on 1 row/)
  assert.match(replacementWarning({ usage: { scientificName: 'Aus cus' }, replaces: { text: 'replaces your species' } }, 3), /Your text stays in verbatimIdentification/)
  assert.equal(decisionResult({ decision: 'col', scientificName: 'Aus bus', scientificNameAuthorship: 'L.' }), 'Aus bus L.')
  assert.equal(decisionResult({ decision: 'empty' }), 'No name published')
  assert.equal(decisionResult({ decision: 'keep' }), 'Your text as written')
  assert.equal(reasonText({ reasons: [{ text: 'Different kingdom' }] }), 'Different kingdom')
  assert.equal(reasonText({}), '')
})

test('decision body, query, and paging use bounded server requests', () => {
  assert.deepEqual(decisionBody('p', 'Aus bus', 'col', 123, { confirmCoarser: true }), {
    action: 'names', plan_id: 'p', name_decisions: { 'Aus bus': { decision: 'col', usage_id: 123, confirm_coarser: true } },
  })
  assert.deepEqual(decisionBody('p', 'Aus bus', null).name_decisions['Aus bus'], null)
  const query = new URLSearchParams(groupQuery({ group: 'check:name', offset: 100, q: 'Aus bus' }))
  assert.equal(query.get('names_view'), 'group')
  assert.equal(query.get('names_group'), 'check:name')
  assert.equal(query.get('names_offset'), '100')
  assert.equal(query.get('names_limit'), String(PAGE_SIZE))
  assert.equal(query.get('names_q'), 'Aus bus')
  assert.equal(pageCount(250), 3)
  assert.equal(pageCount(0), 1)
})

test('progress, statuses, check state, and review messages handle empty and populated data', () => {
  assert.deepEqual(progress({ labels: 20, decided: 16, unchecked: 2, groups: [{ auto: 8, undecided: 2 }, { auto: 3, undecided: 1 }] }), {
    auto: 11, need: 3, unchecked: 2, decided: 16, labels: 20, percent: 80,
    text: '11 accepted automatically · 3 need you · 2 still being checked',
  })
  assert.deepEqual(rowStatus({ decision: { by: 'user' } }), { kind: 'user', text: 'Changed by you' })
  assert.deepEqual(rowStatus({ decision: { by: 'bulk:check' } }), { kind: 'bulk', text: 'Applied to the group' })
  assert.deepEqual(rowStatus({ decision: { by: 'auto:auto' } }), { kind: 'auto', text: 'Accepted automatically' })
  assert.deepEqual(rowStatus({ decision: { decision: 'keep' }, decision_held: true }), { kind: 'held', text: 'Your text as written (until you confirm)' })
  assert.deepEqual(rowStatus({}), { kind: null, text: '' })
  assert.equal(isEditable({ status: 'review' }), true)
  assert.equal(isEditable({ status: 'complete' }), false)
  assert.equal(isChecking({ status: 'running' }), true)
  assert.equal(isChecking({ status: 'complete' }), false)
  assert.equal(checkMessage(null), null)
  assert.equal(checkMessage({ status: 'complete' }), null)
  assert.equal(checkMessage({ status: 'running', summary: { checked: 1, labels: 4 } }).spinner, true)
  assert.match(checkMessage({ status: 'error', error: 'COL unavailable', summary: { checked: 1, labels: 4 } }).text, /COL unavailable/)
  assert.equal(carriedMessage(undefined), null)
  assert.equal(carriedMessage({ decisions: 1 }), '1 earlier name decision was kept from your previous check.')
  assert.equal(carriedMessage({ dropped: 2 }), '2 earlier name decisions could not be kept because the names in your data changed.')
  assert.equal(unconfirmedMessage({ unconfirmed: 1 }), '1 held decision is kept as your own name until confirmed.')
  assert.equal(unconfirmedMessage({}), null)
  assert.equal(skippedMessage({ skipped_long: { labels: 1, rows: 1 }, max_label_chars: 500 }), '1 name is longer than 500 characters (1 row). They are not checked and are converted as they are.')
  assert.equal(skippedMessage({ skipped_long: { labels: 0, rows: 0 } }), null)
})

test('no group copy uses the removed all/apply wording', () => {
  assert.doesNotMatch(JSON.stringify(GROUPS), /for all|Accept all|Apply to/i)
})

test('a rank change is part of the option note', () => {
  assert.equal(optionNote({ eligible: 2, broader: 2, rank: 2 }), '2 of these would become a broader group · 2 would change rank')
})
