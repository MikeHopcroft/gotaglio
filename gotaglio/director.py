import asyncio
from datetime import datetime, timedelta, timezone
import sys
import traceback
from typing import Any, Callable
import uuid

from .constants import AUDIO_INPUT_MODEL_TYPES
from .git_ops import get_current_edits, get_git_sha
from .helpers import IdShortener
from .models import register_models
from .pipeline import Pipeline, process_one_case
from .pipeline_spec import PipelineSpec
from .registry import Registry


class Director:
    def __init__(
        self,
        pipeline_spec: PipelineSpec,
        replacement_config: dict[str, Any] | None,
        flat_config_patch: dict[str, Any],
        max_concurrency: int,
    ):
        self._start = datetime.now().timestamp()
        self._spec = pipeline_spec
        self._concurrency = max_concurrency

        # Build a registry and register configured models
        registry = Registry()
        register_models(registry)
        self._registry = registry

        # Create pipeline bound to this registry and compute its DAG
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
        # Validate audio cases against configured model capability
        self._validate_audio_cases_against_model(cases)
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
        case: dict[str, Any],
        completed: Callable | None = None,
        turn: int | None = None,
    ):
        return await process_one_case(case, self._dag, completed, turn)

    def diff_configs(self):
        return self._pipeline.diff_configs()

    def _validate_audio_cases_against_model(self, cases):
        """
        If any case includes an 'audio' attribute, ensure the configured model
        supports direct audio input based on model type allowlist.
        """
        try:
            # Determine configured model name and type
            config = self._pipeline.get_config()
            from glom import glom

            model_name = glom(config, "infer.model.name", default=None)
            if not model_name:
                # If no model configured, let existing validation/error paths handle it.
                return

            model = self._registry.model(model_name)
            # Prefer metadata() to read the model's declared type
            md = {}
            try:
                md = model.metadata() or {}
            except Exception:
                md = {}
            model_type = md.get("type")

            # Detect presence of any audio cases
            has_audio_case = any(isinstance(c, dict) and ("audio" in c) for c in cases)
            if not has_audio_case:
                return

            # If we cannot determine the model type, fail conservatively with a clear message
            if not model_type:
                raise ValueError(
                    f"Audio case requires an audio-capable model, but configured model '{model_name}' does not expose a type in metadata()."
                )

            if model_type not in AUDIO_INPUT_MODEL_TYPES:
                allowed = ", ".join(sorted(AUDIO_INPUT_MODEL_TYPES)) or "<none>"
                raise ValueError(
                    f"Audio case requires an audio-capable model. Configured model '{model_name}' (type '{model_type}') is not in allowed types: {allowed}."
                )
        except Exception:
            # Re-raise to surface cleanly to the caller; ExceptionContext upstream will format
            raise


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