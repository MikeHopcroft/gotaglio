import asyncio
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
from typing import Any, cast

from ..constants import app_configuration
from ..director import Director
from ..pipeline_spec import PipelineSpecs
from ..shared import (
    log_file_name_from_prefix,
    parse_key_value_args,
    read_data_file,
    read_json_file,
    write_log_file,
)
from ..summarize import summarize


def serve_command(pipeline_specs: PipelineSpecs, args):
    pipeline_name = args.pipeline
    port = args.port
    flat_config_patch = parse_key_value_args(args.key_values)
    concurrency = 1
    pipeline_spec = pipeline_specs.get(pipeline_name)

    director = Director(pipeline_spec, None, flat_config_patch, concurrency)
    print(f"Serve configuration")
    print(f"  port: {port}")
    print(f"  pipeline: {pipeline_name}")
    diff = director.diff_configs()
    lines = [f"    {k}: {v1} => {v2}" for k, v1, v2 in diff]
    print("\n".join(lines))
    print(f"  concurrancy: {concurrency}")
    print("")

