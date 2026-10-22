'use client'

import { useEffect, useId, useRef, useState } from 'react'
import { CORRECTION_HELP, MAX_CORRECTED_NAME_CHARS } from '../utils/nameReview.mjs'

// The "Type a correction" form of both name reviews: one name, prefilled with the label as written.
export default function NameCorrectionForm({ label, disabled, onSave, onCancel }) {
  const id = useId()
  const [name, setName] = useState(label || '')
  const inputRef = useRef(null)
  useEffect(() => { inputRef.current?.focus() }, [])

  return (
    <form className="d-grid gap-1" onSubmit={(event) => { event.preventDefault(); onSave(name) }}>
      <label className="small" htmlFor={id}>Corrected name</label>
      <input ref={inputRef} id={id} className="form-control form-control-sm" value={name} required
        maxLength={MAX_CORRECTED_NAME_CHARS} disabled={disabled} aria-describedby={`${id}-help`}
        onChange={(event) => setName(event.target.value)} />
      <div id={`${id}-help`} className="form-text mt-0">{CORRECTION_HELP}</div>
      <div className="d-flex gap-1 mt-1">
        <button type="submit" className="btn btn-sm btn-primary" disabled={disabled || !name.trim()}>Save</button>
        <button type="button" className="btn btn-sm btn-link" onClick={onCancel} disabled={disabled}>Cancel</button>
      </div>
    </form>
  )
}
