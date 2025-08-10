from rich.console import Console
from glom import glom
from rich.table import Table
from rich.text import Text
from typing import Any, Dict, Callable, List, Optional, Union

from .helpers import IdShortener
from .pipeline_spec import column_spec, ColumnSpec, SummarizerSpec, TurnSpec


def summarize(
    summarizer_spec: SummarizerSpec,
    turn_spec: Optional[TurnSpec],
    make_console: Callable,
    runlog: Dict[str, Any],
):
    s = Summarizer(summarizer_spec, turn_spec)
    s.summarize(make_console, runlog)


class Summarizer:
    def __init__(
        self, summarizer_spec: SummarizerSpec, turn_spec: Optional[TurnSpec] = None
    ):
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
                    result["stages"]["succeeded"]
                    if self._turn_spec is None
                    else result["stages"]["turns"][turn_index]["succeeded"]
                )
                return (
                    Text("COMPLETE", style="bold green")
                    if succeeded
                    else Text("ERROR", style="bold red")
                )

            def keywords_cell(result, turn_index):
                return (
                    ", ".join(sorted(result["case"]["keywords"]))
                    if "keywords" in result["case"]
                    else ""
                )

            columns = [
                column_spec(name="id", contents=id_cell, justify="right", style="cyan", no_wrap=True),
                column_spec(name="status", contents=status_cell, style="magenta"),
                column_spec(name="keywords", contents=keywords_cell),
            ]
            for column in self._summarizer_spec.columns:
                columns.append(column)

            # Using Table from the rich text library.
            # https://rich.readthedocs.io/en/stable/introduction.html
            table = Table(title=f"Summary for {runlog['uuid']}")
            # table.add_column("id", justify="right", style="cyan", no_wrap=True)
            # table.add_column("run", style="magenta")
            for column in columns:
                table.add_column(
                    column.name,
                    # justify="left",
                    # style="green",
                    **column.params,
                )
            # TODO: reinstate
            # table.add_column("score", justify="right", style="green")
            # table.add_column("keywords", justify="left", style="green")
            # table.add_column("user", justify="left", style="green")

            # Set up some counters for totals to be presented after the table.
            total_count = len(results)
            self.complete_count = 0
            self.passed_count = 0
            self.failed_count = 0
            self.error_count = 0

            # Add one row for each case.
            for result in results:
                # uuid = result["case"]["uuid"]
                turn_results = (
                    glom(result, "stages.turns", default=[])
                    if self._turn_spec is not None
                    else result
                )
                for index, turn_result in enumerate(turn_results):
                    self.render_one_row(
                        table, columns, result, index, turn_result
                    )

            # Display the table and the totals.
            console.print(table)
            console.print()
            console.print(f"Total: {total_count}")
            console.print(
                f"Complete: {self.complete_count}/{total_count} ({(self.complete_count/total_count)*100:.2f}%)"
            )
            console.print(
                f"Error: {self.error_count}/{total_count} ({(self.error_count/total_count)*100:.2f}%)"
            )
            console.print(
                f"Passed: {self.passed_count}/{total_count} ({(self.passed_count/total_count)*100:.2f}%)"
            )
            console.print(
                f"Failed: {self.failed_count}/{total_count} ({(self.failed_count/total_count)*100:.2f}%)"
            )
            console.print()

    def render_one_row(self, table, columns, result, turn_index, turn_result):
        succeeded = turn_result["succeeded"]
        # TODO: reinstate the cost calculation logic.
        # cost = (
        #     turn_result["stages"]["assess"] if succeeded else None # TODO: configurable
        # )
        cost = turn_index % 2  # Dummy cost for demonstration purposes

        if succeeded:
            self.complete_count += 1
            if cost == 0:
                self.passed_count += 1
            else:
                self.failed_count += 1
        else:
            self.error_count += 1

        # complete = (
        #     Text("COMPLETE", style="bold green")
        #     if succeeded
        #     else Text("ERROR", style="bold red")
        # )
        # TODO: reinstate the cost calculation logic.
        # cost_text = "" if cost == None else f"{cost:.2f}"
        # score = (
        #     Text(cost_text, style="bold green")
        #     if cost == 0
        #     else Text(cost_text, style="bold red")
        # )
        # keywords = (
        #     ", ".join(sorted(result["case"]["keywords"]))
        #     if "keywords" in result["case"]
        #     else ""
        # )
        # user = turn_result["case"]["turns"][index]["user"]   # TODO: configurable
        # row = [f"{short_id(uuid)}.{turn_index:02}", complete]
        # for col in self._summarizer_spec.columns:
        #     row.append(col.contents(result, turn_index))
        row = [col.contents(result, turn_index) for col in columns]
        table.add_row(*row)
        # table.add_row(
        #     f"{short_id(uuid)}.{index:02}",
        #     complete,
        #     # TODO: reinstate
        #     # score,
        #     # keywords,
        #     # user
        # )
