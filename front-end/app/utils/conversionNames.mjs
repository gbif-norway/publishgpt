// Pure helpers for the conversion's scientific-name review.
import { formatName } from './taxonReview.mjs'

export const DECISION_LABELS = {
  parsed: 'Parsed name and authorship',
  col: 'Catalogue of Life name',
  alternative: 'Other Catalogue of Life name',
  keep: 'Kept as supplied',
  empty: 'No name published',
  stem: 'Published without “sp.”',
}

export const GROUPS = {
  check: { title: 'Check against Catalogue of Life', buttons: { col: 'Use COL names', mine: 'Keep my names', manual: 'Review all manually' } },
  unconfirmed: { title: 'Not found exactly in Catalogue of Life', buttons: { col: 'Use COL names', mine: 'Keep my names', manual: 'Review all manually' } },
  spelling: { title: 'Spelling differs from Catalogue of Life', buttons: { col: 'Use COL names', mine: 'Keep my names', manual: 'Review all manually' } },
  uncertain: { title: 'Identified to genus or family (sp.)', buttons: { stem: 'Use the genus or family', mine: 'Keep my names', manual: 'Review all manually' } },
  auto: { title: 'Matched exactly', buttons: { col: 'Use COL names', mine: 'Keep my names', manual: 'Review all manually' } },
}

const CONTEXT_RANKS = ['kingdom', 'phylum', 'class']
export const PAGE_SIZE = 100

export const classificationContext = usage => CONTEXT_RANKS.map(rank => usage?.classification?.[rank]).filter(Boolean).join(' › ')

export const choiceGroups = entry => {
  const choices = entry?.col_choices || []
  const main = choices.find(choice => choice.decision === 'col') || null
  const alternatives = choices.filter(choice => choice.decision === 'alternative')
  const fresh = alternatives.filter(choice => !main || String(choice.usage.id) !== String(main.usage.id))
  return { main, sameName: fresh.filter(choice => choice.same_name && !choice.replaces), others: fresh.filter(choice => !(choice.same_name && !choice.replaces)) }
}

export const choiceLabel = choice => {
  const usage = choice?.usage
  if (!usage) return ''
  return [formatName(usage), usage.taxonRank, classificationContext(usage)].filter(Boolean).join(' · ')
}

export const needsConfirmation = choice => Boolean(choice?.replaces || choice?.authorship_differs || choice?.rank_change)

export const replacementWarning = (choice, rows) => {
  if (!needsConfirmation(choice)) return ''
  const count = rows ? ` on ${rows.toLocaleString()} ${rows === 1 ? 'row' : 'rows'}` : ''
  if (!choice.replaces && choice.rank_change) return `“${choice.usage.scientificName}” ${choice.rank_change}${count}. It may be a different taxon with the same name.`
  if (!choice.replaces) return `Catalogue of Life writes the authorship of “${choice.usage.scientificName}” as “${choice.usage.scientificNameAuthorship}”, which is not the authorship in your data; it would replace yours${count}. It may be a different taxon with the same name.`
  return `“${choice.usage.scientificName}” ${choice.replaces.text}${count}. Your text stays in verbatimIdentification.`
}

export const decisionResult = decision => {
  if (!decision) return ''
  if (decision.decision === 'empty') return 'No name published'
  if (decision.decision === 'keep') return 'Your text as written'
  return `${formatName(decision)}${decision.taxonRank ? ` (${decision.taxonRank})` : ''}`
}

const CHECK_TITLES = {
  name: 'Catalogue of Life has a different name',
  rank: 'Rank differs from Catalogue of Life',
  lineage: 'May be another taxon with the same name',
  kingdom: 'Kingdom differs from Catalogue of Life',
  id: 'Your identifier points to another name',
}

export const groupTitle = group => {
  if (group?.kind !== 'check') return GROUPS[group?.kind]?.title || ''
  const signature = group.signature || {}
  if (signature.code === 'mixed') return signature.yours === 'rank' ? 'Listed at two ranks' : 'Listed under two kingdoms'
  return CHECK_TITLES[signature.code] || GROUPS.check.title
}

export const groupExplanation = group => {
  const signature = group?.signature || {}
  if (group?.kind !== 'check') return ({
    auto: 'Catalogue of Life matched these names to accepted names.',
    uncertain: 'Choose whether to publish the genus or family without the uncertain ending.',
    spelling: 'Catalogue of Life suggests a different spelling for these names.',
    unconfirmed: 'Catalogue of Life could not confirm these names.',
  })[group?.kind] || ''
  if (signature.code === 'kingdom') return `Your file says ${signature.yours}; Catalogue of Life has these names in ${signature.col}.`
  if (signature.code === 'mixed') return signature.text || signature.reason || signature.first_reason || group?.reasons?.[0]?.text || 'Your file lists this name with more than one classification.'
  if (signature.code === 'lineage') return signature.text || signature.reason || 'Catalogue of Life has another use of this name in the group your file uses.'
  if (signature.code === 'rank') return `Your file gives this name the rank ${signature.yours}; Catalogue of Life has it as ${signature.col}.`
  if (signature.code === 'id') return 'Your scientificNameID or taxonID points to another name in Catalogue of Life.'
  if (signature.code === 'name') return 'Catalogue of Life has a different name here. Keep yours unless you are sure.'
  return ''
}

export const groupChoiceBody = (planId, group, choice) => ({ action: 'names', plan_id: planId, group_choice: { group: group.id, choice } })
export const selectedGroupChoice = group => group?.choice || (group?.kind === 'auto' ? 'col' : group?.kind === 'uncertain' ? 'stem' : '')
export const ariaPressed = (selected, choice) => selected === choice

export const optionNote = option => {
  if (!option) return ''
  const counts = []
  const add = (count, singular, plural, prefix = '') => {
    if (count) counts.push(`${count.toLocaleString()} ${prefix}${count === 1 ? singular : plural}`)
  }
  add(option.broader || 0, 'would become a broader group', 'would become a broader group', 'of these ')
  add(option.different || 0, 'would change name', 'would change name')
  add(option.spelling || 0, "would get COL's spelling", "would get COL's spelling")
  add(option.kept || 0, 'has no COL name and keeps yours', 'have no COL name and keep yours')
  add(option.authorship || 0, 'would replace your authorship', 'would replace your authorship')
  return counts.join(' · ')
}

export const classificationNotice = summary => {
  const notice = summary?.classification_notice
  if (!notice?.names) return ''
  const example = notice.examples?.[0]
  if (!example) return notice.mixed
    ? `Your file uses two sets of higher-group names for ${notice.names.toLocaleString()} names.`
    : `Your file uses other higher-group names than Catalogue of Life for ${notice.names.toLocaleString()} names.`
  const prefix = notice.mixed ? 'Your file uses two sets of higher-group names' : 'Your file uses other higher-group names than Catalogue of Life'
  return `${prefix} for ${notice.names.toLocaleString()} names (e.g. ${example.yours} where COL has ${example.col}). Only names are published, so this changes nothing.`
}

export const groupOptions = group => (group?.options || []).map(option => ({ ...option, decision: option.decision, eligible: option.eligible || 0 }))
export const progress = (summary = {}) => {
  const groups = summary.groups || []
  const auto = groups.reduce((sum, group) => sum + (group.auto || 0), 0)
  const need = groups.reduce((sum, group) => sum + (group.undecided || 0), 0)
  const unchecked = summary.unchecked || 0
  const decided = summary.decided || 0
  const labels = summary.labels || 0
  return { auto, need, unchecked, decided, labels, percent: labels ? Math.min(100, Math.round((decided / labels) * 100)) : 0,
    text: `${auto.toLocaleString()} accepted automatically · ${need.toLocaleString()} need you${unchecked ? ` · ${unchecked.toLocaleString()} still being checked` : ''}` }
}

export const rowStatus = entry => {
  const decision = entry?.decision
  if (!decision) return { kind: null, text: '' }
  if (entry.decision_unconfirmed || entry.decision_held) return { kind: 'held', text: 'Your text as written (until you confirm)' }
  if (decision.by === 'user') return { kind: 'user', text: 'Changed by you' }
  if (decision.by?.startsWith('bulk:')) return { kind: 'bulk', text: 'Applied to the group' }
  if (decision.by?.startsWith('auto:')) return { kind: 'auto', text: 'Accepted automatically' }
  return { kind: null, text: '' }
}

export const reasonText = entry => entry?.reasons?.[0]?.text || ''
export const decisionBody = (planId, label, kind, usageId, { confirmCoarser = false } = {}) => ({ action: 'names', plan_id: planId,
  name_decisions: { [label]: kind ? { decision: kind, ...(usageId ? { usage_id: usageId } : {}), ...(confirmCoarser ? { confirm_coarser: true } : {}) } : null } })
export const groupQuery = ({ group, offset = 0, limit = PAGE_SIZE, q = '' } = {}) => {
  const params = new URLSearchParams({ names_view: 'group', names_group: group || '', names_offset: String(offset), names_limit: String(limit) })
  if (q) params.set('names_q', q)
  return params.toString()
}
export const pageCount = (total, limit = PAGE_SIZE) => Math.max(1, Math.ceil((total || 0) / limit))
export const isEditable = state => ['review', 'reviewing'].includes(state?.status)
export const isChecking = nameReview => Boolean(nameReview?.checking) || nameReview?.status === 'running'

export const checkMessage = nameReview => {
  if (!nameReview) return null
  const { status, error, summary = {} } = nameReview
  const checked = `${(summary.checked || 0).toLocaleString()} of ${(summary.labels || 0).toLocaleString()} names checked`
  if (isChecking(nameReview)) return { variant: 'info', text: `Checking names against Catalogue of Life… ${checked}.`, spinner: true }
  if (status === 'error') return { variant: 'warning', text: `${error || 'Name checks stopped.'} ${checked}. Conversion does not depend on them.` }
  if (status === 'incomplete' || status === 'pending') return { variant: 'warning', text: `${checked}. You can convert now, or check again to continue.` }
  return null
}

export const carriedMessage = carried => {
  const kept = carried?.decisions || 0
  const dropped = carried?.dropped || 0
  if (!kept && !dropped) return null
  const keptText = kept ? `${kept.toLocaleString()} earlier name ${kept === 1 ? 'decision was' : 'decisions were'} kept from your previous check.` : ''
  const droppedText = dropped ? `${dropped.toLocaleString()} earlier ${dropped === 1 ? 'name decision could' : 'name decisions could'} not be kept because the names in your data changed.` : ''
  return [keptText, droppedText].filter(Boolean).join(' ')
}
export const unconfirmedMessage = summary => {
  const count = summary?.unconfirmed || 0
  return count ? `${count.toLocaleString()} held ${count === 1 ? 'decision is' : 'decisions are'} kept as your own name until confirmed.` : null
}
export const skippedMessage = summary => {
  const skipped = summary?.skipped_long
  if (!skipped?.labels) return null
  const names = skipped.labels === 1 ? '1 name is' : `${skipped.labels.toLocaleString()} names are`
  const rows = skipped.rows === 1 ? '1 row' : `${skipped.rows.toLocaleString()} rows`
  return `${names} longer than ${(summary.max_label_chars || 500).toLocaleString()} characters (${rows}). They are not checked and are converted as they are.`
}
