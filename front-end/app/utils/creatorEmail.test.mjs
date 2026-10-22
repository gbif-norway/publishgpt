import test from 'node:test'
import assert from 'node:assert/strict'

import { publishableEmail } from './creatorEmail.mjs'

test('drops the ORCID login placeholder but keeps real addresses', () => {
  assert.equal(publishableEmail('0009-0006-1096-3259@ORCID.org'), '')
  assert.equal(publishableEmail(' ada@example.org '), 'ada@example.org')
  assert.equal(publishableEmail(null), '')
})
