from glom import glom
import json
import os
from rich.console import Console
from rich.text import Text
import sys
from typing import Any

# Add the parent directory to the sys.path so that we can import from the
# gotaglio package, as if it had been installed.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gotaglio.dag import Dag
from gotaglio.exceptions import ExceptionContext
from gotaglio.format import format_messages
from gotaglio.main import main
from gotaglio.pipeline_spec import (
    ColumnSpec,
    FormatterSpec,
    get_result,
    get_stages,
    get_turn,
    PipelineSpec,
    SummarizerSpec,
    column_spec,
)
from gotaglio.pipeline import Internal, Prompt
from gotaglio.repair import Repair
from gotaglio.shared import build_template, to_json_string
from gotaglio.summarize import keywords_column
from gotaglio.tokenizer import tokenizer


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
configuration = {
    "prepare": {
        # Specifies whether prompt should include assistant messages
        # in the conversational history.
        "assistant_history": True,
        # Specifies whether prompt should include user messages
        # in the conversational history.
        "user_history": True,
        # Specifies whether the cart on turn entry should be the
        # `extracted` cart from the previous turn (True) or the
        # `expected` cart (False).
        "linked_turns": True,
        "template": Prompt("Template file for system message"),
        # Internal cache of the template text read from `prepare.template`.
        # This field is set by the stage() function.
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

    # Cache a few configuration values for the prepare stage.
    assistant_history = glom(config, "prepare.assistant_history")
    user_history = glom(config, "prepare.user_history")
    linked_turns = glom(config, "prepare.linked_turns")

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
    # Note that a stage function will only be invoked if all of its previous or
    # input stages have completed with a return value.

    # Stage 1:Create the system and user messages
    async def prepare(context):
        i = len(context["turns"]) - 1

        # Get previous assistant and user messages.
        previous = [
            x
            for x in (context["turns"][i - 1]["stages"]["prepare"] if i != 0 else [])
            if x["role"] != "system"
        ]

        if not assistant_history:
            # Want to keep the initial cart.
            # Keep only the initial assistant message, filter out the rest
            assistant_found = False
            filtered = []
            for x in previous:
                if x["role"] == "assistant":
                    # If we're suppressing user history, the also remove
                    # the first cart.
                    if not assistant_found and user_history:
                        filtered.append(x)
                        assistant_found = True
                else:
                    filtered.append(x)
            previous = filtered

        if not user_history:
            previous = [x for x in previous if x["role"] != "user"]

        # Prepare the system message for this turn.
        system = {"role": "system", "content": await template(context)}

        # Prepare the assistant message that states the cart contents
        # at the beginning of this turn.
        cart = (
            context["case"]["cart"]
            if i == 0
            else (
                context["turns"][i - 1]["stages"]["extract"]
                if linked_turns and not context["isolated_turns"]
                else context["case"]["turns"][i - 1]["expected"]
            )
        )

        assistant = {"role": "assistant", "content": to_json_string(cart)}

        # Prepare the user message for this turn.
        user = {"role": "user", "content": context["case"]["turns"][i]["user"]}

        return [system] + previous + [assistant, user]

    # Stage 2: Invoke the model to generate a response
    async def infer(context):
        stages = get_stages(context)
        # Pass per-pipeline model settings to the model via context
        model_settings = glom(config, "infer.model.settings", default={})
        ctx = dict(context)
        ctx["model_settings"] = model_settings
        return await model.infer(stages["prepare"], ctx)

    # Stage 3: Attempt to extract a numerical answer from the model response.
    # Note that this method will raise an exception if the response is not
    # a number.
    async def extract(context):
        stages = get_stages(context)
        with ExceptionContext(f"Extracting JSON from LLM response."):
            text = stages["infer"]

            # Strip off fenced code block markers, if present.
            marker = "```json\n"
            if text.startswith(marker):
                text = text[len(marker) :]
            text = text.strip("```")
            return json.loads(text)

    # Stage 4: Compare the model response to the expected answer.
    async def assess(context):
        stages = get_stages(context)
        turn = get_turn(context)
        repair = Repair("id", "options", [], ["name"], "name")
        repair.resetIds()
        observed = repair.addIds(stages["extract"]["items"])
        expected = repair.addIds(turn["expected"]["items"])
        return repair.diff(observed, expected)

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

    return Dag.from_linear(stages)


###############################################################################
#
# Summarizer extensions
#
###############################################################################
def cost_cell(result: dict[str, Any], turn_index: int):
    """
    For user-defined `cost` column in the summary report table.
    Provides contents and formatting for the cost cell for the summary table.
    The cost is the difference between the model's response and the expected answer.
    """
    cost = glom(get_stages(result, turn_index), "assess.cost", default=None)
    cost_text = "" if cost == None else f"{cost:.2f}"
    return (
        Text(cost_text, style="bold green")
        if cost == 0
        else Text(cost_text, style="bold red")
    )


def user_cell(result, turn_index):
    """
    For user-defined `user` column in the summary report table.
    Provides contents and formatting for the user cell in the summary table.
    This cell displays the user input for the specified turn index.
    """
    return get_turn(result, turn_index)["user"]


###############################################################################
#
# Formatter extensions
#
###############################################################################
def format_turn(console: Console, turn_index, result: dict[str, Any]):
    stages = get_result(result, turn_index)
    passed = passed_predicate(result)
    if passed:
        console.print(f"### Turn {turn_index + 1}: **PASSED**  ")
    else:
        cost = glom(stages, "stages.assess.cost", default=None)
        console.print(f"### Turn {turn_index + 1}: **FAILED:** (cost={cost})  ")
    console.print()

    input_tokens = sum(
        len(tokenizer.encode(message["content"]))
        for message in stages["stages"]["prepare"]
    )
    console.print(
        f"Input tokens: {input_tokens}, output tokens: {len(tokenizer.encode(stages['stages']['infer']))}  \n"
    )

    format_messages(console, stages["stages"]["prepare"], collapse=["system"])
    console.print("**assistant:**")
    console.print("```json")
    console.print(to_json_string(stages["stages"]["extract"]))
    console.print("```")
    console.print()

    if passed:
        console.print("**No repairs**")
    else:
        console.print("**expected:**")
        console.print("<details><summary>Click to expand</summary>  \n")
        console.print("```json")
        console.print(to_json_string(result["case"]["turns"][turn_index]["expected"]))
        console.print("```")
        console.print("\n</details>  \n  \n")
        console.print("")
        console.print("**Repairs:**")
        for step in stages["stages"]["assess"]["steps"]:
            console.print(f"* {step}")


###############################################################################
#
# Pipeline extensions
#
###############################################################################
def expected(result, turn_index=None):
    """
    Returns the expected value from a turn. Used by mock models.
    """
    return get_turn(result, turn_index)["expected"]


def passed_predicate(result, turn_index=None):
    """
    Predicate function to determine if the result is considered passing.
    This checks if the assessment stage's result is zero, indicating
    that the LLM response matches the expected answer.

    Used by the `format` and `summarize` sub-commands.
    """
    return glom(get_stages(result, turn_index), "assess.cost", default=None) == 0


###############################################################################
#
# Pipeline specification
#
###############################################################################
menu_pipeline_spec = PipelineSpec(
    # Pipeline name used in `gotag run <pipeline>.`
    name="menu",
    #
    # Pipeline description shown by `gotag pipelines.`
    description="A multi-turn menu ordering pipeline",
    # Default configuration values for use by pipeline stages.
    configuration=configuration,
    # Defines the directed acyclic graph (DAG) of stage functions.
    create_dag=stages,
    # Required function to extract the expected answer from the test case.
    expected=expected,
    # Optional FormatterSpec used by the `format` commend to display a rich
    # transcript of the case.
    formatter=FormatterSpec(
        format_turn=format_turn,
    ),
    # Optional predicate determines whether a case is considered passing.
    # Used by the `format` and `summarize` sub-commands.
    passed_predicate=passed_predicate,
    # Optional SummarizerSpec used by the `summarize` command to
    # summarize the results of the run.
    summarizer=SummarizerSpec(
        columns=[
            column_spec(name="cost", contents=cost_cell),
            keywords_column,
            column_spec(name="user", contents=user_cell),
        ]
    ),
)


def go():
    main([menu_pipeline_spec])


if __name__ == "__main__":
    go()
