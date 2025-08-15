import asyncio
from glom import glom
import pytest

from gotaglio.dag import build_dag_from_linear
from gotaglio.director2 import Director2
from gotaglio.gotag import Gotaglio
from gotaglio.pipeline_spec import (
    ColumnSpec,
    MappingSpec,
    PipelineSpec,
    SummarizerSpec,
)
# from gotaglio.models import Model, ModelSpec
# from gotaglio.dag import dag_spec_from_linear
# from gotaglio.mocks import MockModel
# from samples2.menu.menu import stages

def test_single_turn_pipeline():
    """
    Verifies that a single-step pipeline can be created and run without crashing.
    """
    
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

        return build_dag_from_linear(stages)

    def passed_predicate(context):
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
    cases = [{
        "uuid": "9507b491-1e58-49f6-86af-47f4e97ae1aa",
        "user": "hello",
        "value": 0,
        "answer": 111 + config_initial
    }]

    flat_config_patch = {
        "stage1.initial": 2000,
    }

    gt = Gotaglio([spec])
    runlog = gt.run("single_turn", cases, flat_config_patch)
    print("Pipeline processing complete.")

    assert glom(runlog, "results.0.stages.stage3.result3") == glom(cases, "0.answer")
    assert passed_predicate(glom(runlog, "results.0")) == True


# def test_multi_step_pipeline():
#     """
#     Verifies that a multi-step pipeline can be created and run without crashing.
#     """
    
#     async def start(context):
#         return {"turn_index": 0}

#     async def step(context):
#         turn_index = context.get("turn_index", 0)
#         return {"turn_index": turn_index + 1}

#     spec = PipelineSpec(
#         name="multi_step",
#         description="A multi-step pipeline",
#         stages=dag_spec_from_linear([
#             PipelineStageSpec(name="start", function=start),
#             PipelineStageSpec(name="step1", function=step),
#             PipelineStageSpec(name="step2", function=step),
#         ]),
#         turns=2
#     )
    
#     pipeline = Pipeline2(spec)
#     cases = [{"id": "1"}]
    
#     # This is more of a smoke test to ensure no crashes
#     pipeline.run(cases=cases, concurrency=1)
