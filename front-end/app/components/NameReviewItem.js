'use client'

import { previewText } from '../utils/nameReview.mjs'
import NameChoices from './NameChoices'

// One name in either review: the name as written, its decision and exactly what that writes, and the shared choices.
// `details` and `notice` carry what only one review knows (COL's status and interpretation, a held decision).
export default function NameReviewItem({
  label, count, noun, details, result, status, preview, notice, onUndo, editable, busy, choices, onDecide,
}) {
  return (
    <article className="name-review-row py-3">
      <div className="min-w-0">
        <div className="fw-semibold text-break">{label}</div>
        <div className="small text-muted">{count.toLocaleString()} {count === 1 ? noun : `${noun}s`}</div>
        {details}
        <div className="small mt-1">→ {result || <span className="text-muted">No decision yet</span>}
          {status && <span className="text-muted ms-2">{status}</span>}
          {editable && onUndo && (
            <button type="button" className="btn btn-sm btn-link p-0 ms-2" disabled={busy} onClick={onUndo}>Undo</button>
          )}
        </div>
        {preview?.length > 0 && <div className="small text-muted name-review-preview">Writes {previewText(preview)}</div>}
      </div>
      {notice}
      {editable && (
        <div className="name-review-row-options mt-2">
          <NameChoices label={label} choices={choices} busy={busy} onDecide={onDecide} />
        </div>
      )}
    </article>
  )
}
