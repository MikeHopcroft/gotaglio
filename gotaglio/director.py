import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
import re
import sys
import traceback
import uuid

from .constants import log_folder
from .dag import build_dag_from_spec, dag_spec_from_linear, run_dag
from .exceptions import ExceptionContext
from .git import get_current_edits, get_git_sha


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
        self._start = datetime.now().timestamp()
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

        # self._stages = self._pipeline.stages()
        self._config = self._pipeline.config()

        self._id = uuid.uuid4()
        self._output_file = os.path.join(log_folder, f"{self._id}.json")

        self._metadata = {
            "command": " ".join(sys.argv),
            "start": str(datetime.fromtimestamp(self._start, timezone.utc)),
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
            end = datetime.now().timestamp()
            elapsed = end - self._start
            self._metadata["end"] = str(datetime.fromtimestamp(end, timezone.utc))
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
        if not os.path.exists(log_folder):
            os.makedirs(log_folder)
        with open(self._output_file, "w") as f:
            json.dump(self._results, f, indent=2)

        return {"log": self._output_file, "results": self._results}

    def summarize_results(self):
        self._pipeline.summarize(self._results)
        print(f"Results written to {self._output_file}")


async def process_one_case(case, dag, completed):
    ExceptionContext.clear_context()
    start = datetime.now().timestamp()
    result = {
        "succeeded": False,
        "metadata": {"start": str(datetime.fromtimestamp(start, timezone.utc))},
        "case": case,
        "stages": {},
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

    end = datetime.now().timestamp()
    if completed:
        completed()
    elapsed = end - start
    result["metadata"]["end"] = str(datetime.fromtimestamp(end, timezone.utc))
    result["metadata"]["elapsed"] = str(timedelta(seconds=elapsed))
    result["succeeded"] = True
    return result


def validate_cases(cases):
    if not isinstance(cases, list):
        raise ValueError("Cases must be a list.")

    guid_pattern = re.compile(
        r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    )

    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"Case {index} not a dictionary.")
        if "uuid" not in case:
            raise ValueError(f"Case {index} missing uuid.")
        if not guid_pattern.match(case["uuid"]):
            raise ValueError(f"Encountered invalid uuid: {case['uuid']}")

    uuids = set()
    for case in cases:
        if case["uuid"] in uuids:
            raise ValueError(f"Encountered duplicate uuid: {case['uuid']}")
        uuids.add(case["uuid"])
