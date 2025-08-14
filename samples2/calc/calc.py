from glom import glom
import os
from rich.text import Text
import sys

# Add the parent directory to the sys.path so that we can import from the
# gotaglio package, as if it had been installed.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gotaglio.dag import build_dag_from_linear
from gotaglio.exceptions import ExceptionContext
from gotaglio.main import main
from gotaglio.pipeline_spec import (
    ColumnSpec,
    MappingSpec,
    PipelineSpec,
    SummarizerSpec,
)
from gotaglio.pipeline2 import Internal, Prompt
from gotaglio.shared import build_template
from gotaglio.summarize import keywords_column


###############################################################################
#
# Default Configuration Values
#
###############################################################################

# Default configuration values for each pipeline stage.
# The structure and interpretation of each configuration dict is
# dictated by the needs of corresponding pipeline stages.
#
# An instance of `Prompt` indicates that the value must be provided on
# the command line. In this case, the user would need to provide values
# for the following keys on the command line:
#   - prepare.template
#   - infer.model.name
#
# An instance of `Internal` indicates that the value is provided by the
# pipeline runtime. Using a value of `Internal` will prevent the
# corresponding key from being displayed in help messages.
#
# There is no requirement to define a configuration dict for each stage.
# It is the implementation of the pipeline that determines which stages
# require configuration dicts.
configuration={
    "prepare": {
        "template": Prompt("Template file for system message"),
        "template_text": Internal(),
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

###############################################################################
#
# Stage Functions
#
###############################################################################
def stages(name, config, registry):
    """
    Defines the structure of a simple, linear pipeline with four stages:
      **prepare** - creates the system prompt and user messages for the model
      **infer** - invokes the model to generate a response
      **extract** - attempts to extract a numerical answer from the model response
      **assess** - compares the extracted answer to the expected answer

    Parameters:
      name (str): Name of the pipeline. Can be used for error message formatting. Unused in this example.
      config (dict): Dictionary that supplies configuration settings used by stages.
      registry (object): Registry object providing access to models.

    Returns:
      dag_spec (object): A DAG specification object representing the pipeline stages
      and their execution order.

    Pipeline Stages:
      - prepare: Assembles system, assistant, and user messages for the model.
      - infer: Invokes the model to generate a response based on prepared messages.
      - extract: Attempts to extract a numerical answer from the model response.
      - assess: Compares the extracted answer to the expected answer for evaluation.
    """

    # Compile the jinja2 template used in the `prepare` stage.
    # By building the template here, we ensure that any errors in the template
    # compilation are caught before the stage functions are run.
    template = build_template(
        config,
        "prepare.template",
        "prepare.template_text",
    )

    # Instantiate the model for the `infer` stage.
    # By creating the model here, we ensure that any errors, such as a bad
    # model name or configuration issues, are caught before the stage functions
    # are run.
    model = registry.model(glom(config, "infer.model.name"))

    # Define the pipeline stage functions. Each stage function is a coroutine
    # that takes a context dictionary as an argument.
    #
    # context["case"] has the `case` data for the current case. Typically
    # this comes from the cases.json or cases.yamlfile specified as a parameter
    # to the `run` sub-command.
    #
    # context["stages"][name] has the return value for stage `name`. Note
    # that context["stages"][name] will only be defined if after the stage
    # has successfully run to conclusion without raising an exception.
    #
    # Note that a stage function will only be invoked if the previous stage
    # has completed with a return value.

    # Stage 1:Create the system and user messages
    async def prepare(context):
        messages = [
            {"role": "system", "content": await template(context)},
            {"role": "user", "content": context["case"]["user"]},
        ]

        return messages

    # Stage 2: Invoke the model to generate a response
    async def infer(context):
        return await model.infer(context["stages"]["prepare"], context)

    # Stage 3: Attempt to extract a numerical answer from the model response.
    # Note that this method will raise an exception if the response is not
    # a number.
    async def extract(context):
        with ExceptionContext(f"Extracting numerical answer from LLM response."):
            return float(context["stages"]["infer"])

    # Stage 4: Compare the model response to the expected answer.
    async def assess(context):
        return context["stages"]["extract"] - context["case"]["answer"]

    # Define the pipeline
    # The dictionary keys supply the names of the stages that make up the
    # pipeline. Stages will be executed in the order they are defined in the
    # dictionary.
    #
    # For more complex pipelines, you can use the
    # `dag_spec_from_linear()` function to create arbitrary
    # directed acyclic graphs (DAGs) of stages.
    stages = {
        "prepare": prepare,
        "infer": infer,
        "extract": extract,
        "assess": assess,
    }

    return build_dag_from_linear(stages)


###############################################################################
#
# Summarizer extensions
#
###############################################################################
def passed_predicate(result):
    """
    Predicate function to determine if the result is considered passing.
    This checks if the assessment stage's result is zero, indicating
    that the LLM response matches the expected answer.

    Used by the `format` and `summarize` sub-commands.
    """
    return glom(result, "stages.assess", default=None) == 0


def cost_cell(result, turn_index):
    """
    For user-defined `cost` column in the summary report table.
    Provides contents and formatting for the cost cell for the summary table.
    The cost is the difference between the model's response and the expected answer.
    """
    cost = glom(result, f"stages.assess", default=None)
    cost_text = "" if cost == None else f"{cost:.2f}"
    return (
        Text(cost_text, style="bold green")
        if cost == 0
        else Text(cost_text, style="bold red")
    )


def user_cell(result, turn_index):
    """
    For user-defined `user` column in the summary report table.
    Provides contents and for the user cell in the summary table.
    This cell displays the user input for the specified turn index.
    """
    return result["case"]["user"]


###############################################################################
#
# Pipeline Specification
#
###############################################################################
calc_pipeline_spec = PipelineSpec(
    # Pipeline name used in `gotag run <pipeline>.`
    name="calc",
    #
    # Pipeline description shown by `gotag pipelines.`
    description="A simple calculator pipeline",
    # Default configuration values for use by pipeline stages.
    configuration={
        "prepare": {
            "template": Prompt("Template file for system message"),
            "template_text": Internal(),
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
    },
    # Defines the directed acyclic graph (DAG) of stage functions.
    create_dag=stages,
    # Optional predicate determines whether a case is considered passing.
    # Used by the `format` and `summarize` sub-commands.
    passed_predicate=passed_predicate,
    # Optional SummarizerSpec used by the `summarize` command to
    # summarize the results of the run.
    summarizer=SummarizerSpec(
        columns=[
            ColumnSpec(name="cost", contents=cost_cell),
            keywords_column,
            ColumnSpec(name="user", contents=user_cell),
        ]
    ),
    mappings=MappingSpec(
        initial="value",
        expected="answer",
        observed="extract",
        user="user",
    ),
)


def go():
    main([calc_pipeline_spec])


if __name__ == "__main__":
    go()
