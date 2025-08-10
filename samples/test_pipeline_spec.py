import os
import sys

# Add the parent directory to the sys.path so that we can import from the
# gotaglio package, as if it had been installed.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gotaglio.make_console import MakeConsole
from gotaglio.pipeline_spec import PipelineSpec, SummarizerSpec, TurnSpec, ColumnSpec
from gotaglio.pipeline2 import Pipeline2


def user_cell(result, turn_index):
    return result["case"]["turns"][turn_index]["user"]


def go():
    # x = ColumnSpec(name="A", contents=cell_contents)
    # y = PipelineSpec(name="B", summarize=[x])
    # print(y)
    spec = PipelineSpec(
        name="calculator",
        description="A simple calculator pipeline",
        configuration={"base": 10},
        turns=TurnSpec(initial="value", expected="expected", observed="extract"),
        create_dag=lambda name, config: lambda x: x,  # Dummy DAG function
        summarize=SummarizerSpec(columns=[ColumnSpec(name="user", contents=user_cell)])
    )
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
