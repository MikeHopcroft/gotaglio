from pydantic import BaseModel, validator, Field
from typing import Any, Dict, Callable, List, Union


class TurnSpec(BaseModel):
    initial: str = Field(..., min_length=1, description="Initial turn value")
    expected: str = Field(..., min_length=1, description="Expected turn value")
    observed: str = Field(..., min_length=1, description="Observed turn value")


class ColumnSpec(BaseModel):
    name: str = Field(..., min_length=1, description="Column name")
    params: Dict[str, Any] = Field(
        {}, description="Rich formatting parameters for the column"
    )
    contents: Callable[[Dict[str, Any]], Any] = Field(
        ..., description="Function to create the cell contents"
    )


def column_spec(
    name: str, contents: Callable[[Dict[str, Any]], Any], **kwargs
) -> ColumnSpec:
    return ColumnSpec(name=name, contents=contents, params=kwargs)


class SummarizerSpec(BaseModel):
    columns: List[ColumnSpec] = Field([], description="List of columns to summarize")


class PipelineSpec(BaseModel):
    name: str = Field(..., min_length=1, description="Pipeline name")
    description: str = Field(..., min_length=1, description="Pipeline description")
    configuration: Dict[str, Any] = Field(..., description="Pipeline configuration")
    create_dag: Callable[[str, Dict[str, Any]], Any] = Field(
        ..., description="Function to create the DAG"
    )
    turns: TurnSpec = Field(None, description="Optional turns configuration")
    summarize: Union[SummarizerSpec, Callable] = Field(
        ..., description="Optional summarizer spec or function"
    )

    # TODO: Format

    #  Compare
