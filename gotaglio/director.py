import asyncio
from datetime import datetime, timedelta, timezone
from time import perf_counter
import json
import os
import re
import sys
import traceback
import uuid

from .constants import app_configuration
from .dag import build_dag_from_spec, dag_spec_from_linear, run_dag
from .exceptions import ExceptionContext
from .git_ops import get_current_edits, get_git_sha
from .helpers import IdShortener
from .make_console import MakeConsole
from .shared import write_json_file


class Director:
    def __init__(
        self,
        registry_factory,
        pipeline_name,
        cases,
        replacement_config,
        flat_config_patch,
        max_concurrancy,
    ):
        # Wall-clock start for human-readable timestamps
        self._start_wall = datetime.now(timezone.utc)
        # Monotonic start for accurate elapsed timing
        self._start_perf = perf_counter()
        self._concurrancy = max_concurrancy
        self._pipeline_name = pipeline_name

        registry = registry_factory()
        pipeline_factory = registry.pipeline(pipeline_name)
        self._pipeline = pipeline_factory(
            registry, replacement_config, flat_config_patch
        )

        stages = self._pipeline.stages()
        spec = dag_spec_from_linear(stages) if isinstance(stages, dict) else stages
        self._dag = build_dag_from_spec(spec)

        self._config = self._pipeline.config()

        self._id = uuid.uuid4()
        self._output_file = os.path.join(
            app_configuration["log_folder"], f"{self._id}.json"
        )

        self._metadata = {
            "command": " ".join(sys.argv),
            # Record wall-clock timestamps (UTC) for readability
            "start": str(self._start_wall),
            "concurrency": self._concurrancy,
            "pipeline": {"name": pipeline_name, "config": self._pipeline._config},
        }
        self._results = {
            "results": {},
            "metadata": self._metadata,
            "uuid": str(self._id),
        }

        sha = get_git_sha()
        edits = get_current_edits() if sha else None
        if sha:
            self._metadata["sha"] = sha
        if edits:
            self._metadata["edits"] = edits

        validate_cases(cases)
        self._cases = cases

    async def process_all_cases(self, progress, completed):
        try:
            #
            # Perform the run
            #
            semaphore = asyncio.Semaphore(self._concurrancy)

            async def sem_task(case):
                async with semaphore:
                    return await process_one_case(case, self._dag, completed)

            tasks = [sem_task(case) for case in self._cases]
            results = await asyncio.gather(*tasks)

            #
            # Gather and record post-run metadata
            #
            end_wall = datetime.now(timezone.utc)
            elapsed = perf_counter() - self._start_perf
            self._metadata["end"] = str(end_wall)
            self._metadata["elapsed"] = str(timedelta(seconds=elapsed))
            self._results["results"] = results

        except Exception as e:
            self._metadata["exception"] = {
                "message": str(e),
                "traceback": traceback.format_exc(),
                "time": str(datetime.now(timezone.utc)),
            }
        finally:
            # TODO: This is a temporary fix to get around the fact that the progress bar doesn't
            # disappear when the task is completed. It just stops updating.
            if progress:
                progress.stop()
            return self._results

    def write_results(self):
        # Write log
        log_folder = app_configuration["log_folder"]
        if not os.path.exists(log_folder):
            os.makedirs(log_folder)
        write_json_file(self._output_file, self._results)
        # with open(self._output_file, "w", encoding="utf-8") as f:
        #     json.dump(self._results, f, indent=2, ensure_ascii=False)

        print(f"Results written to {self._output_file}")
        return {"log": self._output_file, "results": self._results}

    def summarize_results(self):
        # TODO: this is an example of code that doesn't use Registry.summaraize().
        # This is because the pipeline was already created in __init()__
        console = MakeConsole()
        self._pipeline.summarize(console, self._results)
        console.render()
        # print(f"Results written to {self._output_file}")


async def process_one_case(case, dag, completed):
    ExceptionContext.clear_context()
    start_wall = datetime.now(timezone.utc)
    start_perf = perf_counter()
    result = {
        "succeeded": False,
        # Wall-clock timestamps for readability
        "metadata": {"start": str(start_wall)},
        "case": case,
    # Stage return values go here (unchanged contract)
    "stages": {},
    # New: per-stage timing metadata populated by dag.run_task()
    # Format per stage:
    #   stage_metadata[stage_name] = {
    #       "start": iso_utc,
    #       "end": iso_utc,
    #       "elapsed": "HH:MM:SS.ffffff",
    #       "succeeded": bool
    #   }
    "stage_metadata": {},
    }
    try:
        await run_dag(dag, result)
    except Exception as e:
        result["exception"] = {
            "message": ExceptionContext.format_message(e),
            "traceback": traceback.format_exc(),
            "time": str(datetime.now(timezone.utc)),
        }
        return result

    end_wall = datetime.now(timezone.utc)
    if completed:
        completed()
    elapsed = perf_counter() - start_perf
    result["metadata"]["end"] = str(end_wall)
    result["metadata"]["elapsed"] = str(timedelta(seconds=elapsed))
    result["succeeded"] = True
    return result


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
