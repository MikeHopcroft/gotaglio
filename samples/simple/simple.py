"""
This module demonstrates the implementation of a simple, linear pipeline
using the gotaglio tools. The pipeline has the following stages:
    - prepare: prepares the system, agent, and user messages for the
               for the model. Uses a jinga2 template to format the system
               message.
    - infer: invokes the model to generate a response.
    - extract: extracts a numerical answer from the model response.
    - assess: compares the model response to the expected answer.

The pipeline also provides implementations the following sub-commnads,
which can be invoked from the command line:
    - summarize: prints a summary of the results.
    - format: pretty prints the each case
    - compare: compares two pipeline runs.
"""

import os
from rich.console import Console
from glom import glom
from rich.table import Table
from rich.text import Text
import sys
import tiktoken

# Add the parent directory to the sys.path so that we can import from the
# gotaglio package, as if it had been installed.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gotaglio.exceptions import ExceptionContext
from gotaglio.helpers import IdShortener
from gotaglio.main import main
from gotaglio.models import Model
from gotaglio.pipeline import Internal, Pipeline, Prompt
from gotaglio.shared import build_template


class SimplePipeline(Pipeline):
    # The Pipeline abstract base class requires _name and _description.
    # These are used by the Registry to list and instantiate pipelines.
    # The `pipelines` subcommand will print a list of available pipelines,
    # with their names and descriptions.
    _name = "simple"
    _description = "An example pipeline for an LLM-based calculator."

    def __init__(self, registry, replacement_config, flat_config_patch):
        """
        Initializes the pipeline with the given Registry and configuration.

        Args:
          - registry: an instance of class Registry. Provides access to models.
          - replacement_config: a configuration that should be used instead of the
              default configuration provided by the pipeline. The replacement_config
              is used when rerunning a case from a log file.
          - flat_config_patch: a dictionary of glom-style key-value pairs that that
              override individual configuration values. These key-value pairs come from
              the command line and allow one to adjust model parameters or rerun a case
              with, say, a different model.
        """

        # Default configuration values for each pipeline stage.
        # The structure and interpretation of each configuration dict is
        # dictated by the needs of corresponding pipeline stage.
        #
        # An instance of Prompt indicates that the value must be provided on
        # the command line. In this case, the user would need to provide values
        # for the following keys on the command line:
        #   - prepare.template
        #   - infer.model.name
        #
        # An instance of Internal indicates that the value is provided by the
        # pipeline runtime. Using a value of Internal will prevent the
        # corresponding key from being displayed in help messages.
        #
        # There is no requirement to define a configuration dict for each stage.
        # It is the implementation of the pipeline that determines which stages
        # require configuration dicts.
        default_config = {
            "prepare": {
                "template": Prompt("Template file for system message"),
                "template_text": Internal()
                },
            "infer": {
                "model": {
                    "name": Prompt("Model name to use for inference stage"),
                    "settings": {
                        "max_tokens": 800,
                        "temperature": 0.7,
                        "top_p": 0.95,
                        "frequency_penalty": 0,
                        "presence_penalty": 0,
                    },
                }
            },
        }
        super().__init__(default_config, replacement_config, flat_config_patch)

        # Save registry here for later use in the stages() method.
        self._registry = registry

        # Construct and register some model mocks, specific to this pipeline.
        Flakey(registry, {})
        Perfect(registry, {})
        Parrot(registry, {})

    # The structure of the pipeline is defined by the stages() method.
    # This example demonstrates a simple, linear pipeline with four stages.
    def stages(self):
        #
        # Perform some setup here so that any initialization errors encountered
        # are caught before running the cases.
        #

        # Compile the jinja2 template used in the `prepare` stage.
        template = build_template(
            self.config(),
            "prepare.template",
            "prepare.template_text",
        )

        # Instantiate the model for the `infer` stage.
        model = self._registry.model(glom(self.config(), "infer.model.name"))

        #
        # Define the pipeline stage functions
        #
        """
        Define the pipeline stage functions. Each stage function is a coroutine
        that takes a context dictionary as an argument.

        context["case"] has the `case` data for the current case. Typically
        this comes from the cases JSON file specified as a parameter to the
        `run` sub-command.

        context["stages"][name] has the return value for stage `name`. Note
        that context["stages"][name] will only be defined if after the stage
        has to conclusion without raising an exception.

        Note that a stage function will only be invoked if the previous stage
        has completed with a return value. 
        """

        # Create the system and user messages
        async def prepare(context):
            messages = [
                {"role": "system", "content": await template(context)},
                {"role": "user", "content": context["case"]["user"]},
            ]

            return messages

        # Invoke the model to generate a response
        async def infer(context):
            return await model.infer(context["stages"]["prepare"], context)

        # Attempt to extract a numerical answer from the model response.
        # Note that this method will raise an exception if the response is not
        # a number.
        async def extract(context):
            with ExceptionContext(f"Extracting numerical answer from LLM response."):
                return float(context["stages"]["infer"])

        # Compare the model response to the expected answer.
        async def assess(context):
            return context["stages"]["extract"] - context["case"]["answer"]

        # The pipeline stages will be executed in the order specified in the
        # dictionary returned by the stages() method. The keys of the
        # dictionary are the names of the stages.
        return {
            "prepare": prepare,
            "infer": infer,
            "extract": extract,
            "assess": assess,
        }


    # This method is used to summarize the results of each a pipeline run.
    # It is invoked by the `run`, `rerun`, and `summarize` sub-commands.
    def summarize(self, runlog):
        results = runlog["results"]
        if len(results) == 0:
            print("No results.")
        else:
            # To make the summary more readable, create a short, unique prefix
            # for each case id.
            short_id = IdShortener([result["case"]["uuid"] for result in results])

            # Using Table from the rich text library.
            # https://rich.readthedocs.io/en/stable/introduction.html
            table = Table(title=f"Summary for {runlog['uuid']}")
            table.add_column("id", justify="right", style="cyan", no_wrap=True)
            table.add_column("run", style="magenta")
            table.add_column("score", justify="right", style="green")
            table.add_column("keywords", justify="left", style="green")

            # Set up some counters for totals to be presented after the table.
            total_count = len(results)
            complete_count = 0
            passed_count = 0
            failed_count = 0
            error_count = 0

            # Add one row for each case.
            for result in results:
                succeeded = result["succeeded"]
                cost = result["stages"]["assess"] if succeeded else None

                if succeeded:
                    complete_count += 1
                    if cost == 0:
                        passed_count += 1
                    else:
                        failed_count += 1
                else:
                    error_count += 1

                complete = (
                    Text("COMPLETE", style="bold green")
                    if succeeded
                    else Text("ERROR", style="bold red")
                )
                cost_text = "" if cost == None else f"{cost:.2f}"
                score = (
                    Text(cost_text, style="bold green")
                    if cost == 0
                    else Text(cost_text, style="bold red")
                )
                keywords = (
                    ", ".join(sorted(result["case"]["keywords"]))
                    if "keywords" in result["case"]
                    else ""
                )
                table.add_row(short_id(result["case"]["uuid"]), complete, score, keywords)

            # Display the table and the totals.
            console = Console()
            console.print(table)
            console.print()
            console.print(f"Total: {total_count}")
            console.print(
                f"Complete: {complete_count}/{total_count} ({(complete_count/total_count)*100:.2f}%)"
            )
            console.print(
                f"Error: {error_count}/{total_count} ({(error_count/total_count)*100:.2f}%)"
            )
            console.print(
                f"Passed: {passed_count}/{total_count} ({(passed_count/total_count)*100:.2f}%)"
            )
            console.print(
                f"Failed: {failed_count}/{total_count} ({(failed_count/total_count)*100:.2f}%)"
            )
            console.print()


    # If uuid_prefix is specified, format those cases whose uuids start with
    # uuid_prefix. Otherwise, format all cases.
    def format(self, runlog, uuid_prefix):
        # Lazily load the GPT-4o tokenizer here so that we don't slow down
        # other scenarios that don't need it.
        if not hasattr(self, "_tokenizer"):
            self._tokenizer = tiktoken.get_encoding("cl100k_base")

        results = runlog["results"]
        if len(results) == 0:
            print("No results.")
        else:
            # To make the summary more readable, create a short, unique prefix
            # for each case id.
            short_id = IdShortener([result["case"]["uuid"] for result in results])

            for result in results:
                if uuid_prefix and not result["case"]["uuid"].startswith(uuid_prefix):
                    continue
                print(f"## Case: {short_id(result['case']['uuid'])}")
                if result["succeeded"]:
                    if result["stages"]["assess"] == 0:
                        print("**PASSED**  ")
                    else:
                        print(f"**FAILED**: expected {result['case']['answer']}, got {result['stages']['extract']}  ")
                    input_tokens = sum(
                        len(self._tokenizer.encode(message["content"]))
                        for message in result["stages"]["prepare"]
                    )
                    print(
                        f"Input tokens: {input_tokens}, output tokens: {len(self._tokenizer.encode(result['stages']['infer']))}"
                    )
                    print()
                    for message in result["stages"]["prepare"]:
                        print(f"**{message['role']}**: {message['content']}\n")
                    print(f"**assistant**: {result['stages']['extract']}")
                else:
                    print(f"Error: {result['exception']['message']}")
                    # print(f"Inference: {result['stages']['infer']}")
                    print(f"Traceback: {result['exception']['traceback']}")
                    print(f"Time: {result['exception']['time']}")


    def compare(self, a, b):
        console = Console()
        console.print("TODO: compare()")

        if a["uuid"] == b["uuid"]:
            console.print(f"Run ids are the same.\n")
            self.summarize(a)
            return

        if a["metadata"]["pipeline"]["name"] != b["metadata"]["pipeline"]["name"]:
            console.print(
                f"Cannot perform comparison because pipeline names are different: A is '{
                    a['metadata']['pipeline']['name']
                }', B is '{
                    b['metadata']['pipeline']['name']
                }'"
            )
            return

        a_cases = {result["case"]["uuid"]: result for result in a["results"]}
        b_cases = {result["case"]["uuid"]: result for result in b["results"]}
        a_uuids = set(a_cases.keys())
        b_uuids = set(b_cases.keys())
        both = a_uuids.intersection(b_uuids)
        just_a = a_uuids - b_uuids
        just_b = b_uuids - a_uuids

        console.print(f"A: {a["uuid"]}")
        console.print(f"B: {b["uuid"]}")
        console.print("")
        console.print(f"{len(just_a)} case{'s' if len(just_a) != 1 else ''} only in A")
        console.print(f"{len(just_b)} case{'s' if len(just_b) != 1 else ''} only in B")
        console.print(f"{len(both)} cases in both A and B")
        console.print("")

        # TODO: handle no results case
        if len(both) == 0:
            console.print("There are no cases to compare.")
            console.print()
            # Fall through to print empty table

        # To make the summary more readable, create a short, unique prefix
        # for each case id.
        short_id = IdShortener(both)     

        table = Table(title=f"Comparison of {"A, B"}", show_footer=True)
        table.add_column("id", justify="right", style="cyan", no_wrap=True)
        table.add_column("A", justify="right", style="magenta")
        table.add_column("B", justify="right", style="green")
        table.add_column("keywords", justify="left", style="green")

        rows = []
        pass_count_a = 0
        pass_count_b = 0
        for uuid in both:
            (text_a, order_a) = format_case(a_cases[uuid])
            (text_b, order_b) = format_case(b_cases[uuid])
            keywords = ", ".join(sorted(a_cases[uuid]["case"].get("keywords", [])))
            if order_a == 0:
                pass_count_a += 1
            if order_b == 0:
                pass_count_b += 1
            rows.append(
                (
                    (Text(short_id(uuid)), text_a, text_b, keywords),
                    order_b * 4 + order_a,
                )
            )
        rows.sort(key=lambda x: x[1])
        for row in rows:
            table.add_row(*row[0])

        table.columns[0].footer = "Total"
        table.columns[1].footer = Text(
            f"{pass_count_a}/{len(both)} ({(pass_count_a/len(both))*100:.0f}%)"
        )
        table.columns[2].footer = Text(
            f"{pass_count_b}/{len(both)} ({(pass_count_b/len(both))*100:.0f}%)"
        )

        console.print(table)
        console.print()


def format_case(result):
    if result["succeeded"]:
        if result["stages"]["assess"] == 0:
            return (Text("passed", style="bold green"), 0)
        else:
            return (Text("failed", style="bold red"), 1)
    else:
        return (Text("error", style="bold red"), 2)


class Flakey(Model):
    """
    A mock model class that cycles through
      1. returning the expected answer
      2. returning "hello world"
      3. raising an exception
    """

    def __init__(self, registry, configuration):
        self._counter = -1
        registry.register_model("flakey", self)

    async def infer(self, messages, result=None):
        self._counter += 1
        if self._counter % 3 == 0:
            return f'{result["case"]["answer"]}'
        elif self._counter % 3 == 1:
            return "hello world"
        else:
            raise Exception("Flakey model failed")

    def metadata(self):
        return {}


class Parrot(Model):
    """
    A mock model class that always returns a sentence summarizing the last
    message in the conversation.
    """

    def __init__(self, registry, configuration):
        registry.register_model("parrot", self)

    async def infer(self, messages, result=None):
        return f'{messages[-1]["role"]} says "{messages[-1]["content"]}"'

    def metadata(self):
        return {}


class Perfect(Model):
    """
    A mock model class that always returns the expected answer
    from result["case"]["answer"]
    """

    def __init__(self, registry, configuration):
        registry.register_model("perfect", self)

    async def infer(self, messages, result=None):
        return f'{result["case"]["answer"]}'

    def metadata(self):
        return {}


def go():
    main([SimplePipeline])


if __name__ == "__main__":
    go()
