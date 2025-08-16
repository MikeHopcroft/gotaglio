import asyncio
from glom import glom
import pytest

from gotaglio.dag import Dag
from gotaglio.director2 import Director2
from gotaglio.gotag import Gotaglio
from gotaglio.pipeline_spec import (
    ColumnSpec,
    MappingSpec,
    PipelineSpec,
    SummarizerSpec,
)


def create_dag(name, config, registry):
    async def stage1(context):
        return {"result1": 1 + glom(config, "stage1.initial")}

    async def stage2(context):
        return {"result2": 10 + glom(context, "stages.stage1.result1")}

    async def stage3(context):
        return {"result3": 100 + glom(context, "stages.stage2.result2")}

    stages = {
        "stage1": stage1,
        "stage2": stage2,
        "stage3": stage3,
    }

    return Dag.from_linear(stages)


def test_single_turn_pipeline():
    """
    Verifies that a single-turn pipeline can be created and run without crashing.
    """

    def passed_predicate(context):
        # TODO: is this API right? It is for the case, not for the turn.
        return glom(context, "stages.stage3.result3") == glom(context, "case.answer")

    spec = PipelineSpec(
        name="single_turn",
        description="A single turn pipeline with three stages",
        configuration={
            "stage1": {"initial": 1000},
        },
        create_dag=create_dag,
        passed_predicate=passed_predicate,
        mappings=MappingSpec(
            initial="value",
            expected="answer",
            observed="stage3",
            user="user",
        ),
    )

    config_initial = 2000
    cases = [
        {
            "uuid": "9507b491-1e58-49f6-86af-47f4e97ae1aa",
            "user": "hello",
            "value": 0,
            "answer": 111 + config_initial,
        }
    ]

    flat_config_patch = {
        "stage1.initial": 2000,
    }

    gt = Gotaglio([spec])
    runlog = gt.run("single_turn", cases, flat_config_patch)
    print("Pipeline processing complete.")

    assert glom(runlog, "results.0.stages.stage3.result3") == glom(cases, "0.answer")
    assert passed_predicate(glom(runlog, "results.0")) == True


def test_multi_turn_pipeline():
    """
    Verifies that a multi-turn pipeline can be created and run without crashing.
    """

    def passed_predicate(context):
        # TODO: is this API right? It is for the case, not for the turn.
        return glom(context, "stages.turns.0.stages.stage3.result3") == glom(
            context, "case.turns.0.answer"
        )

    spec = PipelineSpec(
        name="multi_turn",
        description="A multi-turn pipeline with three stages",
        configuration={
            "stage1": {"initial": 1000},
        },
        create_dag=create_dag,
        passed_predicate=passed_predicate,
        mappings=MappingSpec(
            turns="turns",
            initial="value",
            expected="answer",
            observed="stage3",
            user="user",
        ),
    )

    config_initial = 2000
    cases = [
        {
            "uuid": "9507b491-1e58-49f6-86af-47f4e97ae1aa",
            "value": 0,
            "turns": [
                {
                    "user": "turn 1",
                    "answer": 111 + config_initial,
                },
                {
                    "user": "turn 2",
                    "answer": (111 + config_initial),
                },
            ],
        }
    ]

    flat_config_patch = {
        "stage1.initial": 2000,
    }

    gt = Gotaglio([spec])
    runlog = gt.run("multi_turn", cases, flat_config_patch)
    print("Pipeline processing complete.")

    assert glom(runlog, "results.0.stages.turns.0.stages.stage3.result3") == glom(
        cases, "0.turns.0.answer"
    )
    assert passed_predicate(glom(runlog, "results.0")) == True
