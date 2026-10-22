// What the two scientific-name reviews (the chat's taxon review and the conversion's name check) share: the choices
// offered for each name, their wording, and how a decision and what it writes are shown.

export const KEEP_LABEL = 'Keep original'
export const KEEP_TITLE = 'Publish the name as it is in your data'
export const CORRECTION_BUTTON = 'Type a correction'
export const CORRECTION_TITLE = 'Publish a name you type instead'
export const CORRECTION_HELP = 'Published as scientificName exactly as you type it. Authorship and rank stay as in your data, '
  + 'and your original text stays in verbatimIdentification.'
export const MAX_CORRECTED_NAME_CHARS = 200 // api.taxon_matching.MAX_CORRECTED_NAME_CHARS
export const EMPTY_LABEL = 'Don’t publish a name'
export const EMPTY_TITLE = 'Leave scientificName, its authorship and rank empty; your text stays in verbatimIdentification'
export const SEARCH_LABEL = 'Search Catalogue of Life…'

export const formatName = (usage) => {
  if (!usage?.scientificName) return ''
  return [usage.scientificName, usage.scientificNameAuthorship].filter(Boolean).join(' ')
}

const CONTEXT_RANKS = ['kingdom', 'phylum', 'class']

export const classificationContext = usage => CONTEXT_RANKS.map(rank => usage?.classification?.[rank]).filter(Boolean).join(' › ')

export const choiceLabel = choice => {
  const usage = choice?.usage
  if (!usage) return ''
  return [formatName(usage), usage.taxonRank, classificationContext(usage)].filter(Boolean).join(' · ')
}

export const needsConfirmation = choice => Boolean(choice?.replaces || choice?.authorship_differs || choice?.rank_change)

// Why a COL name needs a second click: it replaces the user's name, authorship or rank.
export const replacementWarning = (choice, rows) => {
  if (!needsConfirmation(choice)) return ''
  const count = rows ? ` on ${rows.toLocaleString()} ${rows === 1 ? 'row' : 'rows'}` : ''
  if (!choice.replaces && choice.rank_change) return `“${choice.usage.scientificName}” ${choice.rank_change}${count}. It may be a different taxon with the same name.`
  if (!choice.replaces) return `Catalogue of Life writes the authorship of “${choice.usage.scientificName}” as “${choice.usage.scientificNameAuthorship}”, which is not the authorship in your data; it would replace yours${count}. It may be a different taxon with the same name.`
  return `“${choice.usage.scientificName}” ${choice.replaces.text}${count}. Your text stays in verbatimIdentification.`
}

// The decided name in one line; kind is the server's written_fields kind (keep, parsed, corrected, empty or a COL kind).
export const decisionSummary = (kind, decided = {}) => {
  if (!kind) return ''
  if (kind === 'empty') return 'No name published'
  if (kind === 'keep') return 'Your text as written'
  return `${formatName(decided)}${decided.taxonRank ? ` (${decided.taxonRank})` : ''}`
}

// One column of a decision's preview (api.taxon_matching.preview_items).
export const previewPart = ({ field, how, value }) => {
  if (how === 'set') return `${field} “${value}”`
  if (how === 'empty') return `${field} empty`
  return value ? `${field} as in your data, else “${value}”` : `${field} as in your data`
}

export const previewText = items => (items || []).map(previewPart).join(' · ')
