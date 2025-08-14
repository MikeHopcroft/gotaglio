import os

from ..compare import compare
from ..constants import app_configuration
from ..pipeline_spec import PipelineSpecs
from ..shared import read_json_file, log_file_name_from_prefix


def compare_command(pipeline_specs: PipelineSpecs, args):
    log_folder = app_configuration["log_folder"]
    if not os.path.exists(log_folder):
        print(f"No log folder '{log_folder}'.")
        return

    prefix_a = args.prefix_a
    results_a = read_json_file(log_file_name_from_prefix(prefix_a))

    prefix_b = args.prefix_b
    results_b = read_json_file(log_file_name_from_prefix(prefix_b))

    compare(pipeline_specs, results_a, results_b)

