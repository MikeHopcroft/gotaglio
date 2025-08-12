from glom import glom
from rich.table import Table
from rich.text import Text
from typing import Any, Callable

from .helpers import IdShortener
from .pipeline_spec import column_spec, SummarizerSpec, TurnMappingSpec


def summarize(
    passed_predicate: Callable[[dict[str, Any]], bool],
    summarizer_spec: SummarizerSpec,
    turn_spec: TurnMappingSpec | None,
    make_console: Callable,
    runlog: dict[str, Any],
):
    s = Summarizer(passed_predicate, summarizer_spec, turn_spec)
    s.summarize(make_console, runlog)


class Summarizer:
    def __init__(
        self,
        passed_predicate: Callable[[dict[str, Any]], bool],
        summarizer_spec: SummarizerSpec,
        turn_spec: TurnMappingSpec | None = None,
    ):
        self._passed_predicate = passed_predicate
        self._summarizer_spec = summarizer_spec
        self._turn_spec = turn_spec

    # This method is used to summarize the results of each a pipeline run.
    # It is invoked by the `run`, `rerun`, and `summarize` sub-commands.
    def summarize(self, make_console, runlog):
        console = make_console("text/plain")
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
                    if self._turn_spec is None
                    else f"{short_id(result['case']['uuid'])}.{turn_index:02}"
                )

            def status_cell(result, turn_index):
                succeeded = (
                    result["succeeded"]
                    if self._turn_spec is None
                    else result["stages"]["turns"][turn_index]["succeeded"]
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
                    if self._turn_spec is not None
                    else result
                )
                if self._turn_spec:
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
        # TODO: reinstate the cost calculation logic.
        #   cost = (
        #       turn_result["stages"]["assess"] if succeeded else None # TODO: configurable
        #   )
        # cost = turn_index % 2  # Dummy cost for demonstration purposes
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
