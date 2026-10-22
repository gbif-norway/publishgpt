export { unconfirmedMessage } from './nameReviewState.mjs'
// Conversion job messages; review policy and controls are shared.
export { DECISION_LABELS, GROUPS, PAGE_SIZE, choiceGroups, reviewChoices as conversionChoices, reviewDecision as conversionDecision, decisionResult, groupTitle, groupExplanation, groupChoiceBody, selectedGroupChoice, ariaPressed, optionNote, classificationNotice, groupOptions, progress, rowStatus, reasonText, decisionBody, groupQuery, pageCount } from './nameReviewState.mjs'

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
export const skippedMessage = summary => {
  const skipped = summary?.skipped_long
  if (!skipped?.labels) return null
  const names = skipped.labels === 1 ? '1 name is' : `${skipped.labels.toLocaleString()} names are`
  const rows = skipped.rows === 1 ? '1 row' : `${skipped.rows.toLocaleString()} rows`
  return `${names} longer than ${(summary.max_label_chars || 500).toLocaleString()} characters (${rows}). They are not checked and are converted as they are.`
}
