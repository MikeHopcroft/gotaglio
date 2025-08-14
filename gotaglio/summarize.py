from glom import glom
from rich.table import Table
from rich.text import Text
from typing import Any

from .helpers import IdShortener
from .make_console import MakeConsole
from .pipeline_spec import PipelineSpec, column_spec


def summarize(
    spec: PipelineSpec,
    runlog: dict[str, Any],
):
    console_buffer = MakeConsole()
    console = console_buffer("text/plain")
    if callable(spec.summarizer):
        spec.summarizer(console, runlog)
    else:
        s = Summarizer(spec)
        s.summarize(console, runlog)
    console_buffer.render()

class Summarizer:
    def __init__(
        self, spec: PipelineSpec
    ):
        self._passed_predicate = spec.passed_predicate
        self._summarizer_spec = spec.summarizer
        self._mapping_spec = spec.mappings
        self._using_turns = spec.mappings.turns is not None

    # This method is used to summarize the results of each pipeline run.
    # It is invoked by the `run`, `rerun`, and `summarize` sub-commands.
    def summarize(self, console, runlog):
        results = runlog["results"]
        if len(results) == 0:
            console.print("No results.")
        else:
            # To make the summary more readable, create a short, unique prefix
            # for each case id.
            short_id = IdShortener([result["case"]["uuid"] for result in results])

            def id_cell(result, turn_index):
                return (
                    short_id(result["case"]["uuid"])
                    if self._using_turns
                    else f"{short_id(result['case']['uuid'])}.{turn_index:02}"
                )

            def status_cell(result, turn_index):
                succeeded = (
                    result["stages"]["turns"][turn_index]["succeeded"]
                    if self._using_turns
                    else result["succeeded"]
                )
                return (
                    Text("COMPLETE", style="bold green")
                    if succeeded
                    else Text("ERROR", style="bold red")
                )

            columns = [
                column_spec(
                    name="id",
                    contents=id_cell,
                    justify="right",
                    style="cyan",
                    no_wrap=True,
                ),
                column_spec(name="status", contents=status_cell, style="magenta"),
            ]
            for column in self._summarizer_spec.columns:
                columns.append(column)

            # Using Table from the rich text library.
            # https://rich.readthedocs.io/en/stable/introduction.html
            table = Table(title=f"Summary for {runlog['uuid']}")
            for column in columns:
                table.add_column(
                    column.name,
                    **column.params,
                )
            # TODO: reinstate
            #   table.add_column("score", justify="right", style="green")
            #   table.add_column("user", justify="left", style="green")

            # Set up some counters for totals to be presented after the table.
            self.total_count = 0
            self.complete_count = 0
            self.passed_count = 0
            self.failed_count = 0
            self.error_count = 0

            # Add one row for each case.
            for result in results:
                turn_results = (
                    glom(result, "stages.turns", default=[])
                    if self._using_turns
                    else result
                )
                if self._using_turns:
                    for index, turn_result in enumerate(turn_results):
                        self.render_one_row(table, columns, result, index, turn_result)
                else:
                    # If there are no turns, we just render the result as a single row.
                    self.render_one_row(table, columns, result, 0, turn_results)

            # Display the table and the totals.
            console.print(table)
            console.print()
            console.print(f"Total: {self.total_count}")
            console.print(
                f"Complete: {self.complete_count}/{self.total_count} ({(self.complete_count/self.total_count)*100:.2f}%)"
            )
            console.print(
                f"Error: {self.error_count}/{self.total_count} ({(self.error_count/self.total_count)*100:.2f}%)"
            )
            console.print(
                f"Passed: {self.passed_count}/{self.total_count} ({(self.passed_count/self.total_count)*100:.2f}%)"
            )
            console.print(
                f"Failed: {self.failed_count}/{self.total_count} ({(self.failed_count/self.total_count)*100:.2f}%)"
            )
            console.print()

    def render_one_row(self, table, columns, result, turn_index, turn_result):
        succeeded = turn_result["succeeded"]
        passed = self._passed_predicate(turn_result)

        self.total_count += 1
        if succeeded:
            self.complete_count += 1
            if passed:
                self.passed_count += 1
            else:
                self.failed_count += 1
        else:
            self.error_count += 1

        row = [col.contents(result, turn_index) for col in columns]
        table.add_row(*row)


def keywords_cell(result, turn_index):
    return (
        ", ".join(sorted(result["case"]["keywords"]))
        if "keywords" in result["case"]
        else ""
    )


keywords_column = column_spec(name="keywords", contents=keywords_cell)
