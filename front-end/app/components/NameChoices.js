'use client'

import { useEffect, useRef, useState } from 'react'
import {
  CORRECTION_BUTTON, CORRECTION_TITLE, EMPTY_LABEL, EMPTY_TITLE, KEEP_LABEL, KEEP_TITLE, SEARCH_LABEL, formatName,
} from '../utils/nameReview.mjs'
import NameCorrectionForm from './NameCorrectionForm'
import TaxonSearch from './TaxonSearch'

// The choices both name reviews offer for one name. `choices` comes from each review's adapter (chatChoices,
// conversionChoices): { main, stem, sameName, others, corrects }, each COL choice being
// { decision, usage, usageId, text, warning }. A choice with a warning waits for a confirming second click.
// onDecide({ decision, usageId, confirmCoarser, scientificName }) resolves to an error message, or null when saved;
// decision is one of col, alternative, stem, search, keep, corrected or empty.
export default function NameChoices({ label, choices, busy, onDecide }) {
  const [mode, setMode] = useState(null)
  const [confirming, setConfirming] = useState(null)
  const [error, setError] = useState('')
  const confirmRef = useRef(null)
  useEffect(() => { if (confirming) confirmRef.current?.focus() }, [confirming])
  const { main, stem, sameName = [], others = [], corrects } = choices || {}

  // A saved decision ends any confirmation or form left open for an earlier choice.
  const submit = async (payload) => {
    const failure = await onDecide(payload)
    setError(failure || '')
    if (!failure) setConfirming(null)
    return !failure
  }
  const choose = (choice) => {
    setMode(null)
    if (choice.warning) setConfirming(choice)
    else submit({ decision: choice.decision, usageId: choice.usageId })
  }
  const toggle = (next) => {
    setConfirming(null)
    setMode(mode === next ? null : next)
  }
  const colButton = (choice) => choice && (
    <button type="button" className="btn btn-sm btn-outline-primary" disabled={busy} onClick={() => choose(choice)}>
      {choice.text}{choice.warning ? '…' : ''}
    </button>
  )

  return (
    <>
      <div className="d-flex flex-wrap gap-1" role="group" aria-label={`Decision for ${label}`}>
        {colButton(main)}
        {colButton(stem)}
        <button type="button" className="btn btn-sm btn-outline-secondary" disabled={busy} title={KEEP_TITLE}
          onClick={() => submit({ decision: 'keep' })}>{KEEP_LABEL}</button>
        <button type="button" className={`btn btn-sm btn-outline-secondary${mode === 'correct' ? ' active' : ''}`} disabled={busy}
          title={CORRECTION_TITLE} aria-pressed={mode === 'correct'} onClick={() => toggle('correct')}>{CORRECTION_BUTTON}</button>
        <button type="button" className="btn btn-sm btn-outline-secondary" disabled={busy} title={EMPTY_TITLE}
          onClick={() => submit({ decision: 'empty' })}>{EMPTY_LABEL}</button>
      </div>
      {mode === 'correct' && (
        <div className="mt-2">
          <NameCorrectionForm label={label} disabled={busy} onCancel={() => setMode(null)}
            onSave={async (name) => { if (await submit({ decision: 'corrected', scientificName: name })) setMode(null) }} />
        </div>
      )}
      {sameName.length > 0 && (
        <div className="mt-2">
          <div className="small text-muted">Same-name options in Catalogue of Life:</div>
          <div className="d-flex flex-wrap gap-1 mt-1">
            {sameName.map((choice) => (
              <button key={choice.usageId} type="button" className="btn btn-sm btn-outline-secondary text-start" disabled={busy}
                onClick={() => choose(choice)}>{choice.text}{choice.warning ? '…' : ''}</button>
            ))}
          </div>
        </div>
      )}
      <div className="d-flex flex-wrap align-items-end gap-2 mt-2">
        {others.length > 0 && (
          <label className="small text-muted flex-grow-1 mb-0">Other Catalogue of Life names
            <select className="form-select form-select-sm name-review-other mt-1" value="" disabled={busy}
              onChange={(event) => {
                const choice = others.find((item) => String(item.usageId) === event.target.value)
                if (choice) choose(choice)
              }}>
              <option value="">Choose another name…</option>
              {others.map((choice) => <option key={choice.usageId} value={choice.usageId}>{choice.text}</option>)}
            </select>
          </label>
        )}
        <button type="button" className={`btn btn-sm btn-outline-secondary${mode === 'search' ? ' active' : ''}`} disabled={busy}
          aria-pressed={mode === 'search'} onClick={() => toggle('search')}>{SEARCH_LABEL}</button>
      </div>
      {mode === 'search' && (
        <div className="mt-2">
          <TaxonSearch disabled={busy}
            onPick={async (usageId) => { if (await submit({ decision: 'search', usageId })) setMode(null) }} />
        </div>
      )}
      {corrects && <div className="small text-muted mt-1">{corrects}</div>}
      {confirming && (
        <div className="alert alert-warning small py-2 mt-2 mb-0" role="alert">
          {confirming.warning}
          <div className="d-flex flex-wrap gap-1 mt-1">
            <button ref={confirmRef} type="button" className="btn btn-sm btn-warning" disabled={busy}
              onClick={async () => {
                if (await submit({ decision: confirming.decision, usageId: confirming.usageId, confirmCoarser: true })) setConfirming(null)
              }}>
              Replace with {formatName(confirming.usage)}
            </button>
            <button type="button" className="btn btn-sm btn-link" onClick={() => setConfirming(null)}>Cancel</button>
          </div>
        </div>
      )}
      {error && <div className="text-danger small mt-1" role="alert">{error}</div>}
    </>
  )
}
