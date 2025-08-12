import argparse

from .constants import app_configuration
from .exceptions import ExceptionContext
from .registry import Registry
from .subcommands.add_ids import add_ids
from .subcommands.compare import compare
from .subcommands.format import format2
from .subcommands.help import show_help
from .subcommands.history import show_history
from .subcommands.list_models import list_models
from .subcommands.list_pipelines import list_pipelines
from .subcommands.run import rerun_pipeline, run_pipeline2
from .subcommands.summarize import summarize2


def main(pipelines):
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
            compare(create_registry, args)

        elif args.command == "help":
            show_help(parser, args)

        elif args.command == "history":
            show_history()

        elif args.command == "models":
            list_models(create_registry)

        elif args.command == "pipelines":
            list_pipelines(create_registry)

        elif args.command == "rerun":
            rerun_pipeline(create_registry, args)

        # elif args.command == "run":
        #     run_pipeline(create_registry, args)
        elif args.command == "run":
            run_pipeline2(pipelines, args)

        elif args.command == "format":
            format2(pipelines, args)

        elif args.command == "summarize":
            summarize2(pipelines, args)

        else:
            parser.print_help()

    except Exception as e:
        print("Top level exception")
        print(ExceptionContext.format_message(e))
