import asyncio
from datetime import datetime, timedelta, timezone
import time
from glom import glom
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


# TODO: use semaphore to limit concurrency at the task level. Plumb all the way through.
async def run_task(dag, name, context):
    # Resolve per-stage timing container directly in metadata for this run/turn
    if "turns" in context:
        # Multi-turn: current turn is the last one appended
        meta_container = context["turns"][-1].setdefault("metadata", {}).setdefault(
            "stages", {}
        )
    else:
        # Single-turn: store under top-level metadata
        meta_container = context.setdefault("metadata", {}).setdefault("stages", {})

    # Wall-clock start
    start_ts = datetime.now().timestamp()
    start_iso = str(datetime.fromtimestamp(start_ts, timezone.utc))
    # Monotonic start for elapsed computation
    start_perf = time.perf_counter()
    # Pre-populate stage metadata entry
    meta_container.setdefault(name, {})
    meta_container[name]["start"] = start_iso
    try:
        result = await dag[name]["function"](context)
        succeeded = True
        return (name, result)
    except Exception as e:
        # Record exception on context and re-raise so upstream can handle
        context["exception"] = {
            "stage": name,
            "message": ExceptionContext.format_message(e),
            "traceback": traceback.format_exc(),
            "time": str(datetime.now(timezone.utc)),
        }
        succeeded = False
        raise e
    finally:
        # Wall-clock end
        end_ts = datetime.now().timestamp()
        end_iso = str(datetime.fromtimestamp(end_ts, timezone.utc))
        # Monotonic elapsed
        end_perf = time.perf_counter()
        elapsed = str(timedelta(seconds=(end_perf - start_perf)))
        meta = meta_container[name]
        meta["end"] = end_iso
        meta["elapsed"] = elapsed
        meta["succeeded"] = succeeded


def make_task(dag, name, context):
    return asyncio.create_task(run_task(dag, name, context))


async def run_dag(dag_object, context):
    turns = glom(context, "case.turns", default=None)
    if turns is None:
        stages = {}
        context["stages"] = stages
        # Ensure top-level metadata exists for single-turn timing
        context.setdefault("metadata", {}).setdefault("stages", {})
        await run_dag_helper(dag_object, context, stages)
    else:
        context["turns"] = []
        for index in range(len(turns)):
            start = datetime.now().timestamp()
            metadata = {
                "start": str(datetime.fromtimestamp(start, timezone.utc)),
                # Initialize per-stage timing container inside turn metadata immediately
                "stages": {},
            }
            stages = {}
            turn = {
                "succeeded": False,
                "metadata": metadata,
                "stages": stages,
            }
            context["turns"].append(turn)
            try:
                await run_dag_helper(dag_object, context, stages)
            except Exception as e:
                turn["exception"] = {
                    "message": ExceptionContext.format_message(e),
                    "traceback": traceback.format_exc(),
                    "time": str(datetime.now(timezone.utc)),
                }
                # Record end/elapsed even on error
                end = datetime.now().timestamp()
                elapsed = end - start
                metadata["end"] = str(datetime.fromtimestamp(end, timezone.utc))
                metadata["elapsed"] = str(timedelta(seconds=elapsed))
                # Stop processing turns after an error.
                return
            # Record the successful completion of this turn.
            end = datetime.now().timestamp()
            elapsed = end - start
            metadata["end"] = str(datetime.fromtimestamp(end, timezone.utc))
            metadata["elapsed"] = str(timedelta(seconds=elapsed))
            turn["succeeded"] = True


async def run_dag_helper(dag_object, context, stages):
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
    tasks = [make_task(dag, name, context) for name in ready]

    while tasks:
        # Wait for any of the tasks to complete
        done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        # Process the completed tasks
        for task in done:
            (name, result) = task.result()

            # Record the result of this stage in the context (raw).
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
                    tasks.add(make_task(dag, output, context))

    if waiting:
        raise ValueError("Internal error: some nodes are still waiting to run")
