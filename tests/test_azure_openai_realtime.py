import asyncio
import base64
import json
from typing import Any

import pytest

from gotaglio.models import AzureOpenAIRealtime


class DummyRegistry:
    def register_model(self, name, model):
        setattr(self, name, model)


def make_model(timeout_s: float = 1.0, extra: dict[str, Any] | None = None):
    registry = DummyRegistry()
    cfg = {
        "name": "azure-realtime",
        "type": "AZURE_OPEN_AI_REALTIME",
        "endpoint": "https://example.openai.azure.com",
        "api": "2024-06-01",
        "deployment": "gpt-4o-realtime-preview",
        "key": "sk-test",
        "timeout_s": timeout_s,
    }
    if extra:
        cfg.update(extra)
    return AzureOpenAIRealtime(registry, cfg)


@pytest.mark.asyncio
async def test_infer_requires_audio_raises_value_error():
    model = make_model()
    with pytest.raises(ValueError):
        await model.infer(messages=[], context={})


def test_connect_websocket_missing_config_raises():
    registry = DummyRegistry()
    # Missing endpoint/api/deployment/key
    model = AzureOpenAIRealtime(registry, {"name": "rt", "type": "AZURE_OPEN_AI_REALTIME"})
    with pytest.raises(ConnectionError):
        # Call private method directly for targeted validation
        model._connect_websocket()


def test_make_audio_append_message_base64_roundtrip():
    model = make_model()
    raw = b"hello-bytes"
    payload = model._make_audio_append_message(raw)
    assert payload["type"] == "input_audio_buffer.append"
    encoded = payload["audio"]
    # When conversion fails (non-wav), fallback returns original bytes
    assert base64.b64decode(encoded) == raw


@pytest.mark.asyncio
async def test_infer_sends_expected_sequence_and_events(monkeypatch, tmp_path):
    # Prepare fake audio on disk (exercise file loading path)
    audio_path = tmp_path / "sound.wav"
    audio_bytes = b"FAKEAUDIO123"
    audio_path.write_bytes(audio_bytes)

    # WebSocket dummy that records send frames and yields a couple of JSON messages
    class DummyWS:
        def __init__(self):
            self.sent = []
            self.closed = False
            self._recv_iter = iter([
                json.dumps({"type": "response.output_text.delta", "delta": "hola"}),
                json.dumps({"type": "response.done", "output_text": "hola"}),
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

        async def close(self):
            self.closed = True

    # Track the instance used by the model under test
    holder: dict[str, Any] = {}

    def fake_connect(url, extra_headers=None, ping_timeout=None):
        ws = DummyWS()
        holder["ws"] = ws
        return ws

    # Patch the lazy websockets.connect
    import gotaglio.lazy_imports as li
    monkeypatch.setattr(li.websockets, "connect", fake_connect)

    model = make_model()
    context = {"audio_file": str(audio_path)}
    # Exercise infer; it may not return a value depending on implementation
    await model.infer(messages=[], context=context)

    # Validate send sequence from the actual websocket used
    ws_used = holder.get("ws")
    assert ws_used is not None
    sent = [json.loads(s) for s in ws_used.sent]
    # First should be session.update
    assert sent[0]["type"] == "session.update"
    # Contains expected session config
    assert sent[0]["session"]["voice"] == "alloy"
    assert sent[0]["session"]["modalities"] == ["text"]
    # Instructions should be omitted when not explicitly provided
    assert "instructions" not in sent[0]["session"]
    # Then audio append frame
    assert sent[1]["type"] == "input_audio_buffer.append"
    assert isinstance(sent[1]["audio"], str) and sent[1]["audio"]
    # Commit and create follow
    assert sent[2]["type"] == "input_audio_buffer.commit"
    assert sent[3]["type"] == "response.create"

    # Validate events captured in context
    events = context.get("realtime_events", [])
    types = [e.get("type") for e in events]
    # Ensure core lifecycle events exist
    for ev in ("audio.resolved", "debug.ws", "session.connected", "session.update",
               "input_audio_buffer.append", "input_audio_buffer.commit", "response.create"):
        assert ev in types
    # Audio event is redacted and sized using original bytes (fallback path)
    audio_event = next(e for e in events if e["type"] == "input_audio_buffer.append")
    assert audio_event.get("redacted") is True
    assert audio_event.get("size") == len(audio_bytes)
    # New timing fields
    # All events should include timestamp_utc and elapsed_ms_since_audio_start
    for ev in events:
        assert "timestamp_utc" in ev
        assert "elapsed_ms_since_audio_start" in ev
    # Pre-audio events have None elapsed
    pre_audio_types = {"audio.resolved", "debug.ws", "session.connected", "session.update", "audio.convert.skip"}
    for ev in events:
        if ev.get("type") in pre_audio_types:
            assert ev.get("elapsed_ms_since_audio_start") is None
    # First audio append should be 0ms elapsed
    assert audio_event.get("elapsed_ms_since_audio_start") == 0


@pytest.mark.asyncio
async def test_session_config_overrides_via_model_and_context(monkeypatch, tmp_path):
    # Prepare fake audio
    audio_path = tmp_path / "sound.wav"
    audio_path.write_bytes(b"FAKEAUDIO123")

    class DummyWS:
        def __init__(self):
            self.sent = []
            self.closed = False
            self._recv_iter = iter([
                json.dumps({"type": "response.output_text.delta", "delta": "hola"}),
                json.dumps({"type": "response.done", "output_text": "hola"}),
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

        async def close(self):
            self.closed = True

    holder: dict[str, Any] = {}
    def fake_connect(url, extra_headers=None, ping_timeout=None):
        ws = DummyWS()
        holder["ws"] = ws
        return ws

    import gotaglio.lazy_imports as li
    monkeypatch.setattr(li.websockets, "connect", fake_connect)

    # Model-level defaults
    model = make_model(extra={
        "voice": "vega",
        "modalities": ["text", "audio"],
        "turn_detection": {"type": "server_vad", "threshold": 0.5, "silence_duration_ms": 400},
    })

    # Context-level override should win
    context = {
        "audio_file": str(audio_path),
        "voice": "orion",
        "modalities": ["audio", "text", "audio"],  # duplicate to test dedupe and order
        "turn_detection": {"type": "semantic_vad", "eagerness": "high"},
    }

    await model.infer(messages=[], context=context)

    ws_used = holder.get("ws")
    assert ws_used is not None
    sent = [json.loads(s) for s in ws_used.sent]
    session = sent[0]["session"]
    assert session["voice"] == "orion"
    assert session["modalities"] == ["audio", "text"]
    assert session["turn_detection"]["type"] == "semantic_vad"
    assert session["turn_detection"]["eagerness"] == "high"


@pytest.mark.asyncio
async def test_turn_detection_none_maps_to_type_none(monkeypatch, tmp_path):
    audio_path = tmp_path / "sound.wav"
    audio_path.write_bytes(b"FAKEAUDIO123")

    class DummyWS:
        def __init__(self):
            self.sent = []
            self.closed = False
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

        async def close(self):
            self.closed = True

    holder: dict[str, Any] = {}
    def fake_connect(url, extra_headers=None, ping_timeout=None):
        ws = DummyWS()
        holder["ws"] = ws
        return ws

    import gotaglio.lazy_imports as li
    monkeypatch.setattr(li.websockets, "connect", fake_connect)

    model = make_model(extra={"turn_detection": None})
    await model.infer(messages=[], context={"audio_file": str(audio_path)})

    ws_used = holder.get("ws")
    assert ws_used is not None
    sent = [json.loads(s) for s in ws_used.sent]
    session = sent[0]["session"]
    assert session["turn_detection"]["type"] == "none"


@pytest.mark.asyncio
async def test_invalid_modalities_and_voice_raise(monkeypatch, tmp_path):
    audio_path = tmp_path / "sound.wav"
    audio_path.write_bytes(b"FAKEAUDIO123")

    class DummyWS:
        def __init__(self):
            self.sent = []
            self._recv_iter = iter([json.dumps({"type": "response.done"})])

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def send(self, data):
            self.sent.append(data)

        async def recv(self):
            return json.dumps({"type": "response.done"})

    def fake_connect(url, extra_headers=None, ping_timeout=None):
        return DummyWS()

    import gotaglio.lazy_imports as li
    monkeypatch.setattr(li.websockets, "connect", fake_connect)

    # Invalid modalities value
    model = make_model()
    with pytest.raises(ValueError):
        await model.infer(messages=[], context={"audio_file": str(audio_path), "modalities": ["video"]})

    # Invalid empty voice
    with pytest.raises(ValueError):
        await model.infer(messages=[], context={"audio_file": str(audio_path), "voice": ""})


@pytest.mark.asyncio
async def test_invalid_turn_detection_type_raises(monkeypatch, tmp_path):
    audio_path = tmp_path / "sound.wav"
    audio_path.write_bytes(b"FAKEAUDIO123")

    class DummyWS:
        def __init__(self):
            self.sent = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def send(self, data):
            self.sent.append(data)

        async def recv(self):
            return json.dumps({"type": "response.done"})

    def fake_connect(url, extra_headers=None, ping_timeout=None):
        return DummyWS()

    import gotaglio.lazy_imports as li
    monkeypatch.setattr(li.websockets, "connect", fake_connect)

    model = make_model()
    with pytest.raises(ValueError):
        await model.infer(messages=[], context={
            "audio_file": str(audio_path),
            "turn_detection": {"type": "magic_vad"},
        })


@pytest.mark.asyncio
async def test_infer_includes_instructions_when_provided(monkeypatch, tmp_path):
    # Prepare fake audio on disk
    audio_path = tmp_path / "sound.wav"
    audio_bytes = b"FAKEAUDIO123"
    audio_path.write_bytes(audio_bytes)

    # WebSocket dummy that records send frames
    class DummyWS:
        def __init__(self):
            self.sent = []
            self.closed = False
            self._recv_iter = iter([
                json.dumps({"type": "response.output_text.delta", "delta": "hola"}),
                json.dumps({"type": "response.done", "output_text": "hola"}),
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

        async def close(self):
            self.closed = True

    holder: dict[str, Any] = {}

    def fake_connect(url, extra_headers=None, ping_timeout=None):
        ws = DummyWS()
        holder["ws"] = ws
        return ws

    import gotaglio.lazy_imports as li
    monkeypatch.setattr(li.websockets, "connect", fake_connect)

    model = make_model()
    custom_instructions = "Please respond in Pig Latin."
    context = {"audio_file": str(audio_path), "instructions": custom_instructions}
    await model.infer(messages=[], context=context)

    ws_used = holder.get("ws")
    assert ws_used is not None
    sent = [json.loads(s) for s in ws_used.sent]
    assert sent[0]["type"] == "session.update"
    assert sent[0]["session"]["instructions"] == custom_instructions


    


@pytest.mark.asyncio
async def test_receive_timeout_records_event_and_returns_empty(monkeypatch, tmp_path):
    # Prepare audio bytes in context directly
    audio_bytes = b"FAKEAUDIO-TIMEOUT"

    class SlowWS:
        def __init__(self):
            self.sent = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def send(self, data):
            self.sent.append(data)

        async def recv(self):
            # Exceed the wait timeout deliberately
            await asyncio.sleep(0.2)
            return json.dumps({"type": "noop"})

    def fake_connect(url, extra_headers=None, ping_timeout=None):
        return SlowWS()

    import gotaglio.lazy_imports as li
    monkeypatch.setattr(li.websockets, "connect", fake_connect)

    # Use very small timeout to trigger wait_for timeout
    model = make_model(timeout_s=0.05)
    context = {"audio_bytes": audio_bytes}
    out = await model.infer(messages=[], context=context)
    # On timeout, return empty string
    assert out == ""
    events = context.get("realtime_events", [])
    types = [e.get("type") for e in events]
    assert "error.timeout" in types
    # Timeout path still includes timing fields
    for ev in events:
        assert "timestamp_utc" in ev
        assert "elapsed_ms_since_audio_start" in ev


def test_metadata_excludes_key():
    model = make_model(extra={"voice": "vega"})
    md = model.metadata()
    assert "key" not in md
    assert md.get("voice") == "vega"
