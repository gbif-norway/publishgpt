# Dataset 583 provisional validation findings

The refinement agent reported compatibility issues from GBIF validation
`05a86b4f-73ea-4807-a2a4-eb9c72dfebfb`. All 2,426 records were indexable, but
the disposable archive had 567 `OCCURRENCE_STATUS_UNPARSABLE` and 2,227
`RECORDED_DATE_MISMATCH` issues.

The final archive was already corrected during the workflow. Its validation
`24d5850a-7340-489b-a1c6-3fa2204fbaf9` contains neither issue. This fix addresses
the shared exporter and early checks so future runs do not need agent repair.

- The exporter recognized `not detected`, but missed canonical `notDetected`.
  Both now map to `absent` in exported occurrence cores and extensions.
  The authoritative DwC-DP value stays unchanged.
- The BDQ-inspired check now recognizes recommended `detected`/`notDetected`
  and legacy `present`/`absent`. Custom terms remain a warning that allows a
  justified vocabulary extension, rather than a schema error.
- GBIF compares date precision as well as values. A full eventDate accompanied
  only by its agreeing year can lose precision during interpretation. The
  provisional copy now omits that redundant year for a complete ISO date with
  no other supplied date components. Conflicting years, partial or invalid
  dates, intervals, and rows with other components remain for validation.
  The report distinguishes projection compatibility from source conflicts.

This follows [GBIF's advice to supply eventDate alone and let interpretation
derive components](https://techdocs.gbif.org/en/data-processing/temporal-interpretation).
The [vendored occurrence schema](../back-end/api/templates/dwc-dp/table-schemas/occurrence.json)
recommends `detected`/`notDetected`, while allowing justified extensions.

A local replay of the patched functions against a read-only production snapshot
of 583's date and status columns produced:

| Check | Result |
| --- | ---: |
| Exported present / absent | 1,859 / 567 |
| Status vocabulary warnings | 0 |
| Redundant years omitted from provisional copy | 2,132 |
| Genuine date conflicts before / after | 95 / 95 |

The date counts account for the original 2,227 GBIF warnings. These are local
replay results, not a new GBIF validation run. No production data or packages
were changed, and the dataset remains unpublished.

Regression tests cover the real provisional export, the occurrence extension,
source-table preservation, current and custom vocabulary, and date conflicts.
All 1,124 backend tests pass in Docker.
