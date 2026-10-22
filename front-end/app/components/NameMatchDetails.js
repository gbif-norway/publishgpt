import { formatName } from '../utils/nameReview.mjs'

export default function NameMatchDetails({ entry }) {
  const match = entry.match || {}
  const usage = match.usage
  const aids = entry.review_aids || {}
  return <div className="small mt-1">
    {entry.context_key && <div className="text-muted">{entry.context_key}</div>}
    <div className="text-muted">Catalogue of Life: {usage ? formatName(usage) : 'no suggestion'}{usage?.taxonRank ? ` · ${usage.taxonRank}` : ''}</div>
    {match.acceptedUsage && <div className="text-muted">Synonym; COL accepts {formatName(match.acceptedUsage)}</div>}
    {entry.preprocessed && <div className="text-muted">Interpreted as <em>{entry.query?.scientificName}</em>{entry.preprocessing_note && ` — ${entry.preprocessing_note}`}</div>}
    {[['GBIF Backbone', aids.gbifBackbone], ['Newer COL release', aids.checklistBankXR]]
      .filter(([, aid]) => aid && ['exact', 'variant'].includes(aid.status))
      .map(([source, aid]) => <div key={source} className="text-muted">{source}: {formatName(aid)} <span className="fst-italic">may not yet be reflected on GBIF.org</span></div>)}
  </div>
}
