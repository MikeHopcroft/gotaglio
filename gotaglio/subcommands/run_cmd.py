import asyncio
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn

from ..constants import app_configuration
from ..director import Director
from ..director2 import Director2
from ..pipeline_spec import PipelineSpecs
from ..shared import (
    log_file_name_from_prefix,
    parse_key_value_args,
    read_data_file,
    read_json_file,
)

def run_pipeline2(pipeline_specs: PipelineSpecs, args):
    cases_file = args.cases
    pipeline_name = args.pipeline
    flat_config_patch = parse_key_value_args(args.key_values)
    concurrency = args.concurrency or app_configuration["default_concurrancy"]

    pipeline_spec = pipeline_specs.get(pipeline_name)

    cases = read_data_file(cases_file, False, False)

    director = Director2(pipeline_spec, cases, None, flat_config_patch, concurrency)
    print(f"Run configuration")
    print(f"  id: {director._id}")
    print(f"  cases: {cases_file}")
    print(f"  pipeline: {pipeline_name}")
    diff = director.diff_configs()
    lines = [f"    {k}: {v1} => {v2}" for k, v1, v2 in diff]
    print("\n".join(lines))
    print(f"  concurrancy: {concurrency}")
    print("")

    run_with_progress_bar(director)

    director.write()
    director.summarize()


def rerun_pipeline2(pipeline_specs: PipelineSpecs, args):
    original_id = args.id
    log_file_name = log_file_name_from_prefix(original_id)
    log = read_json_file(log_file_name, False)
    metadata = log["metadata"]

    concurrency = args.concurrency or app_configuration["default_concurrancy"]

    cases = [record["case"] for record in log["results"]]
    if "pipeline" not in metadata:
        raise Exception("No pipeline metadata found in results file")

    pipeline_name = metadata["pipeline"]["name"]
    pipeline_spec = pipeline_specs.get(pipeline_name)

    replacement_config = metadata["pipeline"]["config"]
    flat_config_patch = parse_key_value_args(args.key_values)

    director = Director2(
        pipeline_spec,
        cases,
        replacement_config,
        flat_config_patch,
        concurrency,
    )

    print(f"Rerun configuration")
    print(f"  based on: {log["uuid"]}")
    print(f"  id: {director._id}")
    print(f"  cases: {log_file_name}")
    print(f"  pipeline: {pipeline_name}")
    diff = director.diff_configs()
    lines = [f"    {k}: {v1} => {v2}" for k, v1, v2 in diff]
    print("\n".join(lines))
    print(f"  concurrancy: {concurrency}")
    print("")

    run_with_progress_bar(director)

    director.write()
    director.summarize()


def run_pipeline(registry_factory, args):
    cases_file = args.cases
    pipeline_name = args.pipeline
    flat_config_patch = parse_key_value_args(args.key_values)
    concurrency = args.concurrency or app_configuration["default_concurrancy"]

    cases = read_json_file(cases_file, False)

    director = Director(
        registry_factory,
        pipeline_name,
        cases,
        None,
        flat_config_patch,
        concurrency,
    )

    print(f"Run configuration")
    print(f"  id: {director._id}")
    print(f"  cases: {cases_file}")
    print(f"  pipeline: {pipeline_name}")
    diff = director._pipeline.diff_configs()
    lines = [f"    {k}: {v1} => {v2}" for k, v1, v2 in diff]
    print("\n".join(lines))
    print(f"  concurrancy: {concurrency}")
    print("")

    run_with_progress_bar(director)

    director.write_results()
    director.summarize_results()


def rerun_pipeline(registry_factory, args):
    original_id = args.id
    log_file_name = log_file_name_from_prefix(original_id)
    log = read_json_file(log_file_name, False)
    metadata = log["metadata"]

    concurrency = args.concurrency or app_configuration["default_concurrancy"]

    cases = [record["case"] for record in log["results"]]
    if "pipeline" not in metadata:
        raise Exception("No pipeline metadata found in results file")

    pipeline_name = metadata["pipeline"]["name"]
    replacement_config = metadata["pipeline"]["config"]
    flat_config_patch = parse_key_value_args(args.key_values)

    director = Director(
        registry_factory,
        pipeline_name,
        cases,
        replacement_config,
        flat_config_patch,
        concurrency,
    )

    print(f"Rerun configuration")
    print(f"  based on: {log["uuid"]}")
    print(f"  id: {director._id}")
    print(f"  cases: {log_file_name}")
    print(f"  pipeline: {pipeline_name}")
    diff = director._pipeline.diff_configs()
    lines = [f"    {k}: {v1} => {v2}" for k, v1, v2 in diff]
    print("\n".join(lines))
    print(f"  concurrancy: {concurrency}")
    print("")

    run_with_progress_bar(director)

    director.write_results()
    director.summarize_results()


def run_with_progress_bar(
    director,
):
    with Progress(
        SpinnerColumn(),
        *Progress.get_default_columns(),
        TimeElapsedColumn(),
        transient=True,
    ) as progress:
        task1 = progress.add_task("[red]Processing...", total=len(director._cases))

        def completed():
            progress.update(task1, advance=1)

        asyncio.run(director.process_all_cases(progress, completed))
        progress.update(task1, visible=False)
