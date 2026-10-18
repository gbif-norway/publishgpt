"""Regression checks for preserving explicit source values through ingestion and coverage."""

import csv
import io
import tarfile
import tempfile
from pathlib import Path

import openpyxl
import pandas as pd
from django.test import SimpleTestCase

from api.models import UserFile
from api.dwc_dp_specs import create_dwc_dp_archive
from api.source_coverage import normalize_value, reconcile, render_report


class UploadBytes:
    def __init__(self, name, content):
        self.name = name
        self.content = content

    def open(self, mode):
        pass

    def read(self):
        return self.content

    def close(self):
        pass


class LiteralUploadTests(SimpleTestCase):
    literals = ["NA", "N/A", "NULL", "null", "NaN", "nan", "None", "none", "<NA>", "NaT", "#N/A"]

    def assert_source_values(self, frames):
        frame = next(iter(frames.values()))
        self.assertEqual(frame["code"].iloc[:-1].tolist(), self.literals)
        self.assertTrue(pd.isna(frame["code"].iloc[-1]))
        self.assertEqual(frame["recordID"].iloc[0], "000001")
        self.assertEqual(frame["measurement"].iloc[0], "1.12345678901234567890123456789")
        self.assertEqual(frame["Annotation_Time"].iloc[0], "2026-06-25T09:16:24.625Z")
        self.assertEqual(frame["Created_At"].iloc[0], "2026-06-25T09:16:24.626Z")
        manifest = UserFile.build_source_manifest(frames)
        column = next(c for c in manifest["tables"][0]["columns"] if c["name"] == "code")
        self.assertEqual(column["populated"], len(self.literals))
        self.assertEqual(column["unique"], len(self.literals))

    def rows(self):
        yield ["recordID", "code", "measurement", "Annotation_Time", "Created_At"]
        for i, code in enumerate(self.literals + [""]):
            yield [f"{i + 1:06d}", code, "1.12345678901234567890123456789",
                   "2026-06-25T09:16:24.625Z", "2026-06-25T09:16:24.626Z"]

    def test_delimited_uploads_keep_literal_codes_and_independent_dates(self):
        for extension, delimiter in [("csv", ","), ("tsv", "\t"), ("txt", ";")]:
            with self.subTest(format=extension):
                content = io.StringIO()
                csv.writer(content, delimiter=delimiter).writerows(self.rows())
                upload = UserFile()
                upload.file = UploadBytes(f"source.{extension}", content.getvalue().encode())
                file_type, frames = upload.extract_data()
                self.assertEqual(file_type, UserFile.FileType.TABULAR)
                self.assert_source_values(frames)

    def test_excel_uploads_keep_literal_text_and_real_empty_cells(self):
        workbook = openpyxl.Workbook()
        for row in self.rows():
            workbook.active.append(row)
        # An explicitly textual #N/A is distinct from an Excel error cell.
        for row in workbook.active:
            for cell in row:
                if cell.value == "#N/A":
                    cell.data_type = "s"
        content = io.BytesIO()
        workbook.save(content)
        upload = UserFile()
        upload.file = UploadBytes("source.xlsx", content.getvalue())
        _, frames = upload.extract_data()
        self.assert_source_values(frames)

    def test_reconciliation_detects_literal_codes_lost_from_package(self):
        upload = UserFile()
        upload.file = UploadBytes("source.csv", b"recordID,code\na,LC\nb,NA\nc,NULL\nd,\n")
        _, frames = upload.extract_data()
        source = frames["source.csv"]
        package = {"occurrence-assertion": pd.DataFrame({"assertionValue": ["LC"]})}
        result = reconcile([("original source", source)], package)[0]
        code = next(c for c in result.columns if c.name == "code")
        self.assertEqual(code.populated, 3)
        self.assertEqual(code.distinct, 3)
        self.assertNotEqual(code.status, "mapped")
        self.assertIn("code", render_report([result], package).split("COVERAGE OPEN ITEMS:")[1])
        package["occurrence-assertion"] = pd.DataFrame({"assertionValue": ["LC", "NA", "NULL"]})
        restored = reconcile([("original source", source)], package)[0]
        self.assertEqual(next(c for c in restored.columns if c.name == "code").status, "mapped")

    def test_uploaded_literal_codes_survive_the_validated_package_export(self):
        content = io.StringIO()
        csv.writer(content).writerows(self.rows())
        upload = UserFile()
        upload.file = UploadBytes("source.csv", content.getvalue().encode())
        _, frames = upload.extract_data()
        source = frames["source.csv"].dropna(subset=["code"])
        resources = {
            "event": pd.DataFrame({"event_pk": ["event-1"], "eventDate": ["2026-06-25"],
                                   "eventCategory": ["context"]}),
            "event-assertion": pd.DataFrame({
                "event_fk": ["event-1"] * len(source),
                "verbatimAssertionType": ["source code"] * len(source),
                "assertionValue": source["code"].tolist(),
            }),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "package.tar.gz"
            create_dwc_dp_archive(path, resources, title="Source codes", description="Preserved source text")
            with tarfile.open(path) as archive:
                text = archive.extractfile("event-assertion.csv").read().decode()
        self.assertEqual([row["assertionValue"] for row in csv.DictReader(io.StringIO(text))], self.literals)


class LiteralCoverageTests(SimpleTestCase):
    def test_working_table_stringification_artifacts_are_not_source_facts(self):
        source = pd.DataFrame({"recordID": ["a", "b"], "code": ["LC", None]})
        working = source.astype(str).rename(columns={"recordID": "record_id"})
        package = {"occurrence": pd.DataFrame({"occurrenceID": ["a", "b"], "code": ["LC", None]})}
        results = reconcile([("upload", source), ("working", working)], package,
                            working_source_labels={"working"})
        code = next(c for c in results[1].columns if c.name == "code")
        self.assertEqual(code.status, "mapped")
        self.assertEqual(code.populated, 1)
        self.assertEqual(working.code.tolist(), ["LC", "None"])

    def test_literal_missing_spellings_in_originals_stay_visible(self):
        source = pd.DataFrame({"code": ["NaN", "None", "<NA>", "NaT", None]})
        working = source.astype(str)
        package = {"occurrence-assertion": pd.DataFrame({"assertionValue": ["LC"]})}
        results = reconcile([("upload", source), ("working", working)], package,
                            working_source_labels={"working"})
        for result in results:
            self.assertEqual(result.columns[0].distinct, 4)
            self.assertEqual(result.columns[0].status, "not_found")

    def test_working_tables_without_uploads_keep_explicit_text(self):
        source = pd.DataFrame({"code": ["NaN", "None"]})
        result = reconcile([("extracted", source)], {}, working_source_labels={"extracted"})[0]
        self.assertEqual(result.columns[0].populated, 2)

    def test_even_one_missing_distinct_value_remains_an_open_item(self):
        values = [f"code-{i}" for i in range(100)]
        package = {"occurrence-assertion": pd.DataFrame({"assertionValue": values[:-1]})}
        result = reconcile([("source", pd.DataFrame({"code": values}))], package)[0]
        self.assertEqual(result.columns[0].status, "partial")
        self.assertEqual(result.columns[0].missing_examples, ["code-99"])
        self.assertIn("source: code", render_report([result], package).split("COVERAGE OPEN ITEMS:")[1])

    def test_only_actual_missing_values_and_empty_text_are_empty(self):
        for value in [None, pd.NA, float("nan"), pd.NaT, "", " \t "]:
            with self.subTest(value=value):
                self.assertIsNone(normalize_value(value))
        for value in LiteralUploadTests.literals:
            with self.subTest(value=value):
                self.assertEqual(normalize_value(value), value.casefold())

    def test_numeric_matching_does_not_round_away_differences(self):
        for before, after in [
            ("1.12345678901234567890123456789", "1.12345678901234567890123456788"),
            ("9007199254740992", "9007199254740993"),
            ("0.000000000000012345678901", "0.000000000000012345678902"),
        ]:
            with self.subTest(before=before):
                self.assertNotEqual(normalize_value(before), normalize_value(after))
                result = reconcile([("source", pd.DataFrame({"value": [before]}))],
                                   {"event-assertion": pd.DataFrame({"assertionValue": [after]})})[0]
                self.assertEqual(result.columns[0].status, "not_found")

    def test_equivalent_numeric_spellings_still_match(self):
        for values in [("12", "12.0", "+1.2e1", "0012.000"),
                       ("0", "-0.000", "0e999999"),
                       ("1e1000000", "10e999999")]:
            with self.subTest(values=values):
                self.assertEqual(len({normalize_value(value) for value in values}), 1)
