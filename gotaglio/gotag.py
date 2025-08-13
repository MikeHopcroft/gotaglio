import asyncio
import nest_asyncio
from typing import Any
import uuid

from .constants import app_configuration_values
from .director import Director
from .director2 import Director2
from .format import format
from .make_console import MakeConsole
from .pipeline_spec import PipelineSpec, PipelineSpecs, PipelineSpecs
from .shared import apply_patch_in_place, read_json_file, read_log_file_from_prefix
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
        registry = self._registry_factory()
        registry.compare(runlog_a, runlog_b)

    def format(self, runlog_or_prefix, case_uuid_prefix=None):
        runlog = runlog_from_runlog_or_prefix(runlog_or_prefix)
        pipeline_name = runlog["metadata"]["pipeline"]["name"]
        pipeline_spec = self._pipeline_specs.get(pipeline_name)

        console = MakeConsole()
        format(pipeline_spec, console, runlog, case_uuid_prefix)
        console.render()

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

        director = Director2(
            pipeline_spec,
            cases,
            replacement_config,
            flat_config_patch,
            concurrency,
        )

        asyncio.run(director.process_all_cases(ProgressMock(), completed_mock))
        director.summarize()

        if save:
            director.write()

        return director._results

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
        director = Director2(
            pipeline_spec,
            cases,
            None,
            flat_config_patch,
            concurrency,
        )

        asyncio.run(director.process_all_cases(ProgressMock(), completed_mock))
        director.summarize()

        if save:
            director.write()

        return director._results

    def save(self, runlog, filename=None):
        # TODO: implement
        pass

    def summarize(self, runlog_or_prefix):
        runlog = runlog_from_runlog_or_prefix(runlog_or_prefix)
        pipeline_name = runlog["metadata"]["pipeline"]["name"]
        pipeline_spec = self._pipeline_specs.get(pipeline_name)
        console = MakeConsole()
        summarize(pipeline_spec, console, runlog)
        console.render()


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
        from IPython import get_ipython

        if "IPKernelApp" in get_ipython().config:
            return True
    except ImportError:
        return False
    return False
