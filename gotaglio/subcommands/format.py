import os

from ..constants import app_configuration
from ..format import format as formatter
from ..make_console import MakeConsole
from ..pipeline_spec import PipelineSpec
from ..shared import log_file_name_from_prefix, read_data_file, read_json_file


def format2(pipeline_spec: list[PipelineSpec], args):
    log_folder = app_configuration["log_folder"]
    if not os.path.exists(log_folder):
        print(f"No log folder '{log_folder}'.")
        return

    prefix = args.prefix
    case_uuid_prefix = args.case_id_prefix
    results = read_data_file(log_file_name_from_prefix(prefix), False, False)

    pipeline_name = results["metadata"]["pipeline"]["name"]
    pipeline_config = results["metadata"]["pipeline"]["config"]
    spec = next((s for s in pipeline_spec if s.name == pipeline_name), None)
    if spec is None:
        raise ValueError(f"Cannot fine pipeline '{pipeline_name}'.")
    
    console = MakeConsole()
    formatter(spec.format, spec.turns, console, results, case_uuid_prefix)
    console.render()


def format(registry_factory, args):
    log_folder = app_configuration["log_folder"]
    if not os.path.exists(log_folder):
        print(f"No log folder '{log_folder}'.")
        return

    prefix = args.prefix
    case_uuid_prefix = args.case_id_prefix
    results = read_json_file(log_file_name_from_prefix(prefix))

    registry = registry_factory()
    registry.format(results, case_uuid_prefix)
