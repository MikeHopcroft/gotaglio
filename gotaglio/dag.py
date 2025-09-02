import asyncio
from datetime import datetime, timedelta, timezone
from glom import glom
import traceback
from typing import Any, List
import time

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


# TODO: use semaphore to limit concurrency at the task level. Plumb all the way through.
async def run_task(dag, name, context, stage_timing):
    """
    Execute a stage, recording timing under the provided stage_timing dict.

    Timing contract:
    - stage_timing[name] is created immediately with { start }
    - on completion, we add end, elapsed, succeeded
    - on error, succeeded is False and the exception propagates
    """
    start_monotonic = time.perf_counter()
    start_dt = datetime.now(timezone.utc)

    # Ensure the timing container entry exists from the start
    stage_timing[name] = {"start": str(start_dt)}

    succeeded = False
    try:
        result = await dag[name]["function"](context)
        succeeded = True
        return (name, result)
    except Exception as e:
        # Attach exception at the top-level context for visibility
        context["exception"] = {
            "stage": name,
            "message": ExceptionContext.format_message(e),
            "traceback": traceback.format_exc(),
            "time": str(datetime.now(timezone.utc)),
        }
        raise e
    finally:
        end_monotonic = time.perf_counter()
        end_dt = datetime.now(timezone.utc)
        elapsed = end_monotonic - start_monotonic
        # Update the timing info for this stage
        md = stage_timing.get(name, {})
        md.update(
            {
                "end": str(end_dt),
                "elapsed": str(timedelta(seconds=elapsed)),
                "succeeded": succeeded,
            }
        )
        stage_timing[name] = md


def make_task(dag, name, context, stage_timing):
    return asyncio.create_task(run_task(dag, name, context, stage_timing))


async def run_dag(dag_object, context: dict[str, Any], turn_index: int | None = None):
    turns = glom(context, "case.turns", default=None)
    if turns is None:
        # Single-turn run: initialize top-level metadata and timing container
        stages: dict[str, Any] = {}
        context["stages"] = stages

        start = datetime.now().timestamp()
        metadata = {
            "start": str(datetime.fromtimestamp(start, timezone.utc)),
            "stages": {},
        }
        context["metadata"] = metadata

        await run_dag_helper(dag_object, context, stages, metadata["stages"])

        # Record end and elapsed for the overall run
        end = datetime.now().timestamp()
        elapsed = end - start
        metadata["end"] = str(datetime.fromtimestamp(end, timezone.utc))
        metadata["elapsed"] = str(timedelta(seconds=elapsed))
    else:
        turn_count = len(turns)
        context["turns"] = []
        if turn_index is not None:
            if turn_index >= len(turns) or turn_index < 0:
                raise IndexError(f"Turn index {turn_index} is out of range for available turns.")
            turn_count = turn_index + 1
            context["isolated_turn"] = True

        for index in range(turn_count):
            start = datetime.now().timestamp()
            metadata = {
                "start": str(datetime.fromtimestamp(start, timezone.utc)),
                "stages": {},
            }
            stages = {}
            turn = {
                "succeeded": False,
                "metadata": metadata,
                "stages": stages,
            }
            context["turns"].append(turn)

            if turn_index is None or turn_index == index:
                try:
                    await run_dag_helper(dag_object, context, stages, metadata["stages"])
                except Exception as e:
                    turn["exception"] = {
                        "message": ExceptionContext.format_message(e),
                        "traceback": traceback.format_exc(),
                        "time": str(datetime.now(timezone.utc)),
                    }
                    # Stop processing turns after an error.
                    return

            # Record the successful completion of this turn.
            turn["succeeded"] = True
            # TODO: should the following lines be in a finally block?
            end = datetime.now().timestamp()
            elapsed = end - start
            metadata["end"] = str(datetime.fromtimestamp(end, timezone.utc))
            metadata["elapsed"] = str(timedelta(seconds=elapsed))


async def run_dag_helper(dag_object, context, stages, stage_timing):
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
    tasks = [make_task(dag, name, context, stage_timing) for name in ready]

    while tasks:
        # Wait for any of the tasks to complete
        done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        # Process the completed tasks
        for task in done:
            (name, result) = task.result()

            # Record the result of this stage in the context.
            if name in stages:
                raise ValueError(
                    f"Internal error: node `stages.{name}` already in context"
                )
            stages[name] = result

            # Propagate the outputs to subsequent stages.
            node = dag[name]
            for output in node["outputs"]:
                dependencies[output].remove(name)
                if not dependencies[output]:
                    waiting.remove(output)
                    tasks.add(make_task(dag, output, context, stage_timing))

    if waiting:
        raise ValueError("Internal error: some nodes are still waiting to run")
