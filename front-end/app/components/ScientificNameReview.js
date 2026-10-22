'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { KEEP_LABEL } from '../utils/nameReview.mjs'
import {
  PAGE_SIZE, reviewChoices, reviewDecision, decisionBody, decisionResult,
  groupExplanation, groupOptions, groupQuery, groupTitle,
  ariaPressed, optionNote, pageCount, progress, reasonText, rowStatus, selectedGroupChoice,
  classificationNotice, unconfirmedMessage,
} from '../utils/nameReviewState.mjs'
import NameReviewItem from './NameReviewItem'
import NameMatchDetails from './NameMatchDetails'

function NameProgress({ summary }) {
  const value = progress(summary)
  return <div className="name-review-progress mb-3" aria-label={value.text}>
    <div className="progress" role="progressbar" aria-label="Name review progress" aria-valuenow={value.percent} aria-valuemin="0" aria-valuemax="100">
      <div className="progress-bar" style={{ width: `${value.percent}%` }} />
    </div>
    <div className="small text-muted mt-1">{value.text}</div>
  </div>
}

function NameRow({ entry, editable, busy, onDecide }) {
  const status = rowStatus(entry)
  const held = Boolean(entry.decision_unconfirmed || entry.decision_held)
  const notice = held && <div className="mt-2">
    <div className="small text-danger-emphasis">{entry.decision_held?.kind === 'authorship'
      ? 'This earlier choice would replace your authorship with Catalogue of Life’s, so your name is kept until you confirm it.'
      : 'This earlier choice replaces your name with a coarser or different taxon, so your name is kept until you confirm it.'}</div>
    {editable && <div className="d-flex flex-wrap gap-2 mt-1">
      <button type="button" className="btn btn-sm btn-outline-warning" disabled={busy}
        onClick={() => onDecide(entry.key || entry.label, entry.decision.decision, entry.decision.usageId || undefined, { confirmCoarser: true })}>Confirm {entry.decision.scientificName}</button>
      <button type="button" className="btn btn-sm btn-success" disabled={busy} onClick={() => onDecide(entry.key || entry.label, 'mine')}>{KEEP_LABEL}</button>
    </div>}
  </div>
  return <NameReviewItem label={entry.label} count={entry.rows} noun="row"
    details={<><NameMatchDetails entry={entry} />{reasonText(entry) && <div className="small text-muted mt-1">{reasonText(entry)}</div>}</>}
    result={held ? status.text : decisionResult(entry.decision)} status={held ? '' : status.text} preview={entry.preview} notice={notice}
    onUndo={entry.decision && !held ? () => onDecide(entry.key || entry.label, null) : null}
    editable={editable} busy={busy} choices={reviewChoices(entry)}
    onDecide={payload => onDecide(entry.key || entry.label, ...reviewDecision(payload))} />
}

function NameRows({ group, updated, datasetId, url, editable, busy, onDecide }) {
  const [rows, setRows] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [query, setQuery] = useState('')
  const [error, setError] = useState('')
  const searchRef = useRef(null)
  useEffect(() => { searchRef.current?.focus() }, [])
  useEffect(() => {
    if (!datasetId) return undefined
    const controller = new AbortController()
    const queryString = groupQuery({ group: group.id, offset: page * PAGE_SIZE, limit: PAGE_SIZE, q: query })
    fetch(`${url}${url.includes('?') ? '&' : '?'}${queryString}`, { credentials: 'include', signal: controller.signal })
      .then(async response => {
        const data = await response.json()
        if (!response.ok) throw new Error(data.detail || 'The names could not be loaded.')
        setRows(data.name_review.labels || [])
        setTotal(data.name_review.page?.total || 0)
        setError('')
      }).catch(err => { if (err.name !== 'AbortError') setError(err.message) })
    return () => controller.abort()
  }, [datasetId, group.id, page, query, updated, url])
  const pages = pageCount(total)
  return <>
    <label className="visually-hidden" htmlFor={`name-search-${group.id}`}>Search names</label>
    <input ref={searchRef} id={`name-search-${group.id}`} type="search" maxLength={100} className="form-control form-control-sm mb-2" placeholder="Search names" value={query}
      onChange={event => { setPage(0); setQuery(event.target.value) }} />
    {error && <div className="alert alert-danger small py-2" role="alert">{error}</div>}
    {!rows.length ? <p className="small text-muted mb-0">{query ? 'No names match your search.' : 'No names in this group.'}</p>
      : <div className="name-review-rows">{rows.map(entry => <NameRow key={entry.key || entry.label} entry={entry} editable={editable} busy={busy} onDecide={onDecide} />)}</div>}
    {pages > 1 && <nav className="d-flex align-items-center gap-2 small mt-2" aria-label={`${groupTitle(group)} pages`}>
      <button type="button" className="btn btn-sm btn-outline-secondary" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</button>
      <span>Page {page + 1} of {pages}</span>
      <button type="button" className="btn btn-sm btn-outline-secondary" disabled={page >= pages - 1} onClick={() => setPage(page + 1)}>Next</button>
    </nav>}
  </>
}

function NameReviewModal({ group, updated, datasetId, url, editable, busy, onDecide, onClose, opener }) {
  const dialogRef = useRef(null)
  useEffect(() => {
    const previousOverflow = document.body.style.overflow
    const openerElement = opener?.current
    document.body.style.overflow = 'hidden'
    const dialog = dialogRef.current
    dialog?.focus()
    const onKeyDown = event => {
      if (event.key === 'Escape') { event.stopPropagation(); onClose(); return }
      if (event.key !== 'Tab' || !dialog) return
      const focusable = [...dialog.querySelectorAll('button:not(:disabled), input:not(:disabled), select:not(:disabled), [tabindex="0"]')]
      if (!focusable.length) { event.preventDefault(); dialog.focus(); return }
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (!dialog.contains(document.activeElement) || document.activeElement === dialog) { event.preventDefault(); (event.shiftKey ? last : first).focus() }
      else if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = previousOverflow
      openerElement?.focus()
    }
  }, [onClose, opener])
  return <div className="name-review-backdrop">
    <section ref={dialogRef} className="name-review-modal" role="dialog" aria-modal="true" aria-labelledby="name-review-modal-title" tabIndex={-1}>
      <div className="name-review-modal-header">
        <h2 id="name-review-modal-title" className="h5 mb-0">{groupTitle(group)} · {group.labels.toLocaleString()} {group.labels === 1 ? 'name' : 'names'}</h2>
        <button type="button" className="btn-close" aria-label="Close review" onClick={onClose} />
      </div>
      <p className="small text-muted mt-2 mb-3">{groupExplanation(group)}</p>
      <div className="name-review-modal-list"><NameRows group={group} updated={updated} datasetId={datasetId} url={url} editable={editable} busy={busy} onDecide={onDecide} /></div>
    </section>
  </div>
}

function NameGroup({ group, updated, datasetId, url, editable, busy, send, onDecide }) {
  const [modalOpen, setModalOpen] = useState(false)
  const [error, setError] = useState('')
  const opener = useRef(null)
  const options = groupOptions(group)
  const selected = selectedGroupChoice(group)
  const note = optionNote(options.find(option => ['col', 'stem'].includes(option.decision)))
  const manualEligible = (group.labels || 0) > (group.by_user || 0)
  const choose = async choice => {
    setError('')
    try {
      await send({ group_choice: { group: group.id, choice } })
      if (choice === 'manual') setModalOpen(true)
    } catch (err) { setError(err.message || 'This group could not be updated.') }
  }
  const close = useCallback(() => setModalOpen(false), [])
  const toggle = (choice, label, disabled, title = '') => <button key={choice} type="button"
    className={`btn btn-sm ${ariaPressed(selected, choice) ? 'btn-success' : 'btn-outline-secondary'}`} aria-pressed={ariaPressed(selected, choice)}
    disabled={disabled} title={disabled ? (!editable ? 'Name review is not editable' : busy ? 'Name review is updating' : title) : undefined} onClick={() => choose(choice)}>
    {selected === choice && <i className="bi bi-check-lg me-1" aria-hidden="true" />}{label}
  </button>
  return <section className="name-review-group">
    <div className="name-review-group-header">
      <h3 className="h6 mb-0">{groupTitle(group)} <span className="text-muted fw-normal">· {group.labels.toLocaleString()} {group.labels === 1 ? 'name' : 'names'}</span></h3>
      <button ref={opener} type="button" className="btn btn-sm btn-outline-secondary" disabled={!datasetId} onClick={() => setModalOpen(true)}>Review</button>
    </div>
    <p className="small text-muted mb-2">{groupExplanation(group)}</p>
    <div className="name-review-toggles" role="group" aria-label={`Group choice for ${groupTitle(group)}`}>
      {group.kind === 'uncertain'
        ? toggle('stem', 'Use the genus or family', !editable || busy || !options.find(option => option.decision === 'stem')?.eligible, 'No names can use the genus or family')
        : toggle('col', 'Use COL names', !editable || busy || !options.find(option => option.decision === 'col')?.eligible, 'No names have a Catalogue of Life name')}
      {toggle('mine', 'Keep original names', !editable || busy || !options.find(option => option.decision === 'mine')?.eligible, 'No undecided names to keep')}
      {toggle('manual', 'Review all manually', !editable || busy || !manualEligible, 'No names need a manual decision')}
    </div>
    {note && <div className="small text-muted mt-2">{note}</div>}
    {error && <div className="alert alert-danger small py-2 mt-2 mb-0" role="alert">{error}</div>}
    {modalOpen && <NameReviewModal group={group} updated={updated} datasetId={datasetId} url={url} editable={editable} busy={busy} onDecide={onDecide} onClose={close} opener={opener} />}
  </section>
}

export default function ScientificNameReview({ nameReview, updated, datasetId, url, editable, busy, send }) {
  const actRow = useCallback(async (label, kind, usageId, options) => {
    try {
      const { name_decisions } = decisionBody(undefined, label, kind, usageId, options)
      await send({ name_decisions })
      return null
    } catch (error) { return error.message || 'This name could not be saved.' }
  }, [send])
  const groups = nameReview?.summary?.groups || []
  const notice = classificationNotice(nameReview?.summary)
  const held = unconfirmedMessage(nameReview?.summary)
  const props = { updated, datasetId, url, editable, busy, send, onDecide: actRow }
  return <>
    <NameProgress summary={nameReview?.summary || {}} />
    {notice && <p className="small text-muted">{notice}</p>}
    {held && <div className="alert alert-warning small py-2" role="status">{held}</div>}
    {groups.filter(group => !['auto', 'uncertain'].includes(group.kind)).map(group => <NameGroup key={group.id} group={group} {...props} />)}
    {groups.some(group => ['auto', 'uncertain'].includes(group.kind)) && <div className="name-review-preaccepted mt-3">
      <div className="small fw-semibold text-muted mb-1">Exact and genus or family names</div>
      {groups.filter(group => ['auto', 'uncertain'].includes(group.kind)).map(group => <NameGroup key={group.id} group={group} {...props} />)}
    </div>}
  </>
}
