from pydantic import BaseModel, Field
from typing import Any, Callable


class TurnMappingSpec(BaseModel):
    initial: str = Field(..., min_length=1, description="Initial turn value")
    expected: str = Field(..., min_length=1, description="Expected turn value")
    observed: str = Field(..., min_length=1, description="Observed turn value")
    user: str = Field(..., min_length=1, description="User text")


class ColumnSpec(BaseModel):
    name: str = Field(..., min_length=1, description="Column name")
    params: dict[str, Any] = Field(
        {}, description="Rich formatting parameters for the column"
    )
    contents: Callable[[dict[str, Any]], Any] = Field(
        ..., description="Function to create the cell contents"
    )


def column_spec(
    name: str, contents: Callable[[dict[str, Any]], Any], **kwargs
) -> ColumnSpec:
    return ColumnSpec(name=name, contents=contents, params=kwargs)


class FormatterSpec(BaseModel):
    before_case: Callable[[dict[str, Any]], None] = Field(
        default=None, description="Function to generate contents before each case"
    )
    after_case: Callable[[dict[str, Any]], None] = Field(
        default=None, description="Function to generate contents after each case"
    )
    before_turn: Callable[[dict[str, Any]], None] = Field(
        default=None, description="Function to generate contents before each case"
    )
    after_turn: Callable[[dict[str, Any]], None] = Field(
        default=None, description="Function to generate contents after each case"
    )


class SummarizerSpec(BaseModel):
    columns: list[ColumnSpec] = Field([], description="List of columns to summarize")
    passed: Callable[[dict[str, Any]], bool] = Field(
        default=lambda result: False,
        description="Function to determine if the summarization passed",
    )


class PipelineSpec(BaseModel):
    name: str = Field(..., min_length=1, description="Pipeline name")
    description: str = Field(..., min_length=1, description="Pipeline description")
    configuration: dict[str, Any] = Field(..., description="Pipeline configuration")
    create_dag: Callable[[str, dict[str, Any], Any], Any] = Field(
        ..., description="Function to create the DAG"
    )
    turns: TurnMappingSpec = Field(None, description="Optional turns configuration")
    format: FormatterSpec | Callable = Field(
        default=None, description="Optional formatter spec or function"
    )
    summarize: SummarizerSpec | Callable = Field(
        ..., description="Optional summarizer spec or function"
    )

    # TODO: Format

    #  Compare
