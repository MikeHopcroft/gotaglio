import argparse

from .constants import app_configuration
from .exceptions import ExceptionContext
from .pipeline_spec import PipelineSpec, PipelineSpecs
from .registry import Registry
from .subcommands.add_ids_cmd import add_ids
from .subcommands.compare_cmd import compare_command
from .subcommands.format_cmd import format_command
from .subcommands.help_cmd import show_help
from .subcommands.history_cmd import show_history
from .subcommands.list_models_cmd import list_models
from .subcommands.list_pipelines_cmd import list_pipelines
from .subcommands.run_cmd import rerun_command, run_command
from .subcommands.summarize_cmd import summarize_command


def main(pipelines: list[PipelineSpec]):
    pipeline_specs = PipelineSpecs(pipelines)
 
    # Use create_registry() to delay Registry configuration until we
    # actually need to instantiate a Registry. This avoids Registry
    # instantiation exceptions before argument parsing exceptions.
    def create_registry():
        from .models import register_models
        
        registry = Registry()
        for pipeline in pipelines:
            registry.register_pipeline(pipeline)
        register_models(registry)
        return registry

    #
    # Configure command line parsing.
    #
    parser = argparse.ArgumentParser(
        prog=app_configuration["program_name"],
        description="A tool for managing and running ML pipelines.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # 'add-ids' subcommand
    add_ids_parser = subparsers.add_parser("add-ids", help="Add uuids to a suite")
    add_ids_parser.add_argument("suite", type=str, help="The name of a file with cases")
    add_ids_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force adding UUIDs, even if they already exist",
    )

    # 'compare' subcommand
    compare_parser = subparsers.add_parser(
        "compare", help="Compare two or more label sets"
    )
    compare_parser.add_argument(
        "prefix_a", type=str, help="Filename prefix for run log A"
    )
    compare_parser.add_argument(
        "prefix_b", type=str, help="Filename prefix for run log B"
    )

    # 'help' subcommand
    help_parser = subparsers.add_parser("help", help="Show help for gotaglio commands")
    help_parser.add_argument(
        "subcommand", nargs="?", help="The subcommand to show help for"
    )
    help_parser.add_argument("args", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    # 'history' subcommand
    history_parser = subparsers.add_parser(
        "history", help="Show information about recent runs"
    )

    # 'models' subcommand
    models_parser = subparsers.add_parser("models", help="List available models")

    # 'pipelines' subcommand
    pipelines_parser = subparsers.add_parser(
        "pipelines", help="List available pipelines"
    )

    # 'rerun' subcommand
    rerun_parser = subparsers.add_parser(
        "rerun", help="Rerun an experiment with modifications."
    )
    rerun_parser.add_argument("id", type=str, help="The id of the case to rerun.")
    rerun_parser.add_argument(
        "-c", "--concurrency", type=int, help="Maximum concurrancy for tasks"
    )
    rerun_parser.add_argument(
        "key_values", nargs="*", help="key=value arguments to configure pipeline"
    )

    # 'run' subcommand
    run_parser = subparsers.add_parser("run", help="Run a named pipeline")
    run_parser.add_argument(
        "pipeline", type=str, help="The name of the pipeline to run"
    )
    run_parser.add_argument("cases", type=str, help="The name of a file with cases")
    run_parser.add_argument(
        "-c", "--concurrency", type=int, help="Maximum concurrancy for tasks"
    )
    # key-value arguments are used to override the default pipeline configuration.
    run_parser.add_argument(
        "key_values", nargs="*", help="key=value arguments to configure pipeline"
    )

    # 'format' subcommand
    format_parser = subparsers.add_parser("format", help="Pretty print a run")
    format_parser.add_argument(
        "prefix", type=str, help="Filename prefix for run log (or 'latest')"
    )
    format_parser.add_argument(
        "case_id_prefix",
        type=str,
        nargs="?",
        help="Optional case id prefix to show a single case",
    )

    # 'summarize' subcommand
    summarize_parser = subparsers.add_parser("summarize", help="Summarize a run")
    summarize_parser.add_argument(
        "prefix", type=str, help="Filename prefix for run log (or 'latest')"
    )

    # Parse arguments
    args = parser.parse_args()

    # Route to the appropriate function based on the command
    try:
        if args.command == "add-ids":
            add_ids(args.suite, args.force)

        elif args.command == "compare":
            compare_command(pipeline_specs, args)

        elif args.command == "help":
            show_help(parser, args)

        elif args.command == "history":
            show_history()

        elif args.command == "models":
            list_models()

        elif args.command == "pipelines":
            list_pipelines(pipeline_specs)

        elif args.command == "rerun":
            rerun_command(pipeline_specs, args)

        elif args.command == "run":
            run_command(pipeline_specs, args)

        elif args.command == "format":
            format_command(pipeline_specs, args)

        elif args.command == "summarize":
            summarize_command(pipeline_specs, args)

        else:
            parser.print_help()

    except Exception as e:
        print("Top level exception")
        print(ExceptionContext.format_message(e))
