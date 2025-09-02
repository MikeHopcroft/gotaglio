import asyncio
from dataclasses import dataclass
from typing import Any

import pytest

from gotaglio.dag import Dag, run_dag
from gotaglio.models import AzureOpenAI5


@pytest.mark.asyncio
async def test_pipeline_passes_model_settings_from_config():
    """
    Ensure that per-pipeline infer.model.settings are passed into the model via context["model_settings"].
    """

    captured: dict[str, Any] = {}

    class StubModel:
        def __init__(self):
            self.calls: list[dict[str, Any]] = []

        async def infer(self, messages, context=None):
            # Capture the model settings passed via context
            self.calls.append({
                "messages": messages,
                "settings": (context or {}).get("model_settings", {}),
            })
            return "{}"  # minimal JSON for downstream extract-like stages if needed

    # Configuration containing model settings
    config = {
        "infer": {
            "model": {
                "name": "stub",
                "settings": {
                    "max_completion_tokens": 321,
                    "frequency_penalty": 0.1,
                    "presence_penalty": 0.2,
                },
            }
        }
    }

    stub = StubModel()

    async def prepare(context):
        return [{"role": "user", "content": "hi"}]

    async def infer(context):
        # Mimic samples/menu behavior: pass settings via context to model.infer
        model_settings = config["infer"]["model"].get("settings", {})
        ctx = dict(context)
        ctx["model_settings"] = model_settings
        return await stub.infer(context["stages"]["prepare"], ctx)

    stages = {
        "prepare": prepare,
        "infer": infer,
    }

    dag = Dag.from_linear(stages)
    context = {"stages": {}}
    await run_dag(dag, context)

    assert len(stub.calls) == 1
    assert stub.calls[0]["settings"]["max_completion_tokens"] == 321
    assert stub.calls[0]["settings"]["frequency_penalty"] == 0.1
    assert stub.calls[0]["settings"]["presence_penalty"] == 0.2


@pytest.mark.asyncio
async def test_azure_openai5_uses_max_completion_tokens_and_omits_temperature_top_p(monkeypatch):
    """
    Verify AzureOpenAI5 passes max_completion_tokens and omits temperature/top_p, and supports fallback from max_tokens.
    """

    # Fake OpenAI client to capture parameters
    recorded = {"create_calls": []}

    class FakeCompletions:
        def create(self, **kwargs):
            recorded["create_calls"].append(kwargs)

            @dataclass
            class Message:
                content: str

            @dataclass
            class Choice:
                message: Message

            class Response:
                def __init__(self):
                    self.choices = [Choice(message=Message(content="ok"))]

            return Response()

    class FakeChat:
        def __init__(self):
            self.completions = FakeCompletions()

    class FakeAzureOpenAI:
        def __init__(self, **kwargs):
            # Ensure client construction works with expected kwargs
            self.kwargs = kwargs
            self.chat = FakeChat()

    # Monkeypatch the openai client used in gotaglio.models
    from gotaglio import models as models_module

    monkeypatch.setattr(models_module, "openai", type("_FakeOpenAIModule", (), {"AzureOpenAI": FakeAzureOpenAI}))

    # Build AzureOpenAI5 with a fake registry
    class FakeRegistry:
        def register_model(self, name, model):
            self.model = model

    registry = FakeRegistry()
    model = AzureOpenAI5(
        registry,
        configuration={
            "name": "gpt5",
            "endpoint": "https://example",
            "key": "xyz",
            "api": "2025-01-01-preview",
            "deployment": "gpt-5",
        },
    )

    # First call: max_completion_tokens explicit, with temperature/top_p provided (should be ignored)
    recorded["create_calls"].clear()
    await model.infer(
        messages=[{"role": "user", "content": "hi"}],
        context={
            "model_settings": {
                "max_completion_tokens": 123,
                "temperature": 0.9,
                "top_p": 0.5,
                "frequency_penalty": 0.2,
            }
        },
    )
    assert len(recorded["create_calls"]) == 1
    kwargs = recorded["create_calls"][0]
    assert kwargs.get("max_completion_tokens") == 123
    # Disallowed for GPT-5
    assert "temperature" not in kwargs
    assert "top_p" not in kwargs
    # Still allowed
    assert kwargs.get("frequency_penalty") == 0.2
    assert kwargs.get("presence_penalty") == 0  # default

    # Second call: fallback when only max_tokens is provided
    recorded["create_calls"].clear()
    await model.infer(
        messages=[{"role": "user", "content": "hi"}],
        context={"model_settings": {"max_tokens": 77}},
    )
    assert len(recorded["create_calls"]) == 1
    kwargs = recorded["create_calls"][0]
    assert kwargs.get("max_completion_tokens") == 77