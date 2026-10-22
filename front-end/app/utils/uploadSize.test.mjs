import test from 'node:test'
import assert from 'node:assert/strict'

import { formatFileSize, oversizedFilesError, parseUploadLimitMB, sendUpload, uploadSizeError } from './uploadSize.mjs'

const MB = 1024 * 1024
const file = (name, size) => ({ name, size })

test('falls back to the default unless the configured limit is a positive number', () => {
  assert.equal(parseUploadLimitMB('150', 200), 150)
  for (const value of [undefined, '', '0', '-5', 'abc', 'Infinity']) {
    assert.equal(parseUploadLimitMB(value, 200), 200)
  }
})

test('formats sizes without showing an over-limit size as the limit', () => {
  assert.equal(formatFileSize(10), '1 KB')
  assert.equal(formatFileSize(1536), '2 KB')
  assert.equal(formatFileSize(200 * MB), '200.0 MB')
  assert.equal(formatFileSize(200 * MB + 1), '200.1 MB')
})

test('names each file over the limit when files are sent one at a time', () => {
  assert.equal(oversizedFilesError([file('a.csv', 150 * MB), file('b.csv', 150 * MB)], 200), null)
  assert.equal(oversizedFilesError([file('a.csv', 250 * MB)], 200), 'a.csv (250.0 MB) is larger than the 200 MB upload limit.')
  assert.equal(
    oversizedFilesError([file('a.csv', 250 * MB), file('b.csv', 1), file('c.xlsx', 300 * MB)], 200),
    'a.csv (250.0 MB), c.xlsx (300.0 MB) are larger than the 200 MB upload limit.',
  )
})

test('checks the total of files sent together', () => {
  assert.equal(uploadSizeError([], 200), null)
  assert.equal(uploadSizeError([file('a.csv', 200 * MB)], 200), null)
  assert.equal(uploadSizeError([file('a.zip', 201 * MB)], 200), 'a.zip (201.0 MB) is larger than the 200 MB upload limit.')
  assert.equal(uploadSizeError([file('a.csv', 100 * MB), file('b.csv', 100 * MB)], 200), null)
  assert.equal(
    uploadSizeError([file('a.csv', 150 * MB), file('b.csv', 100 * MB)], 200),
    'These files total 250.0 MB, more than the 200 MB upload limit. Remove some files to continue.',
  )
})

test('reports a refused upload as the size limit, not a generic failure', async () => {
  const refused = () => Promise.reject(new TypeError('Load failed'))
  await assert.rejects(sendUpload('/x', {}, 200, refused), { message: /couldn't confirm the upload.*at most 200 MB/ })
  const tooLarge = () => Promise.resolve({ status: 413 })
  await assert.rejects(sendUpload('/x', {}, 200, tooLarge), { message: 'The upload is larger than the 200 MB limit.' })
  const response = { status: 400 }
  assert.equal(await sendUpload('/x', {}, 200, () => Promise.resolve(response)), response)
})
