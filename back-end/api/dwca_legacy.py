"""Pure helpers for the sandbox BMDE and NBN eXchange Format extensions.

Audited against sources/extension/7977dd7db803-bmde_2020_10_19.xml, f12e834ca1b0-NBNeXchangeFormat.xml
(the only registry versions of these row types) and DwC-DP schema revision 76898192fd298c2aa170a7059e1bdadf3ee2a828.
No term IRI of either family equals a target field IRI, so every target is a reviewed alias. Terms are matched by
exact registered IRI only. No network calls, no Django state. Events, occurrences, surveys and protocols are never
created here: event values are patches of an already emitted event, and assertions need an approved occurrence.
"""
from __future__ import annotations

import calendar
import re
from datetime import date
from decimal import Decimal

from api.dwca_import import ImportFailure

DWC = "http://rs.tdwg.org/dwc/terms/"
BMDE = "http://www.birdscanada.org/bmde/"
NXF = "http://rs.nbn.org.uk/dwc/nxf/0.1/terms/"
BMDE_ROW_TYPE = BMDE + "Observation"
NBN_ROW_TYPE = NXF + "nxfOccurrence"
LEGACY_FAMILIES = {BMDE_ROW_TYPE: "bmde", NBN_ROW_TYPE: "nbn"}
SUBJECT_TABLES = {"bmde": ("occurrence", "event"), "nbn": ("event",)}

# BMDE's twelve unpivoted MoF groups, field pairing as the runtime MeasurementOrFact rule.
GROUP_FIELDS = {"MeasurementType": "verbatimAssertionType", "MeasurementValue": "assertionValue",
                "MeasurementUnit": "assertionUnit", "MeasurementAccuracy": "assertionError",
                "MeasurementDeterminedBy": "assertionBy", "MeasurementMethod": "assertionProtocols"}
GROUPS = [{BMDE + f"{name}{n}": field for name, field in GROUP_FIELDS.items()} for n in range(1, 13)]
UTM = (BMDE + "UTMZone", BMDE + "UTMEasting", BMDE + "UTMNorthing")
TIMES = (BMDE + "TimeObservationsStarted", BMDE + "TimeObservationsEnded")
NBN_DATE = (NXF + "eventDateTypeCode", NXF + "eventDateStart", NXF + "eventDateEnd")
# Vague-date codes whose start/end alignment is checked here. Other codes are withheld, never extrapolated.
DATE_CODES = {"D", "DD", "O", "OO", "Y", "YY"}

# Each group becomes its own occurrence-assertion on an approved Occurrence subject, never merged with other groups.
# bmde: terms are documented MoF equivalents, not exact IRIs.
_GROUP_REASON = ("Measurement {n} (its type, value, unit and so on) becomes one measurement of the occurrence, kept "
                 "separate from the other measurements. Convert all of its columns together, or none.")
LEGACY_DERIVED_TERMS = {
    **{(BMDE_ROW_TYPE, term): _GROUP_REASON.format(n=n) for n, group in enumerate(GROUPS, 1) for term in group},
    **{(BMDE_ROW_TYPE, term): "The UTM zone, easting and northing are combined, as written, into the coordinates of the "
       "event, with the coordinate system UTM. Convert all three together; ChatIPT does not calculate decimal coordinates "
       "from them." for term in UTM},
    **{(BMDE_ROW_TYPE, term): "The start and end times, in decimal hours, become the time of the event (hh:mm, or "
       "start/end), without a time zone. Convert both columns together." for term in TIMES},
    **{(NBN_ROW_TYPE, term): "NBN vague dates become the event date only for the codes D, DD, O, OO, Y and YY, when the "
       "start and end dates are valid and match the code. Dates with other codes are not converted. Convert all three "
       "columns together; if the event already has a different eventDate, the conversion stops." for term in NBN_DATE},
}
_TARGETS = {
    BMDE_ROW_TYPE: {
        **{term: ["occurrence-assertion." + field] for group in GROUPS for term, field in group.items()},
        UTM[0]: ["event.verbatimCoordinates", "event.verbatimCoordinateSystem"],
        UTM[1]: ["event.verbatimCoordinates"], UTM[2]: ["event.verbatimCoordinates"],
        TIMES[0]: ["event.eventTime"], TIMES[1]: ["event.eventTime"],
        BMDE + "SurveyAreaIdentifier": ["event.siteNumber"],
        BMDE + "CoordinatesScope": ["event.georeferenceRemarks"],
    },
    NBN_ROW_TYPE: {
        **{term: ["event.eventDate"] for term in NBN_DATE},
        NXF + "gridReference": ["event.verbatimCoordinates"],
        NXF + "gridReferenceType": ["event.verbatimCoordinateSystem"],
        NXF + "siteFeatureKey": ["event.locationID"],
    },
}
ALIAS_REASONS = {
    (BMDE_ROW_TYPE, BMDE + "SurveyAreaIdentifier"): ("Saved as the site number of the linked event. This is the closest match, "
                                                     "not an exact one, so confirm it names the site of the event."),
    (BMDE_ROW_TYPE, BMDE + "CoordinatesScope"): ("The coordinates scope (such as route start or county centroid) changes what the "
                                                 "event's coordinates mean, so it is kept as a note on how the location was recorded."),
    (NBN_ROW_TYPE, NXF + "gridReference"): ("The grid reference is copied as written into the coordinates of the event. Its "
                                            "precision is not treated as a coordinate uncertainty."),
    (NBN_ROW_TYPE, NXF + "gridReferenceType"): ("The grid system (BNG, ING or UTM) is copied as written for the event, and needs "
                                                "a grid reference in the same row."),
    (NBN_ROW_TYPE, NXF + "siteFeatureKey"): ("An NBN Gateway site key, saved as the locationID of the event. Confirm that it "
                                             "identifies the location of the event."),
}
_PRESERVE = [
    (BMDE_ROW_TYPE, {DWC + "individualCount", BMDE + "ObservationDescriptor"}, "What the count means depends on ObservationDescriptor (for 'Presence/Absence', 1 means present), so the count is left out of the Data Package."),
    (BMDE_ROW_TYPE, {BMDE + f"MultiScientificName{n}" for n in range(1, 7)} | {BMDE + "TaxonomicAuthorityVersion", BMDE + "TaxonomicAuthorityYear"}, "Several names on one record do not say which identification is right, so they are left out of the Data Package."),
    (BMDE_ROW_TYPE, {BMDE + "Specimen" + name for name in ("DecimalLatitude", "DecimalLongitude", "GeodeticDatum", "UTMZone", "UTMNorthing", "UTMEasting")} | {BMDE + "CoordinatesUncertaintyInDecimalDegrees"}, "Coordinates of the specimen itself have no place in this conversion, so they are left out of the Data Package."),
    (BMDE_ROW_TYPE, {BMDE + name for name in ("SurveyAreaSize", "SurveyAreaPercentageCovered", "SurveyAreaShape", "SurveyAreaLongAxisLength", "SurveyAreaShortAxisLength", "SurveyAreaLongAxisOrientation", "SamplingEventStructure", "RouteIdentifier", "ProtocolSpeciesTargeted", "AllIndividualsReported", "AllSpeciesReported")}, "The survey area and completeness need a survey or parent event, which ChatIPT does not create for this table, so they are left out of the Data Package."),
    (BMDE_ROW_TYPE, {BMDE + name for name in ("RecordPermissions", "LastModifiedAction", "NoObservations", "RecordReviewStatus")}, "Record status (permissions, deletions, review state) is checked row by row; it is never turned into licences, absences or verification values."),
    (NBN_ROW_TYPE, {NXF + "gridReferencePrecision"}, "Grid square size is not a coordinate uncertainty, so it is left out of the Data Package."),
    (NBN_ROW_TYPE, {NXF + "sensitiveOccurrence"}, "Sensitive records are flagged row by row; ChatIPT does not write statements about withheld or generalised data for them."),
]
_EVENT_FIELDS = {"bmde": {"siteNumber", "georeferenceRemarks"}, "nbn": {"verbatimCoordinates", "verbatimCoordinateSystem", "locationID"}}
_OCCURRENCE_TERMS = {term for group in GROUPS for term in group}


def _filled(value):
    return isinstance(value, str) and value.strip() != ""


def _hours(text):
    if not re.fullmatch(r"\d{1,2}(\.\d*)?|\.\d+", text.strip()):
        raise ImportFailure(f"{text!r} is not a time in decimal hours (such as 13.5 for 13:30).")
    minutes = Decimal(text.strip()) * 60
    if minutes != minutes.to_integral_value():
        raise ImportFailure(f"{text!r} is more precise than whole minutes, and ChatIPT does not round it.")
    if minutes >= 24 * 60:
        raise ImportFailure(f"{text!r} is not a time of day.")
    return int(minutes)


def legacy_targets(row_type, term, values):
    """Return targets and a review explanation for an entire source column."""
    targets = _TARGETS.get(row_type, {}).get(term)
    if targets is None:
        reason = next((text for kind, terms, text in _PRESERVE if kind == row_type and term in terms), None)
        return [], reason
    if term in TIMES:
        try:
            [_hours(value) for value in values]
        except ImportFailure:
            return [], "Some values are not times in decimal hours (such as 13.5 for 13:30), so the column is left out of the Data Package."
    reason = LEGACY_DERIVED_TERMS.get((row_type, term)) or ALIAS_REASONS[(row_type, term)]
    if term == NBN_DATE[0] and any(value not in DATE_CODES for value in values):
        reason += " Some rows use other codes; those dates are not converted."
    return list(targets), reason


def _date(text, term):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise ImportFailure(f"{term} {text!r} is not a date in the form YYYY-MM-DD.")
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ImportFailure(f"{term} {text!r} is not a valid date.") from None


def nbn_event_date(code, start, end):
    """Return the ISO eventDate for a supported vague date, None for codes left to review."""
    if not _filled(code):
        raise ImportFailure("Each NBN row needs an eventDateTypeCode.")
    if code not in DATE_CODES:
        return None
    if not (_filled(start) and _filled(end)):
        raise ImportFailure(f"Vague date code {code} needs both eventDateStart and eventDateEnd.")
    first, last = _date(start, "eventDateStart"), _date(end, "eventDateEnd")
    month_end = lambda day: day.day == calendar.monthrange(day.year, day.month)[1]
    valid = first <= last and {
        "D": first == last,
        "DD": True,
        "O": first.day == 1 and (first.year, first.month) == (last.year, last.month) and month_end(last),
        "OO": first.day == 1 and month_end(last),
        "Y": (first.month, first.day, last.month, last.day) == (1, 1, 12, 31) and first.year == last.year,
        "YY": (first.month, first.day, last.month, last.day) == (1, 1, 12, 31),
    }[code]
    if not valid:
        raise ImportFailure(f"eventDateStart {start} and eventDateEnd {end} do not match vague date code {code}.")
    return start if first == last else f"{start}/{end}"


def legacy_row_review(row_type, source):
    """Return why one source row needs review before publication, or None."""
    value = lambda term: (source.get(term) or "").strip()
    reasons = []
    if row_type == BMDE_ROW_TYPE:
        if value(BMDE + "RecordPermissions") not in {"", "5"}:
            reasons.append(f"RecordPermissions {value(BMDE + 'RecordPermissions')!r} limits who may see this record, so decide how to handle it before publishing")
        if value(BMDE + "LastModifiedAction").upper() == "DELETE":
            reasons.append("LastModifiedAction DELETE says this record should be removed")
        if value(BMDE + "NoObservations") == "NoObs":
            reasons.append("NoObservations says nothing was observed; ChatIPT does not turn that into an absence")
        if value(BMDE + "RecordReviewStatus").lower() in {"not accepted", "pending review"}:
            reasons.append(f"RecordReviewStatus is {value(BMDE + 'RecordReviewStatus')!r}")
        if value(DWC + "individualCount") and value(BMDE + "ObservationDescriptor").replace(" ", "").lower() == "presence/absence":
            reasons.append("individualCount here means present, not a number of individuals")
        for n, group in enumerate(GROUPS, 1):
            filled = {field for term, field in group.items() if value(term)}
            if filled and not {"verbatimAssertionType", "assertionValue"} <= filled:
                reasons.append(f"measurement {n} has no type or no value")
    elif row_type == NBN_ROW_TYPE:
        sensitive = value(NXF + "sensitiveOccurrence")
        if sensitive.lower() == "true":
            reasons.append("sensitiveOccurrence is true, so decide how to handle this sensitive record before publishing")
        elif sensitive.lower() != "false":
            reasons.append(f"sensitiveOccurrence {sensitive!r} is not true or false")
        try:
            if nbn_event_date(*(value(term) for term in NBN_DATE)) is None:
                reasons.append(f"dates with vague date code {value(NBN_DATE[0])!r} are not converted")
        except ImportFailure as error:
            reasons.append(str(error).rstrip("."))
        if value(NXF + "gridReferenceType") and not value(NXF + "gridReference"):
            reasons.append("gridReferenceType is given without a gridReference")
    return "; ".join(reasons) + "." if reasons else None


def _checked(family, source, mapped):
    if not isinstance(source, dict) or not isinstance(mapped, dict):
        raise ImportFailure("Legacy extension values must be mappings.")
    row_type = next(key for key, name in LEGACY_FAMILIES.items() if name == family)
    for term, value in source.items():
        if (row_type, term) not in LEGACY_DERIVED_TERMS:
            raise ImportFailure(f"{term} is not an approved derived {family} term.")
        if not isinstance(value, str):
            raise ImportFailure(f"{term} must be text.")
    event = {}
    for table, fields in mapped.items():
        if table != "event" or not isinstance(fields, dict):
            raise ImportFailure(f"{table} is not an audited {family} extension target.")
        for field, value in fields.items():
            if field not in _EVENT_FIELDS[family]:
                raise ImportFailure(f"{table}.{field} is not an audited {family} extension target.")
            if value is not None and not isinstance(value, str):
                raise ImportFailure(f"{table}.{field} must be text.")
            if _filled(value):
                event[field] = value
    return event


def _complete(source, terms, label):
    supplied = [term for term in terms if term in source]
    if supplied and len(supplied) != len(terms):
        raise ImportFailure(f"{label}: convert all of its columns together, or none.")
    return bool(supplied)


def emit_legacy_records(family, source, mapped, subject_table, subject_key, record_key):
    """Return assertion rows or one event patch for a single source row."""
    if family not in SUBJECT_TABLES:
        raise ImportFailure(f"Unsupported legacy family: {family!r}.")
    if subject_table not in SUBJECT_TABLES[family]:
        raise ImportFailure(f"{family} extension rows cannot describe a {subject_table} subject here.")
    if not _filled(subject_key):
        raise ImportFailure(f"A {family} extension row does not resolve to a converted {subject_table}.")
    event = _checked(family, source, mapped)
    occurrence_values = any(_filled(source.get(term)) for term in _OCCURRENCE_TERMS)
    if subject_table == "occurrence":
        if event or any(_filled(source.get(term)) for term in UTM + TIMES):
            raise ImportFailure("BMDE event values need an explicit Event-context choice, not an occurrence subject.")
        rows = []
        for n, group in enumerate(GROUPS, 1):
            if not _complete(source, list(group), f"BMDE measurement {n}"):
                continue
            record = {field: source[term] for term, field in group.items() if _filled(source[term])}
            if not record:
                continue
            if not {"verbatimAssertionType", "assertionValue"} <= record.keys():
                raise ImportFailure(f"BMDE measurement {n} needs both a type and a value.")
            rows.append(("occurrence-assertion", {"occurrence_fk": subject_key, **record}))
        return rows
    if occurrence_values:
        raise ImportFailure("BMDE measurements describe an occurrence, so they cannot be attached to an event.")
    if family == "bmde":
        if _complete(source, UTM, "BMDE UTM coordinates") and any(_filled(source[term]) for term in UTM):
            if not all(_filled(source[term]) for term in UTM):
                raise ImportFailure("BMDE UTM coordinates need a zone, an easting and a northing.")
            event.update(verbatimCoordinates=" ".join(source[term].strip() for term in UTM), verbatimCoordinateSystem="UTM")
        if _complete(source, TIMES, "BMDE observation times") and any(_filled(source[term]) for term in TIMES):
            if not _filled(source[TIMES[0]]):
                raise ImportFailure("TimeObservationsEnded needs TimeObservationsStarted.")
            times = [_hours(source[term]) for term in TIMES if _filled(source[term])]
            if len(times) == 2 and times[1] < times[0]:
                raise ImportFailure("TimeObservationsEnded is earlier than TimeObservationsStarted, so the time span is unclear.")
            clock = [f"{minutes // 60:02d}:{minutes % 60:02d}" for minutes in dict.fromkeys(times)]
            event["eventTime"] = "/".join(clock)
    else:
        if event.get("verbatimCoordinateSystem") and not event.get("verbatimCoordinates"):
            raise ImportFailure("gridReferenceType needs a gridReference in the same row.")
        if _complete(source, NBN_DATE, "NBN vague dates"):
            event_date = nbn_event_date(*(source[term] for term in NBN_DATE))
            if event_date:
                event["eventDate"] = event_date
    return [("event", {"event_pk": subject_key, **event})] if event else []
