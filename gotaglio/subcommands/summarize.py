import os

from ..constants import app_configuration
from ..make_console import MakeConsole
from ..pipeline_spec import PipelineSpecs
from ..shared import log_file_name_from_prefix, read_data_file, read_json_file
from ..summarize import summarize as summarizer


def summarize2(pipeline_spec: PipelineSpecs, args):
    log_folder = app_configuration["log_folder"]
    if not os.path.exists(log_folder):
        print(f"No log folder '{log_folder}'.")
        return

    prefix = args.prefix
    results = read_data_file(log_file_name_from_prefix(prefix), False, False)

    pipeline_name = results["metadata"]["pipeline"]["name"]
    spec = pipeline_spec.get(pipeline_name)
    
    console = MakeConsole()
    summarizer(spec.passed_predicate, spec.summarize, spec.turns, console, results)
    console.render()

def summarize(registry_factory, args):
    log_folder = app_configuration["log_folder"]
    if not os.path.exists(log_folder):
        print(f"No log folder '{log_folder}'.")
        return

    prefix = args.prefix
    results = read_json_file(log_file_name_from_prefix(prefix))

    registry = registry_factory()
    registry.summarize(results)
