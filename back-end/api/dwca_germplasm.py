"""Pure helpers for the four germplasm extensions (Accession, Score, Trait, Trial).

Audited against registry XMLs ae90e94b2293-GermplasmAccession.xml, 2dadad759a37-MeasurementScore.xml,
e3c2cb4ff61a-MeasurementTrait.xml and 5014798f62ff-MeasurementTrial.xml and DwC-DP schema revision
76898192fd298c2aa170a7059e1bdadf3ee2a828. No network calls, no Django state. Every target is an explicit
alias: none of these source IRIs equals the pinned field IRI except dwc:locationID, whose meaning still
needs review. Trial terms are registered as measurementTrail* (sic); Score uses measurementTrial*.
"""
from __future__ import annotations

import re
import math

from api.dwca_import import DWC, ImportFailure

G = "http://purl.org/germplasm/germplasmTerm#"
GTYPE = "http://purl.org/germplasm/germplasmType#"
GEO = "http://www.w3.org/2003/01/geo/wgs84_pos#"
ACCESSION_ROW_TYPE = G + "GermplasmAccession"
SCORE_ROW_TYPE = G + "MeasurementScore"
TRAIT_ROW_TYPE = G + "MeasurementTrait"
TRIAL_ROW_TYPE = G + "MeasurementTrial"
GERMPLASM_FAMILIES = {
    ACCESSION_ROW_TYPE: "germplasm-accession",
    SCORE_ROW_TYPE: "germplasm-score",
    TRAIT_ROW_TYPE: "germplasm-trait",
    TRIAL_ROW_TYPE: "germplasm-trial",
}
SUBJECT_TABLES = {
    "germplasm-accession": ("material",),
    "germplasm-score": ("material", "occurrence", "event"),
    "germplasm-trait": ("protocol",),
    "germplasm-trial": ("event",),
}
_FK = {"material": "materialEntity_fk", "occurrence": "occurrence_fk", "event": "event_fk"}

# Audited passport statements. Each nonempty approved value becomes one material-assertion keyed by the
# exact source IRI. germplasmID, collectingInstituteID, locationID and geo:* are deliberately absent.
ACCESSION_STATEMENT_TERMS = tuple(G + name for name in (
    "germplasmIdentifier", "biologicalStatus", "breedingID", "breedingIdentifier", "breedingYear",
    "breedingCountry", "breedingCountryCode", "breedingInstituteID", "breedingInstitute", "breedingPerson",
    "ancestralData", "purdyPedigree", "breedingRemarks", "acquisitionID", "donorsID", "donorsIdentifier",
    "donorInstituteID", "donorInstitute", "acquisitionDate", "acquisitionSource", "acquisitionRemarks",
    "safetyDuplicationID", "safetyDuplicationDate", "safetyDuplicationInstituteID", "safetyDuplicationInstitute",
    "safetyDuplicationRemarks", "treatyOrRegulationID", "treatyOrRegulationName",
    "treatyOrRegulationGoverningBody", "mlsStatus")) + (GTYPE + "storageCondition",)

# Each passport value becomes one material-assertion on the approved material, with assertionTypeIRI = the exact
# source term IRI and the value verbatim (the term is a property, not a vetted measurement type). Pedigrees, donors,
# acquisitions and safety duplicates create no materials, agents, events or relationships.
_STATEMENT_REASON = ("Each value is saved exactly as written as a detail of the specimen record, labelled with this "
                     "column's name. Pedigrees, donors and duplicates stay as text: they do not become separate "
                     "specimens, people or events.")
# The existing MoF pairing (measurement* to assertion*), not an IRI match. The planning table is
# occurrence-assertion; rows are written to the explicitly approved material, occurrence or event.
_MOF_REASON = ("This is the usual place for this measurement column. Whether the measurements describe the occurrence, "
               "its event or its specimen follows your answer about what the rows of this table describe.")
# Trial rows describe the attached Event core only: values patch empty or equal event fields, conflicts are
# rejected and no event is created.
_TRIAL_REASON = ("Trial details are added to the linked event where it has no value yet. If the event already has a "
                 "different value, the conversion stops rather than overwrite it.")
# Trait Descriptor rows are dataset-level method definitions: protocols with no occurrence, event or material link.
_TRAIT_SCOPE = " Method descriptions belong to the whole dataset; they are not attached to particular records."

_TARGETS = {
    ACCESSION_ROW_TYPE: {
        # An accession identifier, not skos:notation by IRI.
        G + "germplasmID": ("material-identifier.identifier",
                            "germplasmID is usually the accession number of the specimen. Confirm that it identifies the "
                            "specimen on each row; a link to a GBIF occurrence page would identify an occurrence instead."),
    },
    SCORE_ROW_TYPE: {DWC + source: ("occurrence-assertion." + target, _MOF_REASON) for source, target in {
        "measurementID": "assertionID", "measurementType": "verbatimAssertionType", "measurementValue": "assertionValue",
        "measurementUnit": "assertionUnit", "measurementAccuracy": "assertionError",
        "measurementDeterminedDate": "assertionMadeDate", "measurementDeterminedBy": "assertionBy",
        "measurementMethod": "assertionProtocols", "measurementRemarks": "assertionRemarks",
    }.items()},
    TRAIT_ROW_TYPE: {term: ("protocol." + field, reason + _TRAIT_SCOPE) for term, (field, reason) in {
        G + "measurementTraitID": ("protocolID", "The trait's identifier, kept as the identifier of its method description."),
        G + "measurementTraitName": ("protocolName", "The trait's name, kept as the name of its method description."),
        G + "measurementTraitSource": ("protocolReferences", "Where the trait definition comes from, such as a publication, "
                                                             "kept as the sources of its method description."),
        G + "measurementTraitRemarks": ("protocolRemarks", "Notes about the trait, kept as remarks on its method description."),
        DWC + "measurementMethod": ("protocolDescription", "How the trait is measured, kept as its method description."),
    }.items()},
    TRIAL_ROW_TYPE: {term: (target, _TRIAL_REASON) for term, target in {
        G + "measurementTrailID": "event-identifier.identifier",
        G + "measurementTrailIdentifier": "event.fieldNumber",
        G + "measurementTrailYear": "event.year",
        G + "measurementTrailRemarks": "event.eventRemarks",
        G + "measurementTrailReport": "bibliographic-resource.bibliographicCitation",
        DWC + "locationID": "event.locationID",
        GEO + "location": "event.locality",
    }.items()},
}

GERMPLASM_DERIVED_TERMS = {
    **{(ACCESSION_ROW_TYPE, term): _STATEMENT_REASON for term in ACCESSION_STATEMENT_TERMS},
    # Fills verbatimAssertionType only where dwc:measurementType is empty; a differing measurementType is rejected.
    (SCORE_ROW_TYPE, G + "measurementTraitName"): (
        "The trait name is used as the measurement type on rows that have no measurementType. If a row has a different "
        "measurementType, the conversion stops rather than choose one."),
    # W3C geo terms: lat and lon patch decimalLatitude/decimalLongitude only as a pair, and no datum is inferred.
    (TRIAL_ROW_TYPE, GEO + "lat"): ("Latitude of the trial site. It is added to the event only together with the "
                                    "longitude; ChatIPT does not guess the coordinate system (datum)."),
    (TRIAL_ROW_TYPE, GEO + "lon"): ("Longitude of the trial site. It is added to the event only together with the "
                                    "latitude; ChatIPT does not guess the coordinate system (datum)."),
    (TRIAL_ROW_TYPE, GEO + "alt"): "Altitude of the trial site, saved as both the minimum and maximum elevation of the event.",
}

# Columns kept in originals with an explanation for the reviewer.
_PRESERVE_REASONS = {
    (ACCESSION_ROW_TYPE, DWC + "locationID"): ("The site where the original material was collected. It is not copied "
                                               "to an event, so it is left out of the Data Package."),
    # Used by root as the material subject check only; ambiguous as an identifier.
    (SCORE_ROW_TYPE, G + "germplasmID"): ("Used only to check that each measurement belongs to the right specimen; "
                                          "it is not saved as an identifier."),
    # May be a trait ontology IRI or a Trait Descriptor key; no protocol is created from Score.
    (SCORE_ROW_TYPE, G + "measurementTraitID"): ("May refer to a row of your trait table or to a trait in an outside "
                                                "vocabulary. Linking measurements to their trait definitions is a "
                                                "separate question; the column is not saved on its own."),
    (SCORE_ROW_TYPE, G + "measurementByInstituteID"): ("An institute code. ChatIPT does not turn it into an organization "
                                                      "record, so it is left out of the Data Package."),
}


def _allowed():
    allowed = {}
    for row_type, targets in _TARGETS.items():
        for target, _ in targets.values():
            table, field = target.split(".", 1)
            allowed.setdefault(GERMPLASM_FAMILIES[row_type], {}).setdefault(table, set()).add(field)
    return allowed


_FIELDS = _allowed()
_YEAR = re.compile(r"-?\d{1,4}")
_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")


def germplasm_targets(row_type, term, values):
    """Return (targets, review_reason) for one source column; exact registered IRIs only."""
    derived = GERMPLASM_DERIVED_TERMS.get((row_type, term))
    if derived:
        return [], derived
    target = _TARGETS.get(row_type, {}).get(term)
    if not target:
        return [], _PRESERVE_REASONS.get((row_type, term))
    if term == G + "germplasmID" and any("data.gbif.org/occurrences" in value for value in values):
        return [], ("The values are links to GBIF occurrence pages, which identify occurrences rather than this specimen, "
                    "so they are left out of the Data Package.")
    return [target[0]], target[1]


def _filled(value):
    return isinstance(value, str) and value.strip() != ""


def _values(family, mapped, subject_table):
    if not isinstance(mapped, dict):
        raise ImportFailure("Mapped extension values must be a mapping of target tables to fields.")
    allowed = _FIELDS.get(family, {})
    collected = {}
    for table, fields in mapped.items():
        neutral = table
        if family == "germplasm-score" and table == f"{subject_table}-assertion":
            neutral = "occurrence-assertion"
        if not isinstance(fields, dict):
            raise ImportFailure(f"Mapped values for {table} must be a field mapping.")
        for field, value in fields.items():
            if field not in allowed.get(neutral, set()):
                raise ImportFailure(f"{table}.{field} is not an audited {family} target for a {subject_table} subject.")
            value = "" if value is None else value
            if not isinstance(value, str):
                raise ImportFailure(f"{table}.{field} must be text.")
            if collected.setdefault(neutral, {}).setdefault(field, value) != value:
                raise ImportFailure(f"Two columns give different values for {field} in one row.")
    return {table: {field: value for field, value in fields.items() if _filled(value)} for table, fields in collected.items()}


def _derived(row_type, source):
    if not isinstance(source, dict):
        raise ImportFailure("Source values must be a mapping of term IRIs to text.")
    values = {}
    for term, value in source.items():
        if (row_type, term) not in GERMPLASM_DERIVED_TERMS:
            continue
        if value is not None and not isinstance(value, str):
            raise ImportFailure(f"Source value for {term} must be text.")
        if _filled(value):
            values[term] = value
    return values


def _accession(source, values, subject_key):
    rows = []
    identifier = values.get("material-identifier", {}).get("identifier")
    if identifier:
        rows.append(("material-identifier", {"materialEntity_fk": subject_key, "identifier": identifier}))
    statements = _derived(ACCESSION_ROW_TYPE, source)
    # Registered order, one row per term; source multiplicity is kept by root (one call per source row).
    rows += [("material-assertion", {"materialEntity_fk": subject_key, "assertionTypeIRI": term, "assertionValue": statements[term]})
             for term in ACCESSION_STATEMENT_TERMS if term in statements]
    return rows


def _score(source, values, subject_table, subject_key):
    record = dict(values.get("occurrence-assertion", {}))
    name = _derived(SCORE_ROW_TYPE, source).get(G + "measurementTraitName")
    if name:
        if record.get("verbatimAssertionType", name) != name:
            raise ImportFailure("measurementType and measurementTraitName disagree in one measurement row. Leave one of them out of the Data Package.")
        record["verbatimAssertionType"] = name
    if not record.get("assertionValue") or not record.get("verbatimAssertionType"):
        raise ImportFailure("A measurement row needs a value and a measurement type to be converted.")
    return [(f"{subject_table}-assertion", {_FK[subject_table]: subject_key, **record})]


def _trait(values, subject_key):
    description = values.get("protocol", {})
    if not {"protocolName", "protocolDescription", "protocolReferences", "protocolRemarks"} & set(description):
        raise ImportFailure("A trait row needs a name, method, source or remarks to become a method description.")
    return [("protocol", {"protocol_pk": subject_key, **description})]


def _number(term, value, low, high):
    if not _NUMBER.fullmatch(value) or not math.isfinite(float(value)) or not low <= float(value) <= high:
        raise ImportFailure(f"{term} value {value!r} is not a number between {low} and {high}.")
    return value


def _trial(source, values, subject_key, record_key):
    patch = dict(values.get("event", {}))
    if "year" in patch and not _YEAR.fullmatch(patch["year"]):
        raise ImportFailure(f"measurementTrailYear {patch['year']!r} is not a year.")
    geo = _derived(TRIAL_ROW_TYPE, source)
    if (GEO + "lat" in geo) != (GEO + "lon" in geo):
        raise ImportFailure("Trial coordinates need both a latitude (geo:lat) and a longitude (geo:lon).")
    if GEO + "lat" in geo:
        patch["decimalLatitude"] = _number("geo:lat", geo[GEO + "lat"], -90, 90)
        patch["decimalLongitude"] = _number("geo:lon", geo[GEO + "lon"], -180, 180)
    if GEO + "alt" in geo:
        patch["minimumElevationInMeters"] = patch["maximumElevationInMeters"] = _number("geo:alt", geo[GEO + "alt"], float('-inf'), float('inf'))
    rows = [("event", {"event_pk": subject_key, **patch})] if patch else []
    identifier = values.get("event-identifier", {}).get("identifier")
    if identifier:
        rows.append(("event-identifier", {"event_fk": subject_key, "identifier": identifier}))
    citation = values.get("bibliographic-resource", {}).get("bibliographicCitation")
    if citation:
        if not _filled(record_key):
            raise ImportFailure("A trial report requires a deterministic record key.")
        # relationshipType is never inferred; the report is not deduplicated across rows.
        rows += [("bibliographic-resource", {"reference_pk": record_key, "bibliographicCitation": citation}),
                 ("event-reference", {"reference_fk": record_key, "event_fk": subject_key})]
    return rows


def emit_germplasm_records(family, source, mapped, subject_table, subject_key, record_key):
    if family not in SUBJECT_TABLES:
        raise ImportFailure(f"Unsupported germplasm family: {family!r}.")
    if subject_table not in SUBJECT_TABLES[family]:
        raise ImportFailure(f"{family} rows cannot describe a {subject_table!r} subject.")
    if not _filled(subject_key):
        raise ImportFailure(f"A {family} row does not resolve to an approved {subject_table}.")
    values = _values(family, mapped, subject_table)
    if family == "germplasm-accession":
        rows = _accession(source, values, subject_key)
    elif family == "germplasm-score":
        rows = _score(source, values, subject_table, subject_key)
    elif family == "germplasm-trait":
        rows = _trait(values, subject_key)
    else:
        rows = _trial(source, values, subject_key, record_key)
    if not rows:
        raise ImportFailure("A row of this table has no value that can be converted. Leave the table out of the Data Package instead.")
    return rows
