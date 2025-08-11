import asyncio
from glom import glom
import os
from rich.text import Text
import sys

# Add the parent directory to the sys.path so that we can import from the
# gotaglio package, as if it had been installed.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gotaglio.dag import build_dag_from_spec
from gotaglio.director2 import Director2
from gotaglio.exceptions import ExceptionContext
from gotaglio.make_console import MakeConsole
from gotaglio.pipeline_spec import PipelineSpec, SummarizerSpec, TurnSpec, ColumnSpec
from gotaglio.pipeline2 import Internal, Pipeline2, Prompt
from gotaglio.registry import Registry
from gotaglio.shared import build_template, to_json_string
from gotaglio.summarize import keywords_column


# The structure of the pipeline is defined by the stages() method.
# This example demonstrates a simple, linear pipeline with four stages.
def create_dag(name, config, registry):
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
    turn_dag_spec = [
        {"name": "prepare", "function": prepare, "inputs": []},
        {"name": "infer", "function": infer, "inputs": ["prepare"]},
        {"name": "extract", "function": extract, "inputs": ["infer"]},
        {"name": "assess", "function": assess, "inputs": ["extract"]},
    ]
    return build_dag_from_spec(turn_dag_spec)


def cost_cell(result, turn_index):
    cost = glom(result, f"stages.turns.{turn_index}.stages.assess", default=None)
    cost_text = "" if cost == None else f"{cost:.2f}"
    return (
        Text(cost_text, style="bold green")
        if cost == 0
        else Text(cost_text, style="bold red")
    )


def user_cell(result, turn_index):
    return result["case"]["turns"][turn_index]["user"]


def predicate(result):
    x = glom(result, "stages.assess", default=1)
    return x == 0


spec = PipelineSpec(
    name="calculator",
    description="A simple calculator pipeline",
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
    turns=TurnSpec(initial="value", expected="answer", observed="extract", user="user"),
    create_dag=create_dag,
    summarize=SummarizerSpec(
        columns=[
            ColumnSpec(name="cost", contents=cost_cell),
            keywords_column,
            ColumnSpec(name="user", contents=user_cell),
        ],
        passed=lambda result: glom(result, "stages.assess", default=1) == 0,
    ),
)

cases = [
    {
        "uuid": "ed6ceb29-b4b9-427c-99b8-635984198a59",
        "keywords": ["multi-turn"],
        "value": 0,
        "turns": [
            {"user": "1+1", "base": 10, "answer": 2},
            {"user": "add one hundred", "base": 10, "answer": 102},
            {"user": "divide by two", "base": 10, "answer": 51},
        ],
    },
    {
        "uuid": "abcceb29-b4b9-427c-99b8-635984198a59",
        "keywords": ["multi-turn"],
        "value": 0,
        "turns": [
            {"user": "1+1", "base": 10, "answer": 2},
            {"user": "add one hundred", "base": 10, "answer": 102},
            {"user": "divide by two", "base": 10, "answer": 51},
        ],
    },
]

flat_config_patch = {
    "prepare.template": "samples/turns/template.txt",
    "infer.model.name": "gpt4o",
}

max_concurrency = 1


def go2():
    director = Director2(spec, cases, {}, flat_config_patch, max_concurrency)
    progress = None
    completed = None
    asyncio.run(director.process_all_cases(progress, completed))
    print("done")
    director.write_results()
    director.summarize_results()
    print("done2")
    # registry = Registry()
    # pipeline = Pipeline2(spec, None, {"prepare.template": "samples/turns/template.txt", "infer.model.name": "perfect"}, registry)


def go1():
    print(spec)

    registry = Registry()
    pipeline = Pipeline2(spec, None, {"precision": 3}, registry)
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
                        {"user": "divide by two", "expected": 51},
                    ],
                },
                "stages": {
                    "turns": [
                        {"succeeded": True, "stages": {"extract": 2}},
                        {"succeeded": True, "stages": {"extract": 103}},
                        {"succeeded": True, "stages": {"extract": 51}},
                    ]
                },
            },
        ],
    }
    console = MakeConsole()
    pipeline.summarize(console, runlog)
    console.render()


go2()
