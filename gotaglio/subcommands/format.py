import os

from ..constants import app_configuration
from ..format import format
from ..make_console import MakeConsole
from ..pipeline_spec import PipelineSpecs
from ..shared import log_file_name_from_prefix, read_data_file, read_json_file


def format_command(pipeline_specs: PipelineSpecs, args):
    log_folder = app_configuration["log_folder"]
    if not os.path.exists(log_folder):
        print(f"No log folder '{log_folder}'.")
        return

    prefix = args.prefix
    case_uuid_prefix = args.case_id_prefix
    results = read_data_file(log_file_name_from_prefix(prefix), False, False)

    pipeline_name = results["metadata"]["pipeline"]["name"]
    spec = pipeline_specs.get(pipeline_name)
    
    console = MakeConsole()
    format(spec, console, results, case_uuid_prefix)
    console.render()


