import asyncio
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
import time
import traceback
from typing import Any, Awaitable, Callable, List

from .exceptions import ExceptionContext

StageCoroutine = Callable[[dict[str, Any], int, bool], Awaitable[dict[str, Any]]]

@dataclass
class DagNodeSpec:
    name: str
    function: StageCoroutine
    inputs: List[str]


@dataclass
class DagNode:
    function: StageCoroutine
    inputs: List[str]
    outputs: List[str]
    visited: bool
    live: bool

    def __init__(
        self,
        function: StageCoroutine,
        inputs: List[str],
    ):
        self.function = function
        self.inputs = inputs
        self.outputs = []
        self.visited = False
        self.live = False
        # Additional custom logic here
        if not callable(self.function):
            raise ValueError("function must be callable")


class Dag:
    @classmethod
    def from_linear(cls, stages: dict[str, StageCoroutine], uses_turns: bool = False):
        spec = [DagNodeSpec(name=k, function=v, inputs=[]) for k, v in stages.items()]
        for i in range(1, len(spec)):
            spec[i].inputs = [spec[i - 1].name]
        return cls(spec, uses_turns)

    @classmethod
    def from_spec(cls, spec: List[DagNodeSpec], uses_turns: bool = False):
        return cls(spec, uses_turns)

    def __init__(self, spec: List[DagNodeSpec], uses_turns: bool = False):
        self.uses_turns = uses_turns
        # Create basic DAG with input links.
        if len(spec) == 0:
            raise ValueError("Empty graph specication")
        dag: dict[str, DagNode] = {}
        for node in spec:
            if node.name in dag:
                raise ValueError(f"Duplicate node name '{node.name}'")
            dag[node.name] = DagNode(node.function, node.inputs)

        # Add output links for use by run_dag().
        for k, dest in dag.items():
            unique_inputs = set()
            for input in dest.inputs:
                if input in unique_inputs:
                    raise ValueError(f"Node {k}: duplicate input '{input}'")
                if input not in dag:
                    raise ValueError(f"Node {k}: cannot find input '{input}'")
                unique_inputs.add(input)
                src = dag[input]
                src.outputs.append(k)

        # Check for cycles
        roots = [k for k, v in dag.items() if not v.inputs]
        if not roots:
            raise ValueError(
                "No nodes ready to run. At least one node must have no inputs."
            )
        for root in roots:
            check_for_cycles(dag, root, [])

        # Check for unreachable nodes
        if any(not v.visited for v in dag.values()):
            names = [k for k, v in dag.items() if not v.visited]
            raise ValueError(f"The following nodes are unreachable: {', '.join(names)}")

        self.dag = dag


def check_for_cycles(dag: dict[str, DagNode], node: str, path: list[str]):
    if dag[node].visited:
        if dag[node].live:
            raise ValueError(f"Cycle detected: {' -> '.join(path)} -> {node}")
        return
    dag[node].visited = True
    dag[node].live = True
    for output in dag[node].outputs:
        check_for_cycles(dag, output, path + [node])
    dag[node].live = False


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


def make_task(
    name: str,
    dag,
    stages: dict[str, Any],
    timing: dict[str, Any],
    context: dict[str, Any],
    turn_index: int,
    isolated: bool,
):
    return asyncio.create_task(
        run_task(name, dag, stages, timing, context, turn_index, isolated)
    )


# TODO: use semaphore to limit concurrency at the task level. Plumb all the way through.
async def run_task(
    name: str,
    dag: dict[str, DagNode],
    stages: dict[str, Any],
    timing: dict[str, Any],
    context: dict[str, Any],
    turn_index: int,
    isolated: bool,
):
    if name in stages:
        raise ValueError(f"Internal error: node `stages.{name}` already in context")
    if name in timing:
        raise ValueError(
            f"Internal error: node `metadata.stages.{name}` already in context"
        )

    succeeded = False
    timer = Timer()

    try:
        result = await dag[name].function(context, turn_index, isolated)
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
            if turn_index is not None:
                raise ValueError("Turn index not allowed for cases without turns.")
            timing = {}
            context["metadata"]["stages"] = timing
            stages = {}
            context["stages"] = stages
            await run_dag_helper(dag_object, stages, timing, context, 0, False)
            succeeded = True
        else:
            turn_count = len(turns)
            context["turns"] = []
            if turn_index is None:
                # Process all turns in order.
                for index in range(turn_count):
                    await run_turn(dag_object, context, index, False)
            else:
                # Partial run of a single, isolated turn.
                if turn_index >= len(turns) or turn_index < 0:
                    raise IndexError(
                        f"Turn index {turn_index} is out of range for available turns."
                    )
                await run_turn(dag_object, context, turn_index, True)

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
    dag_object: Dag, context: dict[str, Any], turn_index: int, isolated: bool
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
        await run_dag_helper(dag_object, stages, timing, context, turn_index, isolated)
        succeeded = True
    # except Exception as e:
    #     turn["exception"] = {
    #         "message": ExceptionContext.format_message(e),
    #         "traceback": traceback.format_exc(),
    #         "time": str(datetime.now(timezone.utc)),
    #     }
    #     # Stop processing turns after an error.
    #     return
    finally:
        turn.update(timer.get_times())
        turn["succeeded"] = succeeded


async def run_dag_helper(
    dag_object: Dag,
    stages: dict[str, Any],
    timing: dict[str, Any],
    context: dict[str, Any],
    turn_index: int,
    isolated: bool,
):
    dag = dag_object.dag

    # DESIGN NOTE: the dict of unfulfilled dependencies is stored per-run,
    # instead of in the DAG to allow for multiple concurrent runs of the same
    # DAG with different contexts.
    dependencies = {k: set(v.inputs) for k, v in dag.items()}

    ready = [k for k in dag.keys() if not dependencies[k]]
    waiting = [k for k in dag.keys() if dependencies[k]]

    if len(ready) == 0:
        raise ValueError(
            "Internal error: no nodes ready to run. At least one node must have no inputs."
        )

    # TODO: consider using TaskGroup here to ensure proper task
    # cleanup after exceptions.

    # Create a list of tasks for the ready nodes
    tasks = [
        make_task(name, dag, stages, timing, context, turn_index, isolated)
        for name in ready
    ]

    while tasks:
        # Wait for any of the tasks to complete
        done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        # Process the completed tasks
        for task in done:
            name = task.result()

            # Propagate the outputs to subsequent stages.
            node = dag[name]
            for output in node.outputs:
                dependencies[output].remove(name)
                if not dependencies[output]:
                    waiting.remove(output)
                    tasks.add(
                        make_task(
                            output, dag, stages, timing, context, turn_index, isolated
                        )
                    )

    if waiting:
        raise ValueError("Internal error: some nodes are still waiting to run")
