from pydantic import BaseModel, Field
from rich.console import Console
from typing import Any, Callable


class TurnLocator(BaseModel):
    index: int = Field(..., description="Turn index")
    isolated: bool = Field(False, description="Is the turn isolated")


class FormatterSpec(BaseModel):
    before_case: Callable[[Console, dict[str, Any]], None] = Field(
        default=None, description="Function to generate contents before each case"
    )
    after_case: Callable[[Console, dict[str, Any]], None] = Field(
        default=None, description="Function to generate contents after each case"
    )
    format_turn: Callable[[Console, int, dict[str, Any]], None] = Field(
        default=None, description="Function to generate contents for each turn"
    )


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
    """
    Convenience factory creates ColumnSpec for use in SummarizerSpec.
    """
    return ColumnSpec(name=name, contents=contents, params=kwargs)


class SummarizerSpec(BaseModel):
    columns: list[ColumnSpec] = Field([], description="List of columns to summarize")


class MappingSpec(BaseModel):
    # If the test case is multi-turn
    #   path to the turns collection in the case
    # Otherwise None
    turns: str = Field(default=None, min_length=1, description="Turns collection")
    # If the test case is multi-turn
    #   path to the initial value of the sequence of turns
    #   (e.g. empty shopping cart, zero accumulator)
    # Otherwise None
    initial: str = Field(default=None, min_length=1, description="Initial turn value")
    # Path to the expected value in the suite, relative to the turn or the case
    expected: str = Field(..., min_length=1, description="Expected turn value")
    # Path to the observed value in stages, relative to the turn or the case
    observed: str = Field(..., min_length=1, description="Observed turn value")
    # Path to the user input in the suite, relative to the turn or the case
    user: str = Field(..., min_length=1, description="User text")


class PipelineSpec(BaseModel):
    name: str = Field(..., min_length=1, description="Pipeline name")
    description: str = Field(..., min_length=1, description="Pipeline description")
    configuration: dict[str, Any] = Field(..., description="Pipeline configuration")
    create_dag: Callable[[str, dict[str, Any], Any], Any] = Field(
        ..., description="Function to create the DAG"
    )
    formatter: FormatterSpec | Callable = Field(
        default=None, description="Optional formatter spec or function"
    )
    passed_predicate: Callable[[dict[str, Any]], bool] = Field(
        default=lambda result: False,
        description="Function to determine if the summarization passed",
    )
    summarizer: SummarizerSpec | Callable = Field(
        default=None, description="Optional summarizer spec or function"
    )
    mappings: MappingSpec = Field(
        default=None, description="Optional turns configuration"
    )
    # TODO: Compare


class PipelineSpecs:
    """
    Registry for PipelineSpec objects.
    """

    def __init__(self, pipelines: list[PipelineSpec]):
        self.pipelines = pipelines

    def get(self, name: str) -> PipelineSpec | None:
        """
        Retrieve a PipelineSpec by name.
        """
        spec = next((p for p in self.pipelines if p.name == name), None)
        if spec is None:
            raise ValueError(f"Cannot find pipeline '{name}'.")
        return spec

    def __iter__(self):
        return iter(self.pipelines)

    def __len__(self):
        return len(self.pipelines)
