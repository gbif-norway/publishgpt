'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import config from '../config'
import { formatName } from '../utils/taxonReview.mjs'
import {
  PAGE_SIZE, carriedMessage, checkMessage, choiceGroups, choiceLabel, classificationNotice, decisionBody, decisionResult,
  groupChoiceBody, groupExplanation, groupOptions, groupQuery, groupTitle, isChecking, isEditable, needsConfirmation,
  ariaPressed, optionNote, pageCount, progress, reasonText, replacementWarning, rowStatus, selectedGroupChoice, skippedMessage, unconfirmedMessage,
} from '../utils/conversionNames.mjs'

function NameProgress({ summary }) {
  const value = progress(summary)
  return <div className="name-review-progress mb-3" aria-label={value.text}>
    <div className="progress" role="progressbar" aria-label="Name review progress" aria-valuenow={value.percent} aria-valuemin="0" aria-valuemax="100">
      <div className="progress-bar" style={{ width: `${value.percent}%` }} />
    </div>
    <div className="small text-muted mt-1">{value.text}</div>
  </div>
}

function RowChoices({ entry, busy, onDecide }) {
  const [confirming, setConfirming] = useState(null)
  const [rowError, setRowError] = useState('')
  const confirmRef = useRef(null)
  const submit = async (kind, usageId, options) => {
    const failure = await onDecide(entry.label, kind, usageId, options)
    setRowError(failure || '')
    return !failure
  }
  const usageIdOf = choice => ['alternative', 'col'].includes(choice.decision) ? choice.usage?.id : undefined
  const choose = choice => {
    if (!needsConfirmation(choice)) return submit(choice.decision, usageIdOf(choice))
    setConfirming(choice)
    return undefined
  }
  useEffect(() => { if (confirming) confirmRef.current?.focus() }, [confirming])
  const { main, sameName, others } = choiceGroups(entry)
  return <>
    <div className="d-flex flex-wrap gap-1" role="group" aria-label={`Decision for ${entry.label}`}>
      <button type="button" className="btn btn-sm btn-outline-secondary" disabled={busy} onClick={() => submit('mine')}>Keep my name</button>
      {main && <button type="button" className="btn btn-sm btn-outline-primary" disabled={busy} onClick={() => choose(main)}>
        Use {formatName(main.usage)}{needsConfirmation(main) ? '…' : ''}</button>}
      {entry.stem?.scientificName && <button type="button" className="btn btn-sm btn-outline-primary" disabled={busy}
        onClick={() => choose({ decision: 'stem', usage: entry.stem, rank_change: entry.stem_confirm })}>Use {formatName(entry.stem)}</button>}
      <button type="button" className="btn btn-sm btn-outline-secondary" disabled={busy} onClick={() => submit('empty')}>Don&apos;t publish a name</button>
    </div>
    {sameName.length > 0 && <div className="mt-2">
      <div className="small text-muted">Same-name options in Catalogue of Life:</div>
      <div className="d-flex flex-wrap gap-1 mt-1">{sameName.map(choice => <button key={choice.usage.id} type="button" className="btn btn-sm btn-outline-secondary text-start" disabled={busy} onClick={() => choose(choice)}>
        Use {choiceLabel(choice)}{choice.rank_note ? ` — ${choice.rank_note}` : ''}</button>)}</div>
    </div>}
    {others.length > 0 && <div className="mt-2">
      <label className="small text-muted" htmlFor={`name-other-${entry.label}`}>Other Catalogue of Life names</label>
      <select id={`name-other-${entry.label}`} className="form-select form-select-sm name-review-other" value="" disabled={busy}
        onChange={event => { const choice = others.find(item => String(item.usage.id) === event.target.value); if (choice) choose(choice) }}>
        <option value="">Choose another name…</option>{others.map(choice => <option key={choice.usage.id} value={choice.usage.id}>{choiceLabel(choice)}{choice.replaces ? ` — ${choice.replaces.text}` : ''}</option>)}
      </select>
    </div>}
    {main?.corrects && <div className="small text-muted mt-1">COL {main.corrects}.</div>}
    {confirming && <div className="alert alert-warning small py-2 mt-2 mb-0" role="alert">
      {replacementWarning(confirming, entry.rows)}
      <div className="d-flex flex-wrap gap-1 mt-1">
        <button ref={confirmRef} type="button" className="btn btn-sm btn-warning" disabled={busy}
          onClick={async () => { if (await submit(confirming.decision, usageIdOf(confirming), { confirmCoarser: true })) setConfirming(null) }}>Replace with {formatName(confirming.usage)}</button>
        <button type="button" className="btn btn-sm btn-link" onClick={() => setConfirming(null)}>Cancel</button>
      </div>
    </div>}
    {rowError && <div className="text-danger small mt-1" role="alert">{rowError}</div>}
  </>
}

function NameRow({ entry, editable, busy, onDecide }) {
  const status = rowStatus(entry)
  const held = Boolean(entry.decision_unconfirmed || entry.decision_held)
  const result = held ? status.text : decisionResult(entry.decision)
  const undo = () => onDecide(entry.label, null)
  return <article className="name-review-row py-3">
    <div className="min-w-0">
      <div className="fw-semibold text-break">{entry.label}</div>
      <div className="small text-muted">{entry.rows.toLocaleString()} {entry.rows === 1 ? 'row' : 'rows'}</div>
      {reasonText(entry) && <div className="small text-muted mt-1">{reasonText(entry)}</div>}
      <div className="small mt-1">→ {result || <span className="text-muted">No decision yet</span>}
        {status.text && !held && <span className="text-muted ms-2">{status.text}</span>}
        {editable && entry.decision?.by === 'user' && !held && <button type="button" className="btn btn-sm btn-link p-0 ms-2" disabled={busy} onClick={undo}>Undo</button>}
      </div>
    </div>
    {held && <div className="mt-2">
      <div className="small text-danger-emphasis">{entry.decision_held?.kind === 'authorship'
        ? 'This earlier choice would replace your authorship with Catalogue of Life’s, so your name is kept until you confirm it.'
        : 'This earlier choice replaces your name with a coarser or different taxon, so your name is kept until you confirm it.'}</div>
      {editable && <div className="d-flex flex-wrap gap-2 mt-1">
        <button type="button" className="btn btn-sm btn-outline-warning" disabled={busy}
          onClick={() => onDecide(entry.label, entry.decision.decision, entry.decision.usageId || undefined, { confirmCoarser: true })}>Confirm {entry.decision.scientificName}</button>
        <button type="button" className="btn btn-sm btn-success" disabled={busy} onClick={() => onDecide(entry.label, 'mine')}>Keep my name</button>
      </div>}
    </div>}
    {editable && <div className="name-review-row-options mt-2"><RowChoices entry={entry} busy={busy} onDecide={onDecide} /></div>}
  </article>
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
    fetch(`${url}?${queryString}`, { credentials: 'include', signal: controller.signal })
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
      : <div className="name-review-rows">{rows.map(entry => <NameRow key={entry.label} entry={entry} editable={editable} busy={busy} onDecide={onDecide} />)}</div>}
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

function NameGroup({ group, planId, updated, datasetId, url, editable, busy, send, onDecide }) {
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
      await send(groupChoiceBody(planId, group, choice))
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
      {toggle('mine', 'Keep my names', !editable || busy || !options.find(option => option.decision === 'mine')?.eligible, 'No undecided names to keep')}
      {toggle('manual', 'Review all manually', !editable || busy || !manualEligible, 'No names need a manual decision')}
    </div>
    {note && <div className="small text-muted mt-2">{note}</div>}
    {error && <div className="alert alert-danger small py-2 mt-2 mb-0" role="alert">{error}</div>}
    {modalOpen && <NameReviewModal group={group} updated={updated} datasetId={datasetId} url={url} editable={editable} busy={busy} onDecide={onDecide} onClose={close} opener={opener} />}
  </section>
}

const fallbackLabel = (option, partial) => option.value === 'preserve'
  ? (partial ? 'Leave scientificName empty (the text fills verbatimIdentification wherever that would otherwise be empty)'
    : 'Leave scientificName empty (the text stays in verbatimIdentification)')
  : `Copy the supplied text into scientificName${option.value.startsWith('identification.') ? ' (identification)' : ''}`

export default function ConversionNameReview({ state, send, disabled, datasetId, onRefresh, questions = [], decisions = {}, onChoose }) {
  const nameReview = state?.name_review
  const editable = isEditable(state)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const checking = isChecking(nameReview)
  const updated = state?.updated_at
  const planId = state?.plan?.id
  const url = `${config.baseUrl}/api/datasets/${datasetId}/conversion/`
  useEffect(() => {
    if (!checking || !onRefresh) return undefined
    const interval = setInterval(onRefresh, 3000)
    return () => clearInterval(interval)
  }, [checking, onRefresh])
  const act = useCallback(async body => {
    setBusy(true); setError('')
    try { await send(body) } catch (err) { setError(err.message); throw err } finally { setBusy(false) }
  }, [send])
  const actRow = useCallback(async (label, kind, usageId, options) => {
    try { await act(decisionBody(planId, label, kind, usageId, options)); return null } catch (err) { return err.message }
  }, [act, planId])
  if (!nameReview?.summary?.labels && !skippedMessage(nameReview?.summary)) return null
  const { summary } = nameReview
  const groups = summary.groups || []
  const message = checkMessage(nameReview)
  const skipped = skippedMessage(summary)
  const held = unconfirmedMessage(summary)
  const notice = classificationNotice(summary)
  const needsReview = summary.decided < summary.labels || Boolean(held) || checking || summary.checked < summary.labels || nameReview.status === 'error' || Boolean(skipped) || questions.some(question => state.unresolved?.includes(question.id))
  const groupProps = { planId, updated, datasetId, url, editable, busy: disabled || busy, send: act, onDecide: actRow }
  return <details className="review-disclosure name-review" open={needsReview}>
    <summary><i className={`bi ${needsReview ? 'bi-flower1' : 'bi-check-circle'} me-2`} aria-hidden="true" /><span id="scientific-names-heading">Scientific names</span><small>{checking ? 'Checking…' : skipped ? 'Some names weren’t checked' : nameReview.status === 'error' ? 'Check interrupted' : `${summary.decided.toLocaleString()} of ${summary.labels.toLocaleString()} decided`}</small></summary>
    <div className="mt-3">
      <p className="small text-muted mb-2">Names checked with Catalogue of Life. Only names are published; your text stays in verbatimIdentification.</p>
      <NameProgress summary={summary} />
      {notice && <p className="small text-muted">{notice}</p>}
      {editable && (summary.checked < summary.labels || nameReview.status === 'error') && !checking && <button type="button" className="btn btn-sm btn-outline-secondary mb-2" disabled={disabled || busy} onClick={() => act({ action: 'check_names', plan_id: planId })}>Check names again</button>}
      {held && <div className="alert alert-warning small py-2" role="status">{held}</div>}
      {carriedMessage(nameReview.carried) && <p className="small text-muted">{carriedMessage(nameReview.carried)}</p>}
      {skipped && <p className="small text-warning-emphasis">{skipped}</p>}
      {summary.truncated > 0 && <p className="small text-muted">Only the {summary.labels.toLocaleString()} most frequent names are listed; {summary.truncated.toLocaleString()} others are converted as they are.</p>}
      {message && <div className={`alert alert-${message.variant} small py-2`} role="status">{message.spinner && <span className="spinner-border spinner-border-sm me-2" />}{message.text}</div>}
      {error && <div className="alert alert-danger small py-2" role="alert">{error}</div>}
      {groups.filter(group => !['auto', 'uncertain'].includes(group.kind)).map(group => <NameGroup key={group.id} group={group} {...groupProps} />)}
      {groups.some(group => ['auto', 'uncertain'].includes(group.kind)) && <div className="name-review-preaccepted mt-3">
        <div className="small fw-semibold text-muted mb-1">Already accepted</div>
        {groups.filter(group => ['auto', 'uncertain'].includes(group.kind)).map(group => <NameGroup key={group.id} group={group} {...groupProps} />)}
      </div>}
      {questions.map(question => <div key={question.id} className="border-top pt-2 mt-3" data-decision-id={question.id}>
        <label htmlFor={question.id} className="small fw-semibold">For names you don&apos;t decide above{questions.length > 1 ? ` (${state?.plan?.tables?.[question.table]?.name || 'table'})` : ''}</label>
        <p className="small text-muted mb-1">{summary.decided >= summary.labels && !summary.truncated && !summary.skipped_long?.labels
          ? 'Every name has a decision above, so this applies to no row.'
          : 'A Data Package scientificName holds only the name, without its author. Decide names above where you can.'}</p>
        <select id={question.id} className="form-select form-select-sm" value={decisions[question.id] || ''} disabled={disabled || !onChoose} onChange={event => onChoose(question.id, event.target.value)}>
          {!decisions[question.id] && <option value="">Choose…</option>}
          {question.options.map(option => <option key={option.value} value={option.value}>{fallbackLabel(option, Boolean(state?.plan?.columns?.find(column => column.id === question.id)?.verbatim_source))}</option>)}
        </select>
      </div>)}
    </div>
  </details>
}
