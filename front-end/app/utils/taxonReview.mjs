// Pure helpers for the chat's taxon name review; the choices and wording it shares with the conversion are in nameReview.mjs.
import { choiceLabel, decisionSummary, formatName, replacementWarning } from './nameReview.mjs'

export const STATUS_LABELS = {
  exact: { label: 'Exact match', variant: 'success' },
  variant: { label: 'Close spelling', variant: 'warning' },
  higher_rank: { label: 'Higher rank only', variant: 'warning' },
  ambiguous: { label: 'Ambiguous', variant: 'warning' },
  none: { label: 'No match', variant: 'secondary' },
}

export const statusInfo = (row) => STATUS_LABELS[row?.match?.status] || STATUS_LABELS.none

export const isPending = (row) => row.decision === 'pending'

export const filterRows = (rows, { view = 'pending', query = '' } = {}) => {
  const needle = query.trim().toLowerCase()
  return rows.filter((row) => {
    if (view === 'pending' && !isPending(row)) return false
    if (view === 'reviewed' && isPending(row)) return false
    if (!needle) return true
    const haystack = [
      row.verbatim_label,
      row.context_key,
      row.query?.scientificName,
      row.match?.usage?.scientificName,
    ].filter(Boolean).join(' ').toLowerCase()
    return haystack.includes(needle)
  })
}

export const countByDecision = (rows) => rows.reduce((counts, row) => {
  counts[row.decision] = (counts[row.decision] || 0) + 1
  counts.records[row.decision] = (counts.records[row.decision] || 0) + (row.record_count || 0)
  return counts
}, { records: {} })

// The server's written_fields kind of a row's decision (api.taxon_matching.decided_kind).
export const decidedKind = (row) => {
  if (row?.decision === 'keep_original') return row.decided_usage?.kind || 'keep'
  return { accepted: 'col', corrected: 'corrected', empty: 'empty' }[row?.decision] || null
}

export const decisionResult = (row) => decisionSummary(decidedKind(row), row?.decided_usage || {})

// The shared choices for one row: COL's suggestion, then its alternatives, the same names first. choice_checks says
// what each would replace (api.taxon_matching.choice_check), as the conversion's col_choices does.
export const chatChoices = (row) => {
  const usage = row?.match?.usage
  const choice = (decision, choiceUsage, check) => {
    const { replaces = null, authorship_differs: authorshipDiffers = false, rank_change: rankChange = null } = check || {}
    const confirm = { usage: choiceUsage, replaces, authorship_differs: authorshipDiffers, rank_change: rankChange }
    return { decision, usage: choiceUsage, usageId: decision === 'alternative' ? choiceUsage.id : undefined, replaces,
      warning: replacementWarning(confirm, row.record_count) }
  }
  const alternatives = (row?.match?.alternatives || [])
    .map((alternative) => choice('alternative', alternative, row.choice_checks?.alternatives?.[String(alternative.id)]))
  return {
    main: usage ? { ...choice('col', usage, row.choice_checks?.suggestion), text: `Use ${formatName(usage)}` } : null,
    stem: null,
    sameName: alternatives.filter((item) => !item.replaces).map((item) => ({ ...item, text: `Use ${choiceLabel(item)}` })),
    others: alternatives.filter((item) => item.replaces).map((item) => ({ ...item, text: `${choiceLabel(item)} — ${item.replaces.text}` })),
    corrects: '',
  }
}

// The decide request for one of the shared choices (see NameChoices).
export const chatDecisionBody = ({ decision, usageId, confirmCoarser, scientificName }) => {
  const confirm = confirmCoarser ? { confirm_coarser: true } : {}
  if (decision === 'col') return { decision: 'accepted', ...confirm }
  if (decision === 'alternative') return { decision: 'accepted', usage_id: usageId, ...confirm }
  // A name the reviewer searched for and picked is itself the explicit choice, so it is sent confirmed.
  if (decision === 'search') return { decision: 'accepted', usage_id: usageId, confirm_coarser: true }
  if (decision === 'keep') return { decision: 'keep_original' }
  if (decision === 'corrected') return { decision: 'corrected', scientificName }
  return { decision }
}
