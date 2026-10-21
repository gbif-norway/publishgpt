"""Read archives without extracting paths or guessing semantic identifiers."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import stat
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from lxml import etree

from api.dwca_hierarchy import missing_reference

DWC = "http://rs.tdwg.org/dwc/terms/"
MAX_BYTES = 200 * 1024 * 1024
MAX_MEMBERS = 250
MAX_ROWS = 500_000
MAX_COLUMNS = 500
csv.field_size_limit(MAX_BYTES)
REGISTRY = json.loads((Path(__file__).parent / "templates/dwca-conversion/registry.json").read_text())


class ImportFailure(ValueError):
    pass


class ConversionError(ImportFailure):
    """A failure with a category, the decisions that can remedy it, and bounded evidence.

    Categories: stale-plan, decision, conflict, source, internal, transient. A plain
    ImportFailure is treated as a source failure.
    """

    def __init__(self, message, category='source', decision_ids=(), evidence=None):
        super().__init__(message)
        self.category = category
        self.decision_ids = list(dict.fromkeys(decision_ids))
        self.evidence = evidence or {}

    def as_conflict(self):
        return {'id': f"{self.category}:{hashlib.sha256(str(self).encode()).hexdigest()[:12]}", 'category': self.category,
                'reason': str(self), 'decision_ids': self.decision_ids, 'evidence': self.evidence}


def failure_category(error):
    return getattr(error, 'category', 'source')


@dataclass
class SourceTable:
    name: str
    row_type: str
    terms: list[str]
    rows: list[list[str]]
    ids: list[str]
    is_core: bool = False
    loose: bool = False
    row_sources: list[dict] = field(default_factory=list)
    join_basis: str = 'ID columns declared in meta.xml'
    unplaced_reason: str = ''


@dataclass
class SourceArchive:
    files: dict[str, bytes]
    tables: list[SourceTable]
    fingerprint: str
    has_meta: bool
    uploaded_files: dict[str, bytes]
    dropped_extension_rows: list[dict] = field(default_factory=list)
    tidy: dict | None = None  # Reviewable tidy-up changes for the archive view.


def safe_path(name):
    name = name.replace("\\", "/")
    path = PurePosixPath(name)
    if not name or path.is_absolute() or ".." in path.parts or ":" in name or "\x00" in name:
        raise ImportFailure(f"Unsafe input path: {name!r}.")
    return path.as_posix()


def read_inputs(inputs, *, drop_unlinked_extension_rows=False):
    """Inputs are (original filename, bytes), never storage-renamed filenames."""
    inputs = list(inputs)
    if not inputs or sum(len(content) for _, content in inputs) > MAX_BYTES:
        raise ImportFailure("Upload one archive or loose files totalling at most 200 MB.")
    zipped = [item for item in inputs if item[0].lower().endswith((".zip", ".dwca"))]
    files = {}
    if zipped:
        if len(inputs) != 1:
            raise ImportFailure("Upload one ZIP archive, or a set of loose files.")
        try:
            with zipfile.ZipFile(io.BytesIO(zipped[0][1])) as archive:
                members = [member for member in archive.infolist() if not member.is_dir()]
                if len(members) > MAX_MEMBERS or sum(m.file_size for m in members) > MAX_BYTES:
                    raise ImportFailure("The archive has more than 250 files, or is larger than 200 MB when unzipped.")
                for member in members:
                    if stat.S_ISLNK(member.external_attr >> 16) or member.flag_bits & 1:
                        raise ImportFailure("The ZIP contains links or encrypted files, which ChatIPT cannot read.")
                    if member.file_size > 1024 * 1024 and member.file_size / max(member.compress_size, 1) > 1000:
                        raise ImportFailure("A file in the ZIP expands to an unusually large size, so ChatIPT will not unzip it.")
                    name = safe_path(member.filename)
                    if name.casefold() in {key.casefold() for key in files}:
                        raise ImportFailure(f"Duplicate archive path: {name}.")
                    files[name] = archive.read(member)
        except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
            raise ImportFailure(f"ZIP cannot be read: {exc}.") from exc
    else:
        for name, content in inputs:
            name = safe_path(name)
            if name.casefold() in {key.casefold() for key in files}:
                raise ImportFailure(f"Duplicate filename: {name}.")
            files[name] = content
        if len(files) > MAX_MEMBERS:
            raise ImportFailure("Upload at most 250 files.")
    digest = hashlib.sha256()
    for name, content in sorted(files.items()):
        digest.update(name.encode()); digest.update(b"\0"); digest.update(hashlib.sha256(content).digest())
    meta = [name for name in files if PurePosixPath(name).name.lower() == "meta.xml"]
    if len(meta) > 1:
        raise ImportFailure("An upload must contain exactly one archive description (meta.xml).")
    tables = _manifest_tables(files, meta[0]) if meta else _loose_tables(files)
    if not tables or not any(table.is_core for table in tables):
        raise ImportFailure("No main table was found. Include meta.xml, or name the main table occurrence.csv, event.csv or taxon.csv.")
    core = next(table for table in tables if table.is_core)
    if not core.rows:
        raise ImportFailure("The main table has no data rows.")
    if not all(core.ids) or len(set(core.ids)) != len(core.ids):
        raise ImportFailure("Every row of the main table needs its own ID for linking the files (the id column in meta.xml), but some are empty or repeated.")
    keys = set(core.ids)
    unlinked = [(table, [index for index, value in enumerate(table.ids)
                         if value not in keys or missing_reference(value, keys)])
                for table in tables if not table.is_core and table.row_type and table.ids]
    unlinked = [(table, indexes) for table, indexes in unlinked if indexes]
    dropped_extension_rows = []
    if unlinked and not drop_unlinked_extension_rows:
        extensions = []
        for table, indexes in unlinked:
            records = []
            for index in indexes[:3]:
                source = table.row_sources[index] if index < len(table.row_sources) else {}
                values = [{'field': term.rsplit('/', 1)[-1], 'value': value[:240]}
                          for term, value in zip(table.terms, table.rows[index]) if value][:8]
                records.append({'file': source.get('file', table.name),
                                'data_record': source.get('data_record', index + 1),
                                'core_link': table.ids[index], 'values': values})
            extensions.append({'name': table.name, 'count': len(indexes), 'records': records})
        summary = '; '.join(f"{item['name']}: {item['count']} {('record' if item['count'] == 1 else 'records')}"
                            for item in extensions)
        total = sum(item['count'] for item in extensions)
        issue = ('record in an additional table is' if total == 1 else 'records in additional tables are')
        raise ConversionError(
            f"Unable to process this archive: {total} {issue} not linked to a row of the main table. The link is blank, "
            f"ambiguous or an ID that is not in the main table ({summary}).",
            category='source', evidence={'kind': 'unlinked-extension-records', 'tables': extensions})
    if unlinked:
        rejected = {id(table): set(indexes) for table, indexes in unlinked}
        filtered_tables = []
        for table in tables:
            indexes = rejected.get(id(table))
            if indexes:
                dropped_extension_rows.append({'name': table.name, 'rows': len(indexes)})
                table.rows = [row for index, row in enumerate(table.rows) if index not in indexes]
                table.ids = [value for index, value in enumerate(table.ids) if index not in indexes]
                table.row_sources = [value for index, value in enumerate(table.row_sources) if index not in indexes]
                if not table.rows:
                    continue
            filtered_tables.append(table)
        tables = filtered_tables
    return SourceArchive(files, tables, digest.hexdigest(), bool(meta), dict(inputs), dropped_extension_rows)


def dropped_extension_warnings(archive):
    return [{'id': f'dropped-extension-rows:{index}', 'title': 'Unlinked records left out',
             'reason': f"{item['rows']} records from {item['name']} were left out of the Data Package because they are not linked to a row of the main table (the link is blank, ambiguous or not found). The copy of your original files in the download still has them.",
             'rows': item['rows']}
            for index, item in enumerate(archive.dropped_extension_rows)]


def _number(value, label, default=None):
    try:
        number = int(value) if value is not None else default
    except (TypeError, ValueError):
        raise ImportFailure(f"Invalid {label}: {value!r}.")
    if number is not None and number < 0:
        raise ImportFailure(f"{label} cannot be negative.")
    return number


def _escaped(value):
    return {"\\t": "\t", "\\n": "\n", "\\r": "\r", "\\r\\n": "\r\n"}.get(value, value)


def _csv(content, encoding="utf-8", separator=",", quote='"', skip=0):
    try:
        text = content.decode(encoding, "strict").lstrip("\ufeff")
        if len(separator) != 1 or len(quote) > 1:
            raise ImportFailure("meta.xml must declare single characters for the column separator and the quote character.")
        reader = csv.reader(io.StringIO(text, newline=""), delimiter=separator,
                            quotechar=quote or None, quoting=csv.QUOTE_MINIMAL if quote else csv.QUOTE_NONE,
                            strict=True)
        rows = []
        for i, row in enumerate(reader):
            if i < skip:
                continue
            if len(row) > MAX_COLUMNS or len(rows) >= MAX_ROWS:
                raise ImportFailure("A table has more than 500 columns or more than 500,000 rows.")
            if row:  # A blank physical record has no source cells.
                rows.append(row)
        return rows
    except (UnicodeError, LookupError, csv.Error) as exc:
        raise ImportFailure(f"A table could not be read: {exc}.") from exc


def _manifest_tables(files, meta_name):
    content = files[meta_name]
    if re.search(br"<!\s*(DOCTYPE|ENTITY)\b", content, re.I):
        raise ImportFailure("The XML file uses document types or entities, which ChatIPT does not read for safety reasons.")
    try:
        root = etree.fromstring(content, etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False))
    except etree.XMLSyntaxError as exc:
        raise ImportFailure(f"meta.xml cannot be parsed: {exc}.") from exc
    if root.getroottree().docinfo.doctype:
        raise ImportFailure('The XML file uses document types or entities, which ChatIPT does not read for safety reasons.')
    ns = "{http://rs.tdwg.org/dwc/text/}"
    if root.tag != ns + "archive" or len(root.findall(ns + "core")) != 1:
        raise ImportFailure("meta.xml must describe exactly one main table (core) in the standard Darwin Core text format.")
    tables = []
    for node in [root.find(ns + "core"), *root.findall(ns + "extension")]:
        is_core = node.tag == ns + "core"
        row_type = node.get("rowType", "")
        if _escaped(node.get('linesTerminatedBy', '\\n')) not in {'\n', '\r', '\r\n'}:
            raise ImportFailure('Only tables with one record per line are supported.')
        if is_core and row_type not in {DWC + "Occurrence", DWC + "Event", DWC + "Taxon"}:
            raise ImportFailure(f"Archives whose main table holds {row_type.rsplit('/', 1)[-1] or 'unnamed'} records are not supported yet.")
        key = node.find(ns + ("id" if is_core else "coreid"))
        index = _number(key.get("index") if key is not None else None, "join index")
        if index is None:
            raise ImportFailure("Each table in meta.xml must say which column links it to the others (id or coreid).")
        fields = node.findall(ns + "field")
        terms = [field.get("term", "") for field in fields]
        if any(not term for term in terms) or len(set(terms)) != len(terms):
            raise ImportFailure("In meta.xml, each column of a table needs its own term, and no term may be repeated.")
        indices = [_number(field.get("index"), "field index") for field in fields]
        if any(value is None and "default" not in field.attrib for value, field in zip(indices, fields)):
            raise ImportFailure("In meta.xml, a field without a column index needs a default value.")
        rows, ids, row_sources, locations = [], [], [], node.findall(ns + "files/" + ns + "location")
        if not locations:
            raise ImportFailure("A table in meta.xml has no file location.")
        for location in locations:
            path = safe_path(str(PurePosixPath(meta_name).parent / (location.text or "")))
            if path not in files:
                # Loose browser uploads have basenames even when meta.xml names directories.
                matches = [name for name in files if PurePosixPath(name).name == PurePosixPath(path).name]
                if len(matches) != 1:
                    raise ImportFailure(f"meta.xml references missing file {path!r}.")
                path = matches[0]
            raw_rows = _csv(files[path], node.get("encoding", "utf-8"), _escaped(node.get("fieldsTerminatedBy", "\t")),
                            _escaped(node.get("fieldsEnclosedBy", "")), _number(node.get("ignoreHeaderLines"), "header count", 0))
            minimum = max([index, *[value for value in indices if value is not None]]) + 1
            widths = {len(row) for row in raw_rows}
            if len(widths) > 1 or widths and min(widths) < minimum:
                raise ImportFailure(f"{path} has rows with different numbers of columns, or fewer columns than meta.xml declares.")
            for record, row in enumerate(raw_rows, start=1):
                ids.append(row[index])
                row_sources.append({'file': path, 'data_record': record})
                rows.append([row[i] if i is not None and row[i] != "" else field.get("default", "")
                             for i, field in zip(indices, fields)])
        tables.append(SourceTable(" + ".join(location.text or "" for location in locations), row_type, terms, rows, ids, is_core, row_sources=row_sources))
    return tables


def _loose_tables(files):
    tables = []
    roles = {"occurrence": DWC + "Occurrence", "event": DWC + "Event", "taxon": DWC + "Taxon",
             "distribution": 'http://rs.gbif.org/terms/1.0/Distribution',
             "vernacularname": 'http://rs.gbif.org/terms/1.0/VernacularName',
             "typesandspecimen": 'http://rs.gbif.org/terms/1.0/TypesAndSpecimen',
             "identificationhistory": DWC + "Identification", "identification": DWC + "Identification",
             "measurementorfact": DWC + "MeasurementOrFact", "extendedmeasurementorfact": "http://rs.iobis.org/obis/terms/ExtendedMeasurementOrFact",
             "resourcerelationship": DWC + "ResourceRelationship", "dnaderiveddata": "http://rs.gbif.org/terms/1.0/DNADerivedData",
             'multimedia': 'http://rs.gbif.org/terms/1.0/Multimedia', 'images': 'http://rs.gbif.org/terms/1.0/Image',
             'audubon': 'http://rs.tdwg.org/ac/terms/Multimedia', 'audiovisual': 'http://rs.tdwg.org/ac/terms/Multimedia'}
    roles.update({'identifier': 'http://rs.gbif.org/terms/1.0/Identifier', 'alternativeidentifiers': 'http://rs.gbif.org/terms/1.0/Identifier',
                 'reference': 'http://rs.gbif.org/terms/1.0/Reference', 'references': 'http://rs.gbif.org/terms/1.0/Reference'})
    roles['humboldt'] = 'http://rs.tdwg.org/eco/terms/Event'
    roles.update({'eolmedia': 'http://eol.org/schema/media/Document', 'eolreferences': 'http://eol.org/schema/reference/Reference'})
    roles.update({name: 'http://purl.org/germplasm/germplasmTerm#' + row_type for name, row_type in {
        'germplasmaccession': 'GermplasmAccession', 'measurementscore': 'MeasurementScore',
        'measurementtrait': 'MeasurementTrait', 'measurementtrial': 'MeasurementTrial'}.items()})
    roles.update({'bmde': 'http://www.birdscanada.org/bmde/Observation', 'nbn': 'http://rs.nbn.org.uk/dwc/nxf/0.1/terms/nxfOccurrence'})
    for name, content in files.items():
        if PurePosixPath(name).suffix.lower() not in {".csv", ".tsv", ".txt"}:
            continue
        try:
            sample = content[:65536].decode("utf-8-sig", "strict")
            separator = csv.Sniffer().sniff(sample, delimiters=",\t;").delimiter
        except (UnicodeError, csv.Error):
            separator = "\t" if PurePosixPath(name).suffix.lower() in {".tsv", ".txt"} else ","
        rows = _csv(content, "utf-8-sig", separator)
        if not rows:
            continue
        header, rows = rows[0], rows[1:]
        if len(set(header)) != len(header) or any(len(row) != len(header) for row in rows):
            raise ImportFailure(f"{name} has repeated column headers, or rows with different numbers of columns.")
        stem = re.sub(r"^\d+__", "", PurePosixPath(name).stem).replace("_", "").replace("-", "").lower()
        role = roles.get(stem, "")
        names = REGISTRY.get("row_types", {}).get(role, {})
        terms = []
        for column in header:
            candidates = names.get(column, REGISTRY["terms"].get(column, []))
            terms.append(column if column.startswith(("http://", "https://")) else candidates[0] if len(candidates) == 1 else "header:" + column)
        if len(set(terms)) != len(terms):
            raise ImportFailure(f"{name} has several columns for the same Darwin Core term; keep only one of them.")
        tables.append(SourceTable(name, role, terms, rows, [], loose=True, join_basis='Not linked', row_sources=[{'file': name, 'data_record': index+1} for index in range(len(rows))]))
    cores = ([table for table in tables if table.row_type == DWC + "Taxon"] or
             [table for table in tables if table.row_type == DWC + "Event"] or
             [table for table in tables if table.row_type == DWC + "Occurrence"])
    if len(cores) != 1:
        raise ImportFailure("Loose files need exactly one main table, named taxon.csv, event.csv or occurrence.csv. Include meta.xml for other layouts.")
    core = cores[0]; core.is_core = True
    key = DWC + {DWC + 'Event': 'eventID', DWC + 'Occurrence': 'occurrenceID', DWC + 'Taxon': 'taxonID'}[core.row_type]
    for table in tables:
        if not table.row_type and not table.is_core:
            continue
        if not table.is_core and key not in core.terms:
            table.row_type = ''
            table.unplaced_reason = f'The main table has no {key.rsplit("/", 1)[-1]} column, so this table cannot be linked to it.'
            table.join_basis = 'Not linked'
            continue
        if key in table.terms:
            table.ids = [row[table.terms.index(key)] for row in table.rows]
            table.join_basis = key
        elif table.row_type == DWC + 'ResourceRelationship' and DWC + 'resourceID' in table.terms:
            table.ids = [row[table.terms.index(DWC + 'resourceID')] for row in table.rows]
            table.join_basis = DWC + 'resourceID'
        elif table.is_core:
            table.ids = [str(index + 1) for index in range(len(table.rows))]
            table.join_basis = 'Row number (there is no ID column)'
        elif table.row_type:
            # Without a verified link, preserve the table rather than attaching rows by position.
            table.row_type = ""
            table.join_basis = 'Not linked'
            table.unplaced_reason = f'This table has no {key.rsplit("/", 1)[-1]} column to link it to the main table.'
    # File selection and ZIP directory order do not change source identity or table keys.
    return [core, *sorted((table for table in tables if table is not core), key=lambda table: table.name)]


def source_zip(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content)
    return output.getvalue()
