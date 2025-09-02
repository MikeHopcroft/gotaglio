import json
import pytest

from gotaglio.models import AzureOpenAIRealtime

class DummyRegistry:
    def register_model(self, name, model):
        setattr(self, name, model)

@pytest.mark.asyncio
async def test_append_event_has_timestamp(monkeypatch, tmp_path):
    registry = DummyRegistry()
    model = AzureOpenAIRealtime(
        registry,
        {
            "name": "azure-realtime",
            "type": "AZURE_OPEN_AI_REALTIME",
            "endpoint": "https://example.openai.azure.com",
            "api": "2024-06-01",
            "deployment": "gpt-4o-realtime-preview",
            "key": "sk-test",
            "sample_rate_hz": 16000,
            "timeout_s": 3,
        },
    )

    # Prepare fake audio
    audio_path = tmp_path / "hello.wav"
    audio_path.write_bytes(b"FAKEAUDIO")

    # WebSocket dummy: yields a quick completion
    class DummyWS:
        def __init__(self):
            self.sent = []
            self._recv_iter = iter([
                json.dumps({"type": "response.done"}),
            ])
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            return False
        async def send(self, data):
            self.sent.append(data)
        async def recv(self):
            try:
                return next(self._recv_iter)
            except StopIteration:
                return json.dumps({"type": "response.done"})

    def fake_connect(url, extra_headers=None, ping_timeout=None):
        return DummyWS()

    import gotaglio.lazy_imports as li
    monkeypatch.setattr(li.websockets, "connect", fake_connect)

    context = {"audio_file": str(audio_path)}
    _ = await model.infer(messages=[], context=context)

    events = context.get("realtime_events", [])
    assert events, "expected events"
    # Check a few events have timestamp_utc and it's a string
    for ev in events[:3]:
        assert "timestamp_utc" in ev
        assert isinstance(ev["timestamp_utc"], str)
