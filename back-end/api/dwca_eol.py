"""Pure helpers for the EOL Media and EOL References extensions.

Audited against c34fa59ea7e7-media_extension.xml, 650d0e7712e0-reference_extension.xml and DwC-DP schema revision
76898192fd298c2aa170a7059e1bdadf3ee2a828 (docs/dwca-conversion/cloud-audits/remaining-fields.md). Only registered
term IRIs are planned; EOL-namespace terms are never treated as their Audubon/DwC namesakes. No network or Django state.
"""
from __future__ import annotations

from api.dwca_import import ImportFailure
from api.dwca_media import absolute_iri, media_targets

DCT = 'http://purl.org/dc/terms/'
AC = 'http://rs.tdwg.org/ac/terms/'
BIBO = 'http://purl.org/ontology/bibo/'
XMP = 'http://ns.adobe.com/xap/1.0/'
IPTC = 'http://iptc.org/std/Iptc4xmpExt/1.0/xmlns/'
EOL_MEDIA = 'http://eol.org/schema/media/Document'
EOL_REFERENCE = 'http://eol.org/schema/reference/Reference'
EOL_FAMILIES = {EOL_MEDIA: 'eol-media', EOL_REFERENCE: 'eol-reference'}
LEGACY_SUBTYPE = 'http://rs.tdwg.org/audubon_core/subtype'
SPM_INFO_ITEMS = 'http://rs.tdwg.org/ontology/voc/SPMInfoItems'
TEXT_TYPES = {'text', 'http://purl.org/dc/dcmitype/text'}
REFERENCE_SUBJECTS = {'occurrence': 'occurrence_fk', 'event': 'event_fk',
                      'material': 'materialEntity_fk', 'protocol': 'protocol_fk'}

# EOL media terms whose audited definitions agree with the shared Audubon/Simple Multimedia planner.
_SHARED_MEDIA_TERMS = {DCT + name for name in ('identifier', 'type', 'format', 'title', 'description', 'modified', 'rights',
                                              'bibliographicCitation', 'creator')} | {
    AC + 'accessURI', AC + 'furtherInformationURL', AC + 'derivedFrom', XMP + 'CreateDate', XMP + 'Rating',
    XMP + 'rights/UsageTerms', XMP + 'rights/Owner'}
_MIXED = 'This column mixes web links (IRIs) and text. Split it into two columns to convert it; until then it is left out of the Data Package.'
_MEDIA_PRESERVED = {
    'http://rs.tdwg.org/dwc/terms/taxonID': ('A taxonID means the item belongs on a species page, not to a particular occurrence. It is '
                                             'left out of the Data Package, and no identification or occurrence is made from it.'),
    # Adding a thumbnail as a second media resource would be a modelling decision.
    'http://eol.org/schema/media/thumbnailURL': 'A thumbnail would be a second media file, so it is left out of the Data Package.',
    'http://eol.org/schema/agent/agentID': ('These EOL agent identifiers point to records outside your archive and do not say what the '
                                            'person did, so no person record is made from them.'),
    # The pinned schema has no media-reference table; the value is never used as a relationship key.
    'http://eol.org/schema/reference/referenceID': 'The Data Package cannot link media to references, so this column is left out of the Data Package.',
}
_EXACT_REFERENCE = {DCT + 'title': 'title', BIBO + 'pages': 'pages', BIBO + 'volume': 'volume', BIBO + 'edition': 'edition'}
_FULL_REFERENCE_NOTE = (' EOL says a full citation replaces the separate citation parts (title, pages, volume, edition), so '
                        'decide whether those parts should still be copied when both are given.')
_REFERENCE_ALIASES = {
    # Source -> target: dcterms:identifier -> dwc:referenceID, publicationType -> dwc:referenceType, full_reference ->
    # dcterms:bibliographicCitation, bibo:authorList -> dc:creator, bibo:editorList -> bibo:editor (single property).
    DCT + 'identifier': ('referenceID', 'Saved as the identifier of the publication, which is what EOL means by it. Confirm '
                                        'this; a DOI or web link is never used in its place.'),
    'http://eol.org/schema/reference/publicationType': ('referenceType', 'Saved as the kind of publication. Confirm that this EOL column means that.'),
    'http://eol.org/schema/reference/full_reference': ('bibliographicCitation', 'Saved as the full citation. Confirm that this '
                                                                              'EOL column means that.' + _FULL_REFERENCE_NOTE),
    BIBO + 'authorList': ('author', 'Saved as the authors of the reference, copied as written, because ChatIPT cannot tell how the '
                                    'names are separated. Confirm this.'),
    BIBO + 'editorList': ('editor', 'Saved as the editors of the reference, copied as written. Confirm this.'),
}
_REFERENCE_PRESERVED = {
    DCT + 'created': 'The date a work was created is not its publication date, so it is left out of the Data Package.',
    BIBO + 'doi': ('The Data Package has no DOI field for references, and ChatIPT does not use a DOI as the identifier of the '
                   'reference, so it is left out.'),
    BIBO + 'uri': ('The Data Package has no web link field for references, and ChatIPT does not use a link as the identifier of '
                   'the reference, so it is left out.'),
    BIBO + 'pageStart': ('The Data Package has a single pages field, and ChatIPT does not combine first and last pages into it, '
                         'so this is left out of the Data Package.'),
    BIBO + 'pageEnd': ('The Data Package has a single pages field, and ChatIPT does not combine first and last pages into it, '
                       'so this is left out of the Data Package.'),
}
# Which registered source terms may supply each bibliographic-resource field.
_REFERENCE_SOURCES = {field: {term} for term, field in _EXACT_REFERENCE.items()}
_REFERENCE_SOURCES.update({field: {term} for term, (field, _) in _REFERENCE_ALIASES.items()})
_REFERENCE_SOURCES.update(publisher={DCT + 'publisher'}, publisherID={DCT + 'publisher'})


def _shape(values):
    return bool(values) and all(absolute_iri(v) for v in values), any(absolute_iri(v) for v in values)


def _split(values, literal, iri, alias_reason):
    all_iris, any_iris = _shape(values)
    if any_iris and not all_iris:
        return [], _MIXED
    return [iri if all_iris else literal], alias_reason


def _media_targets(term, values):
    if term in _SHARED_MEDIA_TERMS:
        return media_targets(term, values)
    if term == DCT + 'language':
        all_iris, any_iris = _shape(values)
        if all_iris:
            return ['media.languageIRI'], None
        if any_iris:
            return [], _MIXED
        return ['media.language'], 'EOL expects language codes such as en or nb. Confirm they should be saved as the language of the media.'
    if term == LEGACY_SUBTYPE:
        return _split(values, 'media.subtypeLiteral', 'media.subtypeIRI',
                      'This is the older Audubon Core subtype column. Confirm it should be saved as the media subtype.')
    if term == IPTC + 'CVterm':
        if _shape(values)[0]:
            return ['media.subjectCategoryIRI'], ('This IPTC subject term is the closest match for the subject category of the '
                                                  'media, but not an exact one. Confirm it.')
        return [], 'Subject terms written as text have no place in the Data Package, so they are left out.'
    return [], _MEDIA_PRESERVED.get(term)


def _reference_targets(term, values):
    if term in _EXACT_REFERENCE:
        return [f'bibliographic-resource.{_EXACT_REFERENCE[term]}'], None
    if term in _REFERENCE_ALIASES:
        field, reason = _REFERENCE_ALIASES[term]
        return [f'bibliographic-resource.{field}'], reason
    if term == DCT + 'publisher':
        return _split(values, 'bibliographic-resource.publisher', 'bibliographic-resource.publisherID',
                      "Saved as the publisher (or, for web links, the publisher's identifier). Confirm this; no organization "
                      'record is made from it.')
    return [], _REFERENCE_PRESERVED.get(term)


def eol_targets(row_type, term, values):
    """Return (targets, review_reason) for one whole source column of an EOL row type."""
    if row_type == EOL_MEDIA:
        return _media_targets(term, values)
    if row_type == EOL_REFERENCE:
        return _reference_targets(term, values)
    return [], None


def _filled(value):
    return isinstance(value, str) and value.strip() != ''


def eol_media_row_review(source):
    """Return a reason this media row cannot convert without an explicit row decision, or None."""
    reasons = []
    kind = (source.get(DCT + 'type') or '').strip().lower()
    if kind in TEXT_TYPES:
        reasons.append('This is a text account about a taxon, not a media file, so leave the row out of the Data Package.')
    for term, label in ((DCT + 'identifier', 'dcterms:identifier'), (DCT + 'type', 'dcterms:type'),
                        (XMP + 'rights/UsageTerms', 'xmpRights:UsageTerms')):
        if not _filled(source.get(term)):
            reasons.append(f'EOL requires {label}, but it is empty here; ChatIPT does not make up a licence or media type.')
    if _filled(source.get('http://rs.tdwg.org/dwc/terms/taxonID')) or (source.get(IPTC + 'CVterm') or '').strip().startswith(SPM_INFO_ITEMS):
        reasons.append('This item has a taxonID or a species-page subject, so it may show the species in general rather than '
                       'this occurrence or event. Confirm what it shows.')
    return ' '.join(reasons) or None


def _reference_values(source, mapped):
    if not isinstance(mapped, dict) or not isinstance(source, dict):
        raise ImportFailure('Source and mapped EOL reference values must be mappings.')
    values = {}
    for table, fields in mapped.items():
        if table != 'bibliographic-resource' or not isinstance(fields, dict):
            raise ImportFailure(f'{table} is not an audited EOL reference target table.')
        for field, value in fields.items():
            if field not in _REFERENCE_SOURCES:
                raise ImportFailure(f'bibliographic-resource.{field} is not an audited EOL reference target.')
            if value is None:
                value = ''
            if not isinstance(value, str):
                raise ImportFailure(f'bibliographic-resource.{field} must be text.')
            if not _filled(value):
                continue
            if value not in {source.get(term) for term in _REFERENCE_SOURCES[field]}:
                raise ImportFailure(f'bibliographic-resource.{field} does not equal its approved source value.')
            values[field] = value
    if 'publisher' in values and 'publisherID' in values:
        raise ImportFailure('One dcterms:publisher value cannot fill both publisher and publisherID.')
    return values


def emit_eol_records(family, source, mapped, subject_table, subject_key, record_key):
    if family == 'eol-media':
        raise ImportFailure('EOL media rows are emitted by the shared media path with an explicit subject choice.')
    if family != 'eol-reference':
        raise ImportFailure(f'Unsupported EOL family: {family!r}.')
    if subject_table not in REFERENCE_SUBJECTS:
        raise ImportFailure(f'An EOL reference cannot be linked to {subject_table!r}.')
    if not _filled(subject_key):
        raise ImportFailure(f'An EOL reference row does not resolve to a converted {subject_table}.')
    if not _filled(record_key):
        raise ImportFailure('An EOL reference row requires a deterministic record key.')
    values = _reference_values(source, mapped)
    if not _filled(source.get(DCT + 'identifier')):
        raise ImportFailure('Each EOL reference needs an identifier.')
    if not values:
        raise ImportFailure('An EOL reference row has no value that can be converted, so leave it out of the Data Package.')
    # One record per source row; supplied identifiers never become keys and relationshipType is never inferred.
    return [('bibliographic-resource', {'reference_pk': record_key, **values}),
            (f'{subject_table}-reference', {'reference_fk': record_key, REFERENCE_SUBJECTS[subject_table]: subject_key})]
