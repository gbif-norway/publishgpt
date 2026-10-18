"""Conservative, row-linked date preservation checks before transformation.

Only compare tables with a shared, unique source identifier. Never infer row
identity from row position: preparation may filter, split or reorder records.
"""

import re

import pandas as pd


PREPARATION_TASKS = frozenset({
    "Data structure exploration",
    "Data content exploration",
    "Data suitability assessment",
})


def _name(value):
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def _columns(frame):
    # Ambiguous duplicate labels cannot support a reliable comparison.
    names = [_name(column) for column in frame.columns]
    return {name: column for name, column in zip(names, frame.columns)
            if name and names.count(name) == 1}


def _is_date(column):
    words = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(column)).casefold()
    tokens = re.findall(r"[a-z]+", words)
    return bool(set(tokens) & {"date", "time", "datetime", "timestamp", "created", "updated", "modified"}) or bool(
        re.fullmatch(r"(?:created|updated|modified)(?:at|on)", _name(column))
    )


def _text(series):
    return series.astype("string").fillna("").str.strip()


def _identifier(name):
    return name.endswith(("id", "identifier", "uuid", "key"))


def date_changes(sources, prepared):
    """Return changed date counts, using only unambiguous source/table links.

    Header case and punctuation may change. A verbatim/original-prefixed copy
    also preserves the evidence when a working date was deliberately corrected.
    This is a targeted guard, not a substitute for final source reconciliation.
    """
    changes = []
    for table_label, working in prepared:
        work_columns = _columns(working)
        candidates = []
        for source_label, source in sources:
            source_columns = _columns(source)
            date_columns = {name: column for name, column in source_columns.items()
                            if _is_date(column) and name in work_columns}
            if not date_columns:
                continue
            shared = source_columns.keys() & work_columns.keys()
            for key in sorted(shared):
                if not _identifier(key) or _is_date(source_columns[key]):
                    continue
                original_keys = _text(source[source_columns[key]])
                working_keys = _text(working[work_columns[key]])
                if (original_keys.eq("").any() or working_keys.eq("").any()
                        or original_keys.duplicated().any() or working_keys.duplicated().any()
                        or working_keys.empty
                        or not working_keys.isin(original_keys).all()):
                    continue
                # Prefer the source with the greatest shared schema. Equal best
                # sources with reused local IDs are ambiguous and are skipped.
                candidates.append((len(shared), source_label, source, source_columns,
                                   date_columns, original_keys, working_keys, key))
                break
        if not candidates:
            continue
        best_score = max(candidate[0] for candidate in candidates)
        best = [candidate for candidate in candidates if candidate[0] == best_score]
        if len(best) != 1:
            continue
        _, source_label, source, source_columns, date_columns, original_keys, working_keys, key = best[0]
        for name, column in date_columns.items():
            original = pd.Series(_text(source[column]).to_numpy(), index=original_keys)
            expected = original.loc[working_keys].reset_index(drop=True)
            preserved = pd.Series(False, index=expected.index)
            for candidate in (name, "verbatim" + name, "original" + name):
                if candidate in work_columns:
                    actual = _text(working[work_columns[candidate]]).reset_index(drop=True)
                    preserved |= expected.eq(actual)
            count = int((~preserved).sum())
            if count:
                changes.append({"source": source_label, "table": table_label,
                                "column": str(column), "key": str(source_columns[key]),
                                "changed_rows": count})
    return changes


def preparation_date_error(dataset, warnings=None):
    """Block demonstrated date mutations; report unavailable evidence as a warning."""
    from api.models import Table, UserFile

    prepared = [(f"table {table.id}", table.df) for table in dataset.table_set.all()
                if table.df is not None]
    if not prepared:
        return None
    sources = []
    for user_file in dataset.user_files.all():
        if user_file.file_type != UserFile.FileType.TABULAR:
            continue
        try:
            _, frames = user_file.extract_data()
        except Exception as exc:
            if warnings is not None:
                warnings.append(f"Could not verify source date preservation for {user_file.filename}: {exc}")
            continue
        sources.extend((f"{user_file.filename} / {sheet}", Table.make_columns_unique(frame.copy()))
                       for sheet, frame in frames.items() if frame is not None)
    changes = date_changes(sources, prepared)
    if not changes:
        return None
    details = "; ".join(
        f"{change['table']} `{change['column']}`: {change['changed_rows']} changed retained rows "
        f"(source {change['source']}, matched by `{change['key']}`)"
        for change in changes[:10]
    )
    return (
        "Error: Source date values changed during preparation. " + details + ". "
        "Keep this stage open. Use `sources[filename][sheet_name]` to restore the original "
        "values by the listed identifier for retained rows only; keep user-excluded rows excluded. "
        "Do not copy one date column over another, truncate time/precision, or fill missing "
        "components. Deliberate structural repairs (such as removing an unmerged-cell marker "
        "or filling grouped dates) and user-directed corrections may proceed when their source "
        "cells are retained in a `verbatim<original column name>` column. Keep the repair rather "
        "than undoing it when that original evidence is preserved. Leave date normalization to Data transformation, "
        "then call SetAgentTaskToComplete again."
    )
