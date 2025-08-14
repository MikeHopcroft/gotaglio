from rich.table import Table
from rich.text import Text
from typing import Any

from .helpers import IdShortener
from .make_console import MakeConsole
from gotaglio.pipeline_spec import PipelineSpec, PipelineSpecs
from .summarize import summarize


def compare(pipeline_specs: PipelineSpecs, a: dict[str, Any], b: dict[str, Any]):
    console_buffer = MakeConsole()
    console = console_buffer("text/plain")

    pipeline_name = a["metadata"]["pipeline"]["name"]
    pipeline_spec = pipeline_specs.get(pipeline_name)

    if a["uuid"] == b["uuid"]:
        print(f"Run ids are the same.\n")
        summarize(pipeline_spec, a)
        return

    if a["metadata"]["pipeline"]["name"] != b["metadata"]["pipeline"]["name"]:
        console.print(
            f"Cannot perform comparison because pipeline names are different: A is '{
                a['metadata']['pipeline']['name']
            }', B is '{
                b['metadata']['pipeline']['name']
            }'"
        )
        return

    a_cases = {result["case"]["uuid"]: result for result in a["results"]}
    b_cases = {result["case"]["uuid"]: result for result in b["results"]}
    a_uuids = set(a_cases.keys())
    b_uuids = set(b_cases.keys())
    both = a_uuids.intersection(b_uuids)
    just_a = a_uuids - b_uuids
    just_b = b_uuids - a_uuids

    console.print(f"Run A: {a["uuid"]}")
    console.print(f"Run B: {b["uuid"]}")
    console.print("")
    console.print(f"{len(just_a)} case{'s' if len(just_a) != 1 else ''} only in A")
    console.print(f"{len(just_b)} case{'s' if len(just_b) != 1 else ''} only in B")
    console.print(f"{len(both)} cases in both A and B")
    console.print("")

    # TODO: handle no results case
    if len(both) == 0:
        console.print("There are no cases to compare.")
        console.print()
        # Fall through to print empty table

    # To make the summary more readable, create a short, unique prefix
    # for each case id.
    short_id = IdShortener(both)

    table = Table(title=f"Comparison of {"A, B"}", show_footer=True)
    table.add_column("id", justify="right", style="cyan", no_wrap=True)
    table.add_column("A", justify="right", style="magenta")
    table.add_column("B", justify="right", style="green")
    table.add_column("keywords", justify="left", style="green")

    rows = []
    pass_count_a = 0
    pass_count_b = 0
    for uuid in both:
        (text_a, order_a) = format_status(pipeline_spec, a_cases[uuid])
        (text_b, order_b) = format_status(pipeline_spec, b_cases[uuid])
        keywords = ", ".join(sorted(a_cases[uuid]["case"].get("keywords", [])))
        if order_a == 0:
            pass_count_a += 1
        if order_b == 0:
            pass_count_b += 1
        rows.append(
            (
                (Text(short_id(uuid)), text_a, text_b, keywords),
                order_b * 4 + order_a,
            )
        )
    rows.sort(key=lambda x: x[1])
    for row in rows:
        table.add_row(*row[0])

    table.columns[0].footer = "Total"
    table.columns[1].footer = Text(
        f"{pass_count_a}/{len(both)} ({(pass_count_a/len(both))*100:.0f}%)"
    )
    table.columns[2].footer = Text(
        f"{pass_count_b}/{len(both)} ({(pass_count_b/len(both))*100:.0f}%)"
    )

    console.print(table)
    console.print()
    console_buffer.render()


def format_status(pipeline_spec: PipelineSpec, result: dict[str, Any]):
    if result["succeeded"]:
        if pipeline_spec.passed_predicate(result):
            return (Text("passed", style="bold green"), 0)
        else:
            return (Text("failed", style="bold red"), 1)
    else:
        return (Text("error", style="bold red"), 2)
