import asyncio
from datetime import datetime, time, timedelta, timezone
import time
import traceback
from typing import Any, List

from .exceptions import ExceptionContext


class Dag:
    @classmethod
    def from_linear(cls, stages: dict[str, Any], uses_turns: bool = False):
        spec = [{"name": k, "function": v, "inputs": []} for k, v in stages.items()]
        for i in range(1, len(spec)):
            spec[i]["inputs"] = [spec[i - 1]["name"]]
        return cls(spec, uses_turns)

    @classmethod
    def from_spec(cls, spec: List[dict[str, Any]], uses_turns: bool = False):
        return cls(spec, uses_turns)

    def __init__(self, spec: List[dict[str, Any]], uses_turns: bool = False):
        self.uses_turns = uses_turns
        # Create basic DAG with input links.
        if len(spec) == 0:
            raise ValueError("Empty graph specication")
        dag = {}
        for node in spec:
            if node["name"] in dag:
                raise ValueError(f"Duplicate node name '{node['name']}'")
            dag[node["name"]] = {
                "function": node["function"],
                "inputs": node["inputs"],
                "outputs": [],
                "visited": False,
                "live": False,
            }

        # Add output links for use by run_dag().
        for k, dest in dag.items():
            unique_inputs = set()
            for input in dest["inputs"]:
                if input in unique_inputs:
                    raise ValueError(f"Node {k}: duplicate input '{input}'")
                if input not in dag:
                    raise ValueError(f"Node {k}: cannot find input '{input}'")
                unique_inputs.add(input)
                src = dag[input]
                src["outputs"].append(k)

        # Check for cycles
        roots = [k for k, v in dag.items() if not v["inputs"]]
        if not roots:
            raise ValueError(
                "No nodes ready to run. At least one node must have no inputs."
            )
        for root in roots:
            check_for_cycles(dag, root, [])

        # Check for unreachable nodes
        if any(not v["visited"] for v in dag.values()):
            names = [k for k, v in dag.items() if not v["visited"]]
            raise ValueError(f"The following nodes are unreachable: {', '.join(names)}")

        self.dag = dag


def check_for_cycles(dag, node, path):
    if dag[node]["visited"]:
        if dag[node]["live"]:
            raise ValueError(f"Cycle detected: {' -> '.join(path)} -> {node}")
        return
    dag[node]["visited"] = True
    dag[node]["live"] = True
    for output in dag[node]["outputs"]:
        check_for_cycles(dag, output, path + [node])
    dag[node]["live"] = False


class Timer:
    def __init__(self):
        self._start_time = datetime.now(timezone.utc)
        self._start_counter = time.perf_counter()

    def get_times(self):
        end_counter = time.perf_counter()
        end_time = datetime.now(timezone.utc)
        return {
            "start": str(self._start_time),
            "end": str(end_time),
            "elapsed": str(timedelta(seconds=end_counter - self._start_counter)),
        }


def make_task(dag, name, context, stages, timing):
    return asyncio.create_task(run_task(dag, name, context, stages, timing))


# TODO: use semaphore to limit concurrency at the task level. Plumb all the way through.
async def run_task(dag, name, context, stages, timing):
    if name in stages:
        raise ValueError(f"Internal error: node `stages.{name}` already in context")
    if name in timing:
        raise ValueError(
            f"Internal error: node `metadata.stages.{name}` already in context"
        )

    succeeded = False
    timer = Timer()

    try:
        result = await dag[name]["function"](context)
        stages[name] = result
        succeeded = True
    except Exception as e:
        context["exception"] = {
            "stage": name,
            "message": ExceptionContext.format_message(e),
            "traceback": traceback.format_exc(),
            "time": str(datetime.now(timezone.utc)),
        }
        raise e
    finally:
        timing[name] = {"succeeded": succeeded}
        timing[name].update(timer.get_times())

    return name


async def run_dag(
    dag_object: Dag, case, turn_index: int | None = None
) -> dict[str, Any]:
    # DESIGN NOTE: for readability, set `succeeded` here to keep it as
    # the first property. Contract is that `succeeded` indicates that
    # a run has succeded at some point. Failed runs and runs in progress
    # will both have `succeeded` set to False.
    succeeded = False
    context = {
        "succeeded": succeeded,
        # Also add placeholders for timing information that will be filled in
        # later. Risk here is that class Timer could change the names of these
        # fields.
        "metadata": {
            "start": "",
            "end": "",
            "elapsed": "",
        },
        "case": case,
    }

    turns = case.get("turns", None)
    timer = Timer()

    try:
        if turns is None:
            timing = {}
            context["metadata"]["stages"] = timing
            stages = {}
            context["stages"] = stages
            await run_dag_helper(dag_object, context, stages, timing)
            succeeded = True
        else:
            turn_count = len(turns)
            context["turns"] = []
            if turn_index is not None:
                if turn_index >= len(turns) or turn_index < 0:
                    raise IndexError(
                        f"Turn index {turn_index} is out of range for available turns."
                    )
                turn_count = turn_index + 1
                context["isolated_turn"] = True

            for index in range(turn_count):
                await run_turn(index, dag_object, context, turn_index)
            succeeded = True
    except Exception as e:
        context["exception"] = {
            "message": ExceptionContext.format_message(e),
            "traceback": traceback.format_exc(),
            "time": str(datetime.now(timezone.utc)),
        }

    finally:
        context["succeeded"] = succeeded
        context["metadata"].update(timer.get_times())

    return context


# TODO: Finish up this work-in-progress prototype of a successor to run_dag().
async def partial_run_dag(
    dag0: Dag, dag1: Dag, case: dict[str, Any], turn_index: int
) -> dict[str, Any]:
    # DESIGN NOTE: for readability, set `succeeded` here to keep it as
    # the first property. Contract is that `succeeded` indicates that
    # a run has succeded at some point. Failed runs and runs in progress
    # will both have `succeeded` set to False.
    succeeded = False
    context = {
        "succeeded": succeeded,
        # Also add placeholders for timing information that will be filled in
        # later. Risk here is that class Timer could change the names of these
        # fields.
        "metadata": {
            "start": "",
            "end": "",
            "elapsed": "",
        },
        "case": case,
    }

    turns = case.get("turns", None)
    timer = Timer()

    try:
        if turns is None:
            if turn_index != 0:
                raise IndexError("Turn index must be zero for cases without turns.")
            timing = {}
            context["metadata"]["stages"] = timing
            stages = {}
            context["stages"] = stages
            await run_dag_helper(dag1, context, stages, timing)
            succeeded = True
        else:
            turn_count = len(turns)
            context["turns"] = []

            if turn_index is not None:
                if turn_index >= len(turns) or turn_index < 0:
                    raise IndexError(
                        f"Turn index {turn_index} is out of range for available turns."
                    )
                turn_count = turn_index + 1

            for index in range(turn_count):
                dag = dag0 if index < turn_index else dag1
                await run_turn(index, dag, context, turn_index)
            succeeded = True
    except Exception as e:
        context["exception"] = {
            "message": ExceptionContext.format_message(e),
            "traceback": traceback.format_exc(),
            "time": str(datetime.now(timezone.utc)),
        }

    finally:
        context["succeeded"] = succeeded
        context["metadata"].update(timer.get_times())

    return context


async def run_turn(
    index: int, dag_object, context: dict[str, Any], turn_index: int | None
):
    timer = Timer()
    timing = {}
    metadata = {
        "stages": timing,
    }
    stages = {}
    turn: dict[str, Any] = {
        # DESIGN NOTE: for readability, set `succeeded` here to keep it as
        # the first property. Contract is that `succeeded` indicates that
        # a run has succeded at some point. Failed runs and runs in progress
        # will both have `succeeded` set to False.
        #
        # Also add placeholders for timing information that will be filled in
        # later. Risk here is that class Timer could change the names of these
        # fields.
        "succeeded": False,
        "start": "",
        "end": "",
        "elapsed": "",
        "metadata": metadata,
        "stages": stages,
    }
    # DESIGN NOTE: need to append `turn` here before calling run_dag_helper
    # because contract for stage co-routines is that the current turn number
    # can be determined by len(context["turns"]). Otherwise the creation of
    # `turn` and the append operation would be done in the finally block.
    context["turns"].append(turn)
    succeeded = False

    try:
        # Skip running turn if turn_index limits us to a specific turn.
        if turn_index is None or turn_index == index:
            await run_dag_helper(dag_object, context, stages, timing)
            succeeded = True
    except Exception as e:
        turn["exception"] = {
            "message": ExceptionContext.format_message(e),
            "traceback": traceback.format_exc(),
            "time": str(datetime.now(timezone.utc)),
        }
        # Stop processing turns after an error.
        return
    finally:
        turn.update(timer.get_times())
        turn["succeeded"] = succeeded


async def run_dag_helper(dag_object: Dag, context, stages, timing):
    dag = dag_object.dag

    # DESIGN NOTE: the dict of unfulfilled dependencies is stored per-run,
    # instead of in the DAG to allow for multiple concurrent runs of the same
    # DAG with different contexts.
    dependencies = {k: set(v["inputs"]) for k, v in dag.items()}

    ready = [k for k in dag.keys() if not dependencies[k]]
    waiting = [k for k in dag.keys() if dependencies[k]]

    if len(ready) == 0:
        raise ValueError(
            "Internal error: no nodes ready to run. At least one node must have no inputs."
        )

    # TODO: consider using TaskGroup here to ensure proper task
    # cleanup after exceptions.

    # Create a list of tasks for the ready nodes
    tasks = [make_task(dag, name, context, stages, timing) for name in ready]

    while tasks:
        # Wait for any of the tasks to complete
        done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        # Process the completed tasks
        for task in done:
            name = task.result()

            # Propagate the outputs to subsequent stages.
            node = dag[name]
            for output in node["outputs"]:
                dependencies[output].remove(name)
                if not dependencies[output]:
                    waiting.remove(output)
                    tasks.add(make_task(dag, output, context, stages, timing))

    if waiting:
        raise ValueError("Internal error: some nodes are still waiting to run")
