from glom import glom
import os
import sys

# Add the parent directory to the sys.path so that we can import from the
# gotaglio package, as if it had been installed.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gotaglio.dag import build_dag_from_spec
from gotaglio.exceptions import ExceptionContext
from gotaglio.make_console import MakeConsole
from gotaglio.pipeline_spec import PipelineSpec, SummarizerSpec, TurnSpec, ColumnSpec
from gotaglio.pipeline2 import Pipeline2
from gotaglio.shared import build_template, to_json_string

# The structure of the pipeline is defined by the stages() method.
# This example demonstrates a simple, linear pipeline with four stages.
def create_dag(config, registry):
    #
    # Perform some setup here so that any initialization errors encountered
    # are caught before running the cases.
    #

    # Compile the jinja2 template used in the `prepare` stage.
    template = build_template(
        config,
        "prepare.template",
        "prepare.template_text",
    )

    # Instantiate the model for the `infer` stage.
    model = registry.model(glom(config, "infer.model.name"))

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
            {"role": "assistant", "content": str(context["case"]["value"])},
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

    # Define the sub-pipeline spec
    turn_spec = [
        {"name": "prepare", "function": prepare, "inputs": []},
        {"name": "infer", "function": infer, "inputs": ["prepare"]},
        {"name": "extract", "function": extract, "inputs": ["infer"]},
        {"name": "assess", "function": assess, "inputs": ["extract"]},
    ]
    return build_dag_from_spec(turn_spec)


def user_cell(result, turn_index):
    return result["case"]["turns"][turn_index]["user"]

spec = PipelineSpec(
    name="calculator",
    description="A simple calculator pipeline",
    configuration={"base": 10},
    turns=TurnSpec(initial="value", expected="expected", observed="extract"),
    create_dag=create_dag
    summarize=SummarizerSpec(columns=[ColumnSpec(name="user", contents=user_cell)])
)

def go2():
    pipeline = Pipeline2(spec, None, {"precision": 3})


def go1():
    print(spec)

    pipeline = Pipeline2(spec, None, {"precision": 3})
    print(pipeline)

    runlog = {
        "uuid": "1234",
        "results": [
            {
                "succeeded": True,
                "case": {
                    "uuid": "ed6ceb29-b4b9-427c-99b8-635984198a59",
                    "keywords": ["math", "addition"],
                    "value": 0,
                    "turns": [
                        {"user": "1+1", "expected": 2},
                        {"user": "Plus 100", "expected": 102},
                        {"user": "divide by two", "expected": 51}
                    ]
                },
                "stages": {
                    "turns": [
                        {"succeeded": True, "stages": {"extract": 2}},
                        {"succeeded": True, "stages": {"extract": 103}},
                        {"succeeded": True, "stages": {"extract": 51}}
                    ]
                }
            },
        ],
    }
    console = MakeConsole()
    pipeline.summarize(console, runlog)
    console.render()

go()
