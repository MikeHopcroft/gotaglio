import asyncio
from datetime import datetime, timedelta, timezone
import sys
import traceback
from typing import Callable
import uuid

from .basic_types import Case, Configuration
from .git_ops import get_current_edits, get_git_sha
from .helpers import IdShortener
from .pipeline import Pipeline, process_one_case
from .pipeline_spec import PipelineSpec
from .registry import register_models, Registry
from .shared import write_json_file

# Director responsibilities:
#  - build pipeline from spec. This causes the dag to get built inside the pipeline.
#  - record metadata about the run (start time, command line, sha, edits, etc)
#  - manage concurrency in processing a list of cases
#  - calls out to global process_one_case() function to process each case
#  - ensure routing of progress() and completed() callbacks
#  - diff configs
#
# Global process_one_case() responsibilities:
#  - call completed() callback when done
#  - call run_dag()
#
# run_dag() responsibilities:
#  - run the dag for all turns
#
# PROPOSAL: partial_run_dag() takes dag0, which is used for all but the
# final turn, and dag1 which is used for the final turn. Helper function takes
# a complete DAG and replaces stage coroutines with nop() coroutines
# as needed to create dag0 and dag1. Now type of turn can be number instead
# of number | None, since it must always be specified, even for cases that
# don't use turns.
#
# ASSUMPTION: rerunning all of the n-1 prepare steps is preferred to just
# running the nth prepare step in isolation.
#
# BENEFIT: could we remove concept of isolated turns? How would prepare know?
# Could have pipeline's preview() method set LinkedTurns (or whatever other 
# mechanism it wants) to indicate that prepare should be using expected carts. 
#
# Could also supply a different coroutine for the infer() steps before the
# final turn.

class Director:
    def __init__(
        self,
        pipeline_spec: PipelineSpec,
        replacement_config: Configuration | None,
        flat_config_patch: Configuration,
        max_concurrency: int,
    ):
        self._start = datetime.now().timestamp()
        self._spec = pipeline_spec
        self._concurrency = max_concurrency

        registry = Registry()
        register_models(registry)

        self._pipeline = Pipeline(
            pipeline_spec, replacement_config, flat_config_patch, registry
        )
        self._dag = self._pipeline.get_dag()

        self._metadata = {
            "command": " ".join(sys.argv),
            "start": str(datetime.fromtimestamp(self._start, timezone.utc)),
            "concurrency": self._concurrency,
            "pipeline": {
                "name": pipeline_spec.name,
                "config": self._pipeline.get_config(),
            },
        }

        sha = get_git_sha()
        edits = get_current_edits() if sha else None
        if sha:
            self._metadata["sha"] = sha
        if edits:
            self._metadata["edits"] = edits

    async def process_all_cases(self, cases, progress, completed):
        # TODO: validation should be done when cases are loaded.
        validate_cases(cases)
        id = uuid.uuid4()
        runlog = {
            "results": {},
            "metadata": self._metadata.copy(),
            "uuid": str(id),
        }

        try:
            #
            # Perform the run
            #
            semaphore = asyncio.Semaphore(self._concurrency)

            async def sem_task(case):
                async with semaphore:
                    return await self.process_one_case(case, completed)

            tasks = [sem_task(case) for case in cases]
            results = await asyncio.gather(*tasks)

            #
            # Gather and record post-run metadata
            #
            end = datetime.now().timestamp()
            elapsed = end - self._start
            runlog["metadata"]["end"] = str(datetime.fromtimestamp(end, timezone.utc))
            runlog["metadata"]["elapsed"] = str(timedelta(seconds=elapsed))
            runlog["results"] = results

        except Exception as e:
            runlog["metadata"]["exception"] = {
                "message": str(e),
                "traceback": traceback.format_exc(),
                "time": str(datetime.now(timezone.utc)),
            }
        finally:
            # TODO: This is a temporary fix to get around the fact that the progress bar doesn't
            # disappear when the task is completed. It just stops updating.
            if progress:
                progress.stop()
            return runlog

    async def process_one_case(
        self,
        case: Case,
        completed: Callable | None = None,
        turn: int | None = None,
    ):
        result = await process_one_case(case, self._dag, completed, turn)
        return result

    def diff_configs(self):
        return self._pipeline.diff_configs()


# TODO: consider pydantic validation of cases
# TODO: validation should be done by users of Director
def validate_cases(cases):
    if not isinstance(cases, list):
        raise ValueError("Cases must be a list.")

    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"Case {index} not a dictionary.")
        if "uuid" not in case:
            raise ValueError(f"Case {index} missing uuid.")

    # Instantiate the IdShortener to validate uuid text and check for duplicates.
    IdShortener([case["uuid"] for case in cases])
