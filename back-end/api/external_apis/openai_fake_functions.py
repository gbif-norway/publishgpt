from pydantic import BaseModel, Field, PositiveInt
from typing import List
from typing_extensions import Annotated
from enum import Enum

# TranslateNonEnglishColumns
# MergeTopRowsAndCreateHeader
# DropColumnsRows
# Uncrosstab
# JoinColumnsRows
# SplitColumnsRows
# MapToDarwinCore
# FixDates
# AddBasisOfRecord

class TaskStatusEnum(str, Enum):
    COMPLETED = 'completed'
    SKIPPED = 'skipped'
    IN_PROGRESS = 'in_progress'

class GoToNextTask(BaseModel):
    set_current_task_status: TaskStatusEnum

# class SkipToNextTask(BaseModel):
#     proceed: bool = Field(...)

# class SetTaskAsComplete(BaseModel):
#     skip: bool = Field(...)

class DisplayScientificNameFeedbackMessage(BaseModel):
    scientific_name_missing: bool = Field(...)

class ColumnReference(BaseModel):
    column_index: int = Field(...)
    language_two_letter_iso_code: str = Field(...)

class TranslateNonEnglishColumns(BaseModel):
    non_english_column_references: List[ColumnReference] = Field(...)

class SetTaskStatus_TranslateNonEnglishColumns(BaseModel):
    non_english_column_references: List[ColumnReference] = Field(...)
    set_current_task_status: TaskStatusEnum

class DropColumnsRows(BaseModel):
    row_indexes: List[int] = Field(...)
    column_indexes: List[int] = Field(...)

class SetTaskStatus_DropColumnsRows(BaseModel):
    row_indexes: List[int] = Field(...)
    column_indexes: List[int] = Field(...)
    set_current_task_status: TaskStatusEnum

class MergeTopRowsIntoHeader(BaseModel):
    number_of_top_rows_to_merge: PositiveInt = Field(...)

class SetTaskStatus_MergeTopRowsIntoHeader(BaseModel):
    number_of_top_rows_to_merge: PositiveInt = Field(...)
    set_current_task_status: TaskStatusEnum
    # number_of_top_rows_to_merge: Annotated[int, Field(gt=0)]

class MergeRows(BaseModel):
    row_indexes: List[int] = Field(...)

