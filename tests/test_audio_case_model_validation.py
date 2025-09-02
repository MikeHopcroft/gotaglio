import asyncio
import pytest

from gotaglio.director import Director
from gotaglio.pipeline_spec import PipelineSpec
from gotaglio.pipeline import Internal, Prompt
from gotaglio.dag import Dag


def make_min_pipeline_spec(model_name: str) -> PipelineSpec:
    async def prepare(context):
        return []

    async def infer(context):
        return ""

    def create(name, config, registry):
        stages = {
            "prepare": prepare,
            "infer": infer,
        }
        return Dag.from_linear(stages)

    return PipelineSpec(
        name="min",
        description="minimal pipeline for validation tests",
        configuration={
            "infer": {
                "model": {
                    "name": model_name,
                }
            }
        },
        create_dag=create,
    )


class DummyModel:
    def __init__(self, registry, configuration):
        self._config = configuration
        registry.register_model(configuration["name"], self)

    async def infer(self, messages, context=None) -> str:
        return ""

    def metadata(self):
        return {k: v for k, v in self._config.items() if k != "key"}


def register_min_models(registry):
    # Register two models: one realtime, one text-only
    DummyModel(registry, {"name": "text-only", "type": "AZURE_OPEN_AI"})
    DummyModel(registry, {"name": "azure-realtime", "type": "AZURE_OPEN_AI_REALTIME"})


def build_director_with_models(model_name: str) -> Director:
    spec = make_min_pipeline_spec(model_name)

    # Build a Director but swap in a registry pre-populated with dummy models
    director = Director(spec, None, {}, max_concurrency=1)
    # Replace the empty registry with our own models
    from gotaglio.registry import Registry
    reg = Registry()
    register_min_models(reg)
    director._registry = reg  # type: ignore[attr-defined]
    return director


def test_audio_case_with_text_model_fails_fast():
    director = build_director_with_models("text-only")
    cases = [{"uuid": "00000000-0000-0000-0000-000000000001", "audio": "file.wav"}]
    with pytest.raises(ValueError) as ei:
        asyncio.run(director.process_all_cases(cases, progress=None, completed=None))
    assert "Audio case requires an audio-capable model" in str(ei.value)


def test_audio_case_with_realtime_model_passes_validation():
    director = build_director_with_models("azure-realtime")
    cases = [{"uuid": "00000000-0000-0000-0000-000000000002", "audio": "file.wav"}]
    # Should not raise; run completes (infer returns empty string)
    runlog = asyncio.run(director.process_all_cases(cases, progress=None, completed=None))
    assert runlog["results"][0]["succeeded"] is True