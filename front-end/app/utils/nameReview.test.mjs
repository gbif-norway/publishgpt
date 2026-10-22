import test from 'node:test'
import assert from 'node:assert/strict'

import { previewText } from './nameReview.mjs'

test('a preview says exactly what each column gets', () => {
  assert.equal(previewText([
    { field: 'scientificName', how: 'set', value: 'Aus bus' },
    { field: 'scientificNameAuthorship', how: 'yours', value: 'L.' },
    { field: 'taxonRank', how: 'yours', value: null },
    { field: 'taxonFormula', how: 'empty', value: null },
  ]), 'scientificName “Aus bus” · scientificNameAuthorship as in your data, else “L.” · taxonRank as in your data · taxonFormula empty')
  assert.equal(previewText([]), '')
  assert.equal(previewText(undefined), '')
})

test('row-specific qualifier previews show every possible written value', () => {
  assert.equal(previewText([{ field: 'taxonFormula', how: 'yours', value: 'A sp.',
    values: ['A sp.', 'A spp.'], note: 'from each row’s qualifier' }]),
  'taxonFormula as in your data, else “A sp.” or “A spp.” (from each row’s qualifier)')
})
