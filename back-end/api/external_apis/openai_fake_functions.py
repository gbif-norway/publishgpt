from pydantic import BaseModel, Field
from typing import List

# TranslateNonEnglishColumns
# MergeTopRowsAndCreateHeader
# DropColumnsRows
# Uncrosstab
# JoinColumnsRows
# SplitColumnsRows
# MapToDarwinCore
# FixDates
# AddBasisOfRecord
class ProceedToNextTask(BaseModel):
    proceed: bool = Field(...)

class DisplayScientificNameFeedbackMessage(BaseModel):
    scientific_name_missing: bool = Field(...)

class ColumnReference(BaseModel):
    column_index: int = Field(...)
    language_two_letter_iso_code: str = Field(...)

class TranslateNonEnglishColumns(BaseModel):
    non_english_column_references: List[ColumnReference] = Field(...)

class DropColumnsRows(BaseModel):
    row_indexes: List[int] = Field(...)
    column_indexes: List[int] = Field(...)

class MergeTopRowsAndCreateHeader(BaseModel):
    number_of_top_rows_to_merge: int = Field(...)

class MergeRows(BaseModel):
    row_indexes: List[int] = Field(...)

class SetTaskAsComplete(BaseModel):
    pass
