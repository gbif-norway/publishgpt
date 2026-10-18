from unittest.mock import patch

import pandas as pd
from django.test import SimpleTestCase, TestCase

from api.agent_tools import SetAgentTaskToComplete
from api.models import Agent, Dataset, Table, Task, UserFile
from api.prepared_dates import PREPARATION_TASKS, date_changes


def annotation_source():
    # Reported shape: 1230 uploaded, 1191 retained, 461 distinct annotation dates.
    return pd.DataFrame({
        "Annotation_ID": [f"a-{i}" for i in range(1230)],
        "Annotation_Time": ["2020-01-01T12:34:56.123456789+02:00" if i < 461
                            else "2021-02-03" for i in range(1230)],
        "Created_At": ["2021-02-03"] * 1230,
        "locality": ["Retained" if i < 1191 else "Holmengaard" for i in range(1230)],
    })


class PreparedDateTests(SimpleTestCase):
    def setUp(self):
        self.source = annotation_source()
        self.working = self.source.iloc[:1191].iloc[::-1].reset_index(drop=True).copy()

    def check(self, source=None, working=None):
        return date_changes([("original.csv", self.source if source is None else source)],
                            [("table 2481", self.working if working is None else working)])

    def test_copied_creation_dates_detected_for_all_461_retained_rows(self):
        self.working["Annotation_Time"] = self.working["Created_At"]
        changes = self.check()
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["column"], "Annotation_Time")
        self.assertEqual(changes[0]["changed_rows"], 461)
        self.assertEqual(changes[0]["key"], "Annotation_ID")

    def test_filter_reorder_and_reset_index_preserve_dates(self):
        original = self.source.copy(deep=True)
        self.assertEqual(self.check(), [])
        pd.testing.assert_frame_equal(self.source, original)
        self.assertEqual(len(self.working), 1191)
        self.assertNotIn("Holmengaard", self.working.locality.values)

    def test_row_swaps_detected_even_when_all_distinct_values_survive(self):
        source = pd.DataFrame({"id": ["a", "b"], "eventDate": ["2000", "2001"]})
        working = source.copy()
        working["eventDate"] = ["2001", "2000"]
        self.assertEqual(self.check(source, working)[0]["changed_rows"], 2)

    def test_lost_precision_timezone_and_missing_components_are_detected(self):
        for before, after in [
            ("2020-01-01T12:34:56.123456789+02:00", "2020-01-01T12:34:56.123456+02:00"),
            ("2020-01-01T12:34:56+02:00", "2020-01-01T12:34:56"),
            ("2020-01-01T12:34:56", "2020-01-01"),
            ("2020", "2020-01-01"),
            (None, "2020-01-01"),
            ("2020-01-01", None),
        ]:
            with self.subTest(before=before, after=after):
                source = pd.DataFrame({"id": ["a"], "eventDate": [before]})
                working = pd.DataFrame({"id": ["a"], "eventDate": [after]})
                self.assertEqual(self.check(source, working)[0]["changed_rows"], 1)

    def test_header_case_and_punctuation_changes_do_not_hide_mutation(self):
        self.working = self.working.rename(columns={"Annotation_Time": "annotation time",
                                                     "Annotation_ID": "annotation id"})
        self.working["annotation time"] = self.working["Created_At"]
        self.assertEqual(self.check()[0]["changed_rows"], 461)

    def test_intentional_correction_keeps_original_evidence(self):
        self.working["verbatimAnnotation_Time"] = self.working["Annotation_Time"]
        self.working["Annotation_Time"] = self.working["Created_At"]
        self.assertEqual(self.check(), [])

    def test_grouped_date_repairs_can_proceed_with_original_cells_preserved(self):
        source = pd.DataFrame({"recordID": ["a", "b"], "observationDate": ["2020-03", None]})
        working = source.copy()
        working["observationDate"] = working.observationDate.ffill()
        self.assertEqual(self.check(source, working)[0]["changed_rows"], 1)
        working["verbatimObservationDate"] = source.observationDate
        self.assertEqual(self.check(source, working), [])

    def test_ambiguous_sources_and_duplicate_ids_are_not_joined(self):
        self.working["Annotation_Time"] = self.working["Created_At"]
        self.assertEqual(date_changes([("a.csv", self.source), ("b.csv", self.source)],
                                      [("prepared", self.working)]), [])
        self.source["Annotation_ID"] = "duplicate"
        self.working["Annotation_ID"] = "duplicate"
        self.assertEqual(self.check(), [])

    def test_non_date_fields_are_left_to_transformation(self):
        self.working["locality"] = "New locality"
        self.assertEqual(self.check(), [])


class PreparationCompletionTests(TestCase):
    def setUp(self):
        self.source = annotation_source()
        self.dataset = Dataset.objects.create(title="Annotations", description="Source evidence")
        self.upload = UserFile.objects.create(dataset=self.dataset, file="user_files/annotations.csv")
        self.table = Table.objects.create(dataset=self.dataset, title="annotations",
                                          df=self.source.iloc[:1191].copy())
        self.extract = patch.object(UserFile, "extract_data", return_value=(
            UserFile.FileType.TABULAR, {"annotations.csv": self.source},
        ))
        self.extract.start()
        self.addCleanup(self.extract.stop)

    def test_each_preparation_stage_rejects_overwritten_dates_and_accepts_restoration(self):
        for name in sorted(PREPARATION_TASKS):
            with self.subTest(stage=name):
                task = Task.objects.create(name=name)
                agent = Agent.objects.create(dataset=self.dataset, task=task)
                self.table.df["Annotation_Time"] = self.table.df["Created_At"]
                self.table.save()
                result = SetAgentTaskToComplete(agent_id=agent.id).run()
                self.assertIn("461 changed retained rows", result)
                self.assertIn("keep user-excluded rows excluded", result)
                agent.refresh_from_db()
                self.assertIsNone(agent.completed_at)
                self.table.refresh_from_db()
                self.assertEqual(len(self.table.df), 1191)
                self.table.df = self.source.iloc[:1191].copy()
                self.table.save()
                result = SetAgentTaskToComplete(agent_id=agent.id).run()
                self.assertIn("Task marked as complete", result)
                agent.refresh_from_db()
                self.assertIsNotNone(agent.completed_at)

    def test_unreadable_original_warns_without_deadlocking_preparation(self):
        task = Task.objects.create(name="Data structure exploration")
        agent = Agent.objects.create(dataset=self.dataset, task=task)
        with patch.object(UserFile, "extract_data", side_effect=OSError("unavailable")):
            result = SetAgentTaskToComplete(agent_id=agent.id).run()
        self.assertIn("Task marked as complete", result)
        self.assertIn("Could not verify source date preservation", result)
        agent.refresh_from_db()
        self.assertIsNotNone(agent.completed_at)

    def test_unreadable_attachment_does_not_hide_changes_to_readable_source(self):
        extra = UserFile.objects.create(dataset=self.dataset, file="user_files/unused.csv")
        self.table.df["Annotation_Time"] = self.table.df["Created_At"]
        self.table.save()
        task = Task.objects.create(name="Data structure exploration")
        agent = Agent.objects.create(dataset=self.dataset, task=task)

        def extract(upload):
            if upload.pk == extra.pk:
                raise OSError("unused attachment unavailable")
            return UserFile.FileType.TABULAR, {"annotations.csv": self.source}

        self.extract.stop()
        with patch.object(UserFile, "extract_data", autospec=True, side_effect=extract):
            result = SetAgentTaskToComplete(agent_id=agent.id).run()
        self.assertIn("461 changed retained rows", result)
        agent.refresh_from_db()
        self.assertIsNone(agent.completed_at)

    def test_other_stages_do_not_restrict_legitimate_normalization(self):
        task = Task.objects.create(name="Unrelated stage")
        agent = Agent.objects.create(dataset=self.dataset, task=task)
        with patch("api.prepared_dates.preparation_date_error") as check:
            result = SetAgentTaskToComplete(agent_id=agent.id).run()
        check.assert_not_called()
        self.assertIn("Task marked as complete", result)
