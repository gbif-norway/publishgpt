import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import config from '../config.js'
import { getCsrfToken } from '../utils/csrf.js'
import { formatName } from '../utils/nameReview.mjs'
import {
  chatChoices,
  chatDecisionBody,
  countByDecision,
  decisionResult,
  filterRows,
  isPending,
  statusInfo,
} from '../utils/taxonReview.mjs'
import NameReviewItem from './NameReviewItem'

const PAGE_SIZE = 50
const FOCUSABLE = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'

const postJson = async (path, body) => {
  const csrfToken = await getCsrfToken()
  const headers = { 'Content-Type': 'application/json' }
  if (csrfToken) headers['X-CSRFToken'] = csrfToken
  const response = await fetch(`${config.baseUrl}${path}`, {
    method: 'POST',
    headers,
    credentials: 'include',
    body: JSON.stringify(body),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = data?.detail || Object.values(data || {}).flat().join(' ')
    throw new Error(detail || 'The decision could not be saved.')
  }
  return data
}

// What only the chat's review knows about a name: its source context, qualifier, COL's suggestion and the interpretation.
function RowDetails({ row }) {
  const status = statusInfo(row)
  const usage = row.match?.usage
  const aids = row.review_aids || {}
  const aidLines = [
    ['GBIF Backbone', aids.gbifBackbone],
    ['Newer COL release', aids.checklistBankXR],
  ].filter(([, aid]) => aid && ['exact', 'variant'].includes(aid.status))

  return (
    <div className="small mt-1">
      {(row.context_key || row.identification_qualifier) && (
        <div className="d-flex flex-wrap align-items-center gap-2 text-muted">
          {row.context_key && <span>{row.context_key}</span>}
          {row.identification_qualifier && <span className="badge text-bg-light border">qualifier: {row.identification_qualifier}</span>}
        </div>
      )}
      <div className="d-flex flex-wrap align-items-center gap-2">
        <span className="text-muted">Catalogue of Life:</span>
        {usage ? <span>{formatName(usage)}</span> : <span className="text-muted">no suggestion</span>}
        {usage?.taxonRank && <span className="text-muted">{usage.taxonRank}</span>}
        <span className={`badge text-bg-${status.variant}`}>{status.label}</span>
      </div>
      {row.match?.acceptedUsage && (
        <div className="text-muted">Synonym; COL accepts {formatName(row.match.acceptedUsage)}</div>
      )}
      {row.preprocessed && (
        <div className="text-muted">
          <i className="bi bi-lightbulb me-1" aria-hidden="true"></i>
          Interpreted as <em>{row.query?.scientificName}</em>
          {row.preprocessing_note && <> — {row.preprocessing_note}</>}
        </div>
      )}
      {aidLines.map(([source, aid]) => (
        <div key={source} className="text-muted">
          {source}: {formatName(aid)}{aid.taxonRank ? ` (${aid.taxonRank})` : ''}
          {' '}<span className="fst-italic">may not yet be reflected on GBIF.org</span>
        </div>
      ))}
    </div>
  )
}

export default function TaxonReviewModal({ datasetId, scope, show, onClose, onDone, editable }) {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [view, setView] = useState('pending')
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(0)
  const [busyIds, setBusyIds] = useState(new Set())
  const [confirmBulk, setConfirmBulk] = useState(false)
  const [bulkBusy, setBulkBusy] = useState(false)
  const bodyRef = useRef(null)
  const dialogRef = useRef(null)
  // The parent re-renders while it polls; a ref keeps the keyboard effect from re-running.
  const onCloseRef = useRef(onClose)
  useEffect(() => { onCloseRef.current = onClose }, [onClose])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ dataset: datasetId })
      if (scope?.source_table) {
        params.set('source_table', scope.source_table)
        params.set('context_column', scope.context_column || '')
      }
      const response = await fetch(`${config.baseUrl}/api/taxon-matches/?${params}`, {
        credentials: 'include',
      })
      if (!response.ok) throw new Error('The taxon names could not be loaded.')
      const data = await response.json()
      setRows(Array.isArray(data) ? data : (data.results || []))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [datasetId, scope?.source_table, scope?.context_column])

  useEffect(() => {
    if (show) load()
  }, [show, load])

  // Keyboard: move focus into the dialog, keep Tab inside it, close on Escape, and return focus
  // to whatever opened it.
  useEffect(() => {
    if (!show) return undefined
    const opener = document.activeElement
    dialogRef.current?.focus()
    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        onCloseRef.current()
        return
      }
      if (event.key !== 'Tab' || !dialogRef.current) return
      const focusable = [...dialogRef.current.querySelectorAll(FOCUSABLE)]
        .filter((element) => !element.disabled && element.offsetParent !== null)
      if (!focusable.length) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      const active = document.activeElement
      const inside = dialogRef.current.contains(active)
      if (event.shiftKey && (active === first || active === dialogRef.current || !inside)) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && (active === last || !inside)) {
        event.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      if (opener && typeof opener.focus === 'function') opener.focus()
    }
  }, [show])

  useEffect(() => { setPage(0) }, [view, query])

  const replaceRows = (updated) => {
    const byId = new Map(updated.map((row) => [row.id, row]))
    setRows((current) => current.map((row) => byId.get(row.id) || row))
  }

  // Resolves to the error message, or null once saved; the shared choices show it beside the name.
  const undo = async (row) => {
    const failure = await decide(row, { decision: 'pending' })
    setError(failure && `${row.verbatim_label}: ${failure}`)
  }

  const decide = async (row, payload) => {
    setBusyIds((current) => new Set(current).add(row.id))
    try {
      replaceRows([await postJson(`/api/taxon-matches/${row.id}/decide/`, payload)])
      return null
    } catch (err) {
      return err.message
    } finally {
      setBusyIds((current) => {
        const next = new Set(current)
        next.delete(row.id)
        return next
      })
    }
  }

  const bulkRows = useMemo(() => rows.filter((row) => row.bulk_acceptable), [rows])

  const acceptBulk = async () => {
    setBulkBusy(true)
    setError(null)
    try {
      const data = await postJson('/api/taxon-matches/accept-exact/', { dataset: datasetId })
      replaceRows(data.results || [])
      setConfirmBulk(false)
    } catch (err) {
      setError(err.message)
    } finally {
      setBulkBusy(false)
    }
  }

  const visible = useMemo(() => filterRows(rows, { view, query }), [rows, view, query])
  const pageCount = Math.max(1, Math.ceil(visible.length / PAGE_SIZE))
  const pageRows = visible.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
  const counts = countByDecision(rows)
  const pendingCount = counts.pending || 0
  const release = rows.find((row) => row.col_release?.alias)?.col_release?.alias

  if (!show) return null

  return (
    <>
      <div
        className="modal fade show d-block"
        role="dialog"
        tabIndex="-1"
        aria-modal="true"
        aria-labelledby={`taxon-review-title-${datasetId}`}
        onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}
      >
        <div className="modal-dialog modal-xl modal-dialog-scrollable taxon-review-modal">
          <div className="modal-content" ref={dialogRef} tabIndex="-1">
            <div className="modal-header align-items-start">
              <div>
                <h2 className="modal-title fs-5" id={`taxon-review-title-${datasetId}`}>Review taxon names</h2>
                <p className="small text-muted mb-0 mt-1">
                  Suggestions from Catalogue of Life{release ? ` (${release})` : ''}, the taxonomy GBIF.org uses.
                  A match means the name was found, not that the identification is right. Your original
                  names are always kept.
                </p>
              </div>
              <button type="button" className="btn-close" aria-label="Close" onClick={onClose}></button>
            </div>

            <div className="modal-body" ref={bodyRef}>
              <div className="d-flex flex-wrap align-items-center gap-2 mb-3">
                <div className="btn-group btn-group-sm" role="group" aria-label="Filter names">
                  {[
                    ['pending', `Needs review (${pendingCount})`],
                    ['reviewed', `Reviewed (${rows.length - pendingCount})`],
                    ['all', `All (${rows.length})`],
                  ].map(([value, label]) => (
                    <button key={value} type="button"
                      className={`btn btn-outline-secondary${view === value ? ' active' : ''}`}
                      onClick={() => setView(value)} aria-pressed={view === value}>
                      {label}
                    </button>
                  ))}
                </div>
                <input type="search" className="form-control form-control-sm taxon-review-filter"
                  placeholder="Filter names" value={query} onChange={(event) => setQuery(event.target.value)}
                  aria-label="Filter names" />
                {editable && (
                  <button type="button" className="btn btn-sm btn-success ms-auto"
                    disabled={bulkRows.length === 0 || bulkBusy} onClick={() => setConfirmBulk(true)}>
                    Accept {bulkRows.length} exact {bulkRows.length === 1 ? 'match' : 'matches'}…
                  </button>
                )}
              </div>

              {!editable && (
                <div className="alert alert-secondary small py-2">
                  This review is finished, so the decisions can no longer be changed here.
                </div>
              )}

              {editable && confirmBulk && (
                <div className="alert alert-success small">
                  <p className="mb-2">
                    These names are written exactly as in Catalogue of Life and have no qualifier such as
                    “sp.” or “cf.”. Accepting them sets the scientific name, authorship and rank
                    for {bulkRows.reduce((sum, row) => sum + row.record_count, 0)} records:
                  </p>
                  <div className="taxon-bulk-list mb-2">
                    {bulkRows.map((row) => (
                      <div key={row.id}>
                        {row.verbatim_label} → <strong>{formatName(row.match.usage)}</strong>
                        <span className="text-muted"> ({row.match.usage.taxonRank}, {row.record_count} records)</span>
                      </div>
                    ))}
                  </div>
                  <button type="button" className="btn btn-sm btn-success me-2" onClick={acceptBulk} disabled={bulkBusy}>
                    {bulkBusy ? 'Accepting…' : `Accept ${bulkRows.length}`}
                  </button>
                  <button type="button" className="btn btn-sm btn-link" onClick={() => setConfirmBulk(false)} disabled={bulkBusy}>
                    Cancel
                  </button>
                </div>
              )}

              {error && <div className="alert alert-danger small" role="alert">{error}</div>}
              {loading && <div className="text-muted small">Loading taxon names…</div>}

              {!loading && visible.length === 0 && (
                <div className="text-muted small py-4 text-center">
                  {rows.length === 0 ? 'There are no matched taxon names yet.' : 'No names in this view.'}
                </div>
              )}

              {pageRows.length > 0 && (
                <div className="name-review-rows">
                  {pageRows.map((row) => (
                    <NameReviewItem key={row.id} label={row.verbatim_label} count={row.record_count} noun="record"
                      details={<RowDetails row={row} />} result={decisionResult(row)}
                      status={isPending(row) ? '' : 'Changed by you'} preview={row.preview}
                      onUndo={isPending(row) ? null : () => undo(row)} editable={editable} busy={busyIds.has(row.id)}
                      choices={chatChoices(row)} onDecide={(payload) => decide(row, chatDecisionBody(payload))} />
                  ))}
                </div>
              )}

              {pageCount > 1 && (
                <nav className="d-flex align-items-center gap-2 small" aria-label="Taxon name pages">
                  <button type="button" className="btn btn-sm btn-outline-secondary" disabled={page === 0}
                    onClick={() => { setPage(page - 1); bodyRef.current?.scrollTo(0, 0) }}>
                    Previous
                  </button>
                  <span>Page {page + 1} of {pageCount}</span>
                  <button type="button" className="btn btn-sm btn-outline-secondary" disabled={page >= pageCount - 1}
                    onClick={() => { setPage(page + 1); bodyRef.current?.scrollTo(0, 0) }}>
                    Next
                  </button>
                </nav>
              )}
            </div>

            <div className="modal-footer justify-content-between">
              <span className="small text-muted">
                {rows.length - pendingCount} of {rows.length} names reviewed
              </span>
              <div className="d-flex gap-2">
                <button type="button" className="btn btn-outline-secondary" onClick={onClose}>Close</button>
                {editable && (
                  <button type="button" className="btn btn-primary"
                    disabled={loading || rows.length === 0 || busyIds.size > 0 || bulkBusy}
                    onClick={onDone}>
                    Done, apply my decisions
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
      <div className="modal-backdrop fade show"></div>
    </>
  )
}
