import asyncio
import nest_asyncio
from typing import Any
import uuid

from .compare import compare
from .constants import app_configuration_values
from .director import Director
from .format import format
from .pipeline_spec import PipelineSpec, PipelineSpecs, PipelineSpecs
from .serve import serve
from .shared import (
    apply_patch_in_place,
    read_json_file,
    read_log_file_from_prefix,
    write_log_file,
)
from .summarize import summarize


class Gotaglio:
    """
    Gotaglio is a class that provides methods to manage and manipulate tags.
    """

    # TODO: FIX THIS. Add merging.
    def __init__(
        self, pipeline_specs: list[PipelineSpec], config_patch: dict[str, Any] = {}
    ):
        # For running asyncio in Jupyter
        nest_asyncio.apply()
        self._pipeline_specs = PipelineSpecs(pipeline_specs)
        apply_patch_in_place(app_configuration_values, config_patch)

    def add_ids(self, cases, force=False):
        # TODO: allow either a runlog object or a string id prefix
        add_count = 0
        for case in cases:
            if "uuid" not in case or force:
                case["uuid"] = str(uuid.uuid4())
                add_count += 1
        print(f"Total cases: {len(cases)}")
        print(f"UUIDs added: {add_count}")

    def compare(self, a, b):
        runlog_a = runlog_from_runlog_or_prefix(a)
        runlog_b = runlog_from_runlog_or_prefix(b)
        compare(self._pipeline_specs, runlog_a, runlog_b)

    def format(self, runlog_or_prefix, case_uuid_prefix=None):
        runlog = runlog_from_runlog_or_prefix(runlog_or_prefix)
        pipeline_name = runlog["metadata"]["pipeline"]["name"]
        pipeline_spec = self._pipeline_specs.get(pipeline_name)

        format(pipeline_spec, runlog, case_uuid_prefix)

    def load(self, uuid_prefix):
        return read_log_file_from_prefix(uuid_prefix)

    def rerun(self, runlog_or_prefix, flat_config_patch={}, concurrency=2, save=False):
        runlog = runlog_from_runlog_or_prefix(runlog_or_prefix)
        cases = [record["case"] for record in runlog["results"]]
        metadata = runlog["metadata"]
        if "pipeline" not in metadata:
            raise Exception("No pipeline metadata found in results file")

        pipeline_name = metadata["pipeline"]["name"]
        pipeline_spec = self._pipeline_specs.get(pipeline_name)
        replacement_config = metadata["pipeline"]["config"]

        director = Director(
            pipeline_spec,
            replacement_config,
            flat_config_patch,
            concurrency,
        )

        runlog = asyncio.run(
            director.process_all_cases(cases, ProgressMock(), completed_mock)
        )
        summarize(pipeline_spec, runlog)

        if save:
            write_log_file(runlog, chatty = True)

        return runlog

    def run(
        self,
        pipeline_name,
        cases_or_filename,
        flat_config_patch={},
        concurrency=2,
        save=False,
    ):
        pipeline_spec = self._pipeline_specs.get(pipeline_name)
        cases = cases_from_cases_or_filename(cases_or_filename)
        director = Director(
            pipeline_spec,
            None,
            flat_config_patch,
            concurrency,
        )

        runlog = asyncio.run(
            director.process_all_cases(cases, ProgressMock(), completed_mock)
        )
        summarize(pipeline_spec, runlog)

        if save:
            write_log_file(runlog, chatty = True)

        return runlog

    def save(self, runlog, filename: str | None = None, chatty: bool = False):
        write_log_file(runlog, filename, chatty)

    def serve(
        self,
        pipeline_name: str,
        port: int = 8000
    ):
        pipeline_spec = self._pipeline_specs.get(pipeline_name)
        director = Director(pipeline_spec, None, {}, 1)
        print(f"Serving pipeline '{pipeline_name}' on port {port}")
        
        # Start service
        serve(pipeline_spec, director, port)


    def summarize(self, runlog_or_prefix):
        runlog = runlog_from_runlog_or_prefix(runlog_or_prefix)
        pipeline_name = runlog["metadata"]["pipeline"]["name"]
        pipeline_spec = self._pipeline_specs.get(pipeline_name)
        summarize(pipeline_spec, runlog)


def runlog_from_runlog_or_prefix(runlog_or_prefix):
    if isinstance(runlog_or_prefix, str):
        return read_log_file_from_prefix(runlog_or_prefix)
    return runlog_or_prefix


def cases_from_cases_or_filename(cases_or_filename):
    if isinstance(cases_or_filename, str):
        return read_json_file(cases_or_filename)
    return cases_or_filename


class ProgressMock:
    def stop(self):
        pass


def completed_mock():
    pass


def is_running_in_notebook():
    try:
        from IPython.core.getipython import get_ipython

        ipython = get_ipython()
        if ipython is not None and "IPKernelApp" in ipython.config:
            return True
    except ImportError:
        return False
    return False
