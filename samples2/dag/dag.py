# This module demonstrates the implementation of a directed acyclic graph (DAG)
# pipeline using the gotaglio tools. The DAG consists of 6 nodes, organized as
# follows:
#
#           A    E
#          / \   |
#         B   C  |
#          \ /   |
#           D    |
#             \ /
#              F

import asyncio
import os
from rich.console import Console
from rich.table import Table
from rich.text import Text
import sys

# Add the parent directory to the sys.path so that we can import from the
# gotaglio package, as if it had been installed.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gotaglio.dag import build_dag_from_spec
from gotaglio.main import main
from gotaglio.pipeline_spec import PipelineSpec


###############################################################################
#
# Stage Functions
#
###############################################################################
# The structure of the pipeline is defined by the stages() method.
# This example demonstrates a directed acyclic graph (DAG) pipeline with
# six nodes:
#
#     A    E
#    / \   |
#   B   C  |
#    \ /   |
#     D    |
#       \ /
#        F
#
def stages(name, config, registry):
    # Define the six pipeline node functions.
    # To avoid code duplication, we use a single `work()` function that
    # simulates work by sleeping for a specified amount of time. The `work`
    # function returns a dictionary with the name of the stage, the start
    # time, and the end time.
    async def a(context):
        return await work("A", 0.01)


    async def b(context):
        return await work("B", 0.01)


    async def c(context):
        return await work("C", 0.02)


    async def d(context):
        return await work("B", 0.01)


    async def e(context):
        return await work("E", 0.01)


    async def f(context):
        return await work("F", 0.01)


    # The work() function is used by each stage to simulate work.
    # It uses sequence numbers to record start end end times.
    async def work(name, time):
        start = sequence()
        await asyncio.sleep(time)
        end = sequence()
        return {
            "name": name,
            "start": start,
            "end": end,
        }

    # The sequence() function is used to generate sequence numbers for
    # use by the work function. For the demo, sequence numbers are easier
    # to read than timestamps.
    counter = 0

    def sequence():
        nonlocal counter
        counter += 1
        return counter


    # Finally, return the DAG specification for
    #
    #     A    E
    #    / \   |
    #   B   C  |
    #    \ /   |
    #     D    |
    #       \ /
    #        F
    #       
    spec = [
        {"name": "A", "function": a, "inputs": []},
        {"name": "B", "function": b, "inputs": ["A"]},
        {"name": "C", "function": c, "inputs": ["A"]},
        {"name": "D", "function": d, "inputs": ["B", "C"]},
        {"name": "E", "function": e, "inputs": []},
        {"name": "F", "function": f, "inputs": ["D", "E"]},
    ]

    return build_dag_from_spec(spec)

###############################################################################
#
# Formatter extensions
#
###############################################################################
# A simple format() method that prints out a timeline for each case.
def format(console, runlog):
    results = runlog["results"]
    if len(results) == 0:
        print("No results.")
    else:
        timeline(results[0])

###############################################################################
#
# Summarizer extensions
#
###############################################################################
# For the purposes of this demo we define a very limited summarize() method
# that prints out a timeline for the first case.
def summarize(console, runlog):
    results = runlog["results"]
    if len(results) == 0:
        print("No results.")
    else:
        timeline(results[0])


###############################################################################
#
# Pipeline Specification
#
###############################################################################

dag_pipeline_spec = PipelineSpec(
    # Pipeline name used in `gotag run <pipeline>.`
    name = "dag",
    # Pipeline description shown by `gotag pipelines.`
    description = "An example of a directed acyclic graph (DAG) pipeline.",
    # TODO: configuration values for use by pipeline stages???
    configuration= {},
    create_dag=stages,
    # passed_predicate=lambda result: True,
    formatter=format,
    summarizer=summarize,
    format=format,
)

# class DAGPipeline(Pipeline):
#     # The Pipeline abstract base class requires _name and _description.
#     # These are used by the Registry to list and instantiate pipelines.
#     # The `pipelines` subcommand will print a list of available pipelines,
#     # with their names and descriptions.
#     _name = "dag"
#     _description = "An example of a directed acyclic graph (DAG) pipeline."

#     def __init__(self, registry, replacement_config, flat_config_patch):
#         default_config = {}
#         super().__init__(default_config, replacement_config, flat_config_patch)




#     # For the purposes of this demo we define a very limited summarize() method
#     # that prints out a timeline for the first case.
#     def summarize(self, runlog):
#         results = runlog["results"]
#         if len(results) == 0:
#             print("No results.")
#         else:
#             timeline(results[0])


#     # A simple format() method that prints out a timeline for each case.
#     def format(self, runlog, uuid_prefix):
#         results = runlog["results"]
#         if len(results) == 0:
#             print("No results.")
#         else:
#             for result in results:
#                 if uuid_prefix and not result["case"]["uuid"].startswith(uuid_prefix):
#                     continue
#             timeline(result)


#     def compare(self, a, b):
#         print("Compare not implemented.")


# Helper function that renders the execution timeline as a table.
# Uses the rich Table class to print out a timeline
# of stage execution in the DAG.
def timeline(context):
    stages = context["stages"]
    names = sorted(stages.keys())
    last = max([stage["end"] for stage in stages.values()])

    table = Table(title=f"Timeline for case {context['case']['uuid']}")
    table.add_column("step", justify="right", style="cyan", no_wrap=True)
    for name in names:
        table.add_column(name, justify="center", style="cyan", no_wrap=True)

    for i in range(1, last + 1):
        row = [str(i)]
        for name in names:
            stage = stages[name]
            if stage["start"] <= i <= stage["end"]:
                row.append(Text(" x ", style="green on green"))
            else:
                row.append("")
        table.add_row(*row)

    console = Console()
    console.print(table)


def go():
    main([dag_pipeline_spec])


if __name__ == "__main__":
    go()
