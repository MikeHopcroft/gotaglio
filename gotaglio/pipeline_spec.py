from pydantic import BaseModel, validator, Field
from typing import Any, Dict, Callable, List, Optional, Union


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
    # Format
    # Compare


# def cell_contents():
#     return "Cell content goes here"

# def go():
#     # x = ColumnSpec(name="A", contents=cell_contents)
#     # y = PipelineSpec(name="B", summarize=[x])
#     # print(y)
#     spec = PipelineSpec(
#         name="calculator",
#         description="A simple calculator pipeline",
#         configuration={"precision": 2},
#         turns=TurnSpec(
#             initial="value",
#             expected="expected",
#             observed="extract"
#         ),
#         create_dag=lambda name, config: lambda x: x,  # Dummy DAG function
#         summarize=[ColumnSpec(name="Result", contents=cell_contents)],
#     )
#     print(spec)

# go()
