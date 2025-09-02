# Configurable Realtime session: voice, turn_detection, modalities

## Problem
Our Azure OpenAI Realtime model sends a fixed session configuration: `voice` defaults to "alloy", `modalities` defaults to `["text"]`, and `turn_detection` is hardcoded to `{ "type": "none" }`. Users need to configure these per model and per run (via context/CLI patches) to enable audio output, select voices, and use server-side turn detection (server_vad or semantic_vad) or disable it entirely.

## Goals (acceptance criteria)
- [ ] Model accepts configuration for `voice: str | None`, `modalities: list["text"|"audio"] | None`, and `turn_detection: dict | None` via model config and per-run overrides via `context`.
- [ ] `modalities` validates allowed values: only `"text"` and `"audio"`; order preserved; duplicates removed.
- [ ] `voice` validates as non-empty string when provided.
- [ ] `turn_detection` supports:
  - [ ] `{ "type": "server_vad", "threshold": float, "prefix_padding_ms": int, "silence_duration_ms": int, "create_response": bool, "interrupt_response": bool }` (any subset allowed; we pass through known fields)
  - [ ] `{ "type": "semantic_vad", "eagerness": "low"|"medium"|"high"|"auto", "create_response": bool, "interrupt_response": bool }`
  - [ ] `None` disables turn detection (config-level intent). Payload normalization maps `None` to Azure-friendly `{"type": "none"}`.
- [ ] Precedence: per-run `context` > `context["realtime"]` > model config > defaults.
- [ ] Session payload includes the resolved `voice`, `modalities`, and normalized `turn_detection`.
- [ ] Backwards compatible: existing behavior unchanged when no new config provided.
- [ ] Unit tests cover validation and payload emission for all three fields (voice, modalities, turn_detection variants, and None).

## Non-goals
- Adding new transports (WebRTC) or non-Azure realtime providers.
- Dynamic updates mid-session beyond the initial `session.update` message.

## Design
- Extend `AzureOpenAIRealtime._send_session_config` to resolve and validate `voice`, `modalities`, and `turn_detection` using the same precedence as `instructions`.
- Implement small internal helpers:
  - `_resolve_opt(context, key, default)` to encapsulate precedence across `context` and `self._config`.
  - `_normalize_modalities(value)` -> list[str] where members ∈ {"text","audio"}.
  - `_normalize_turn_detection(value)` -> dict suitable for Azure: returns `{"type":"none"}` when value is `None`; passes through validated dicts for `server_vad` and `semantic_vad`; rejects unknown `type`.
- Payload shape remains compatible with Azure Realtime:
  - `session.modalities`: list of literals ["text", "audio"].
  - `session.voice`: string.
  - `session.turn_detection`: dict as above. If disabled via config `None`, we send `{ "type": "none" }` to be explicit.
- Allow per-run overrides via `context`:
  - Top-level keys: `context["voice"]`, `context["modalities"]`, `context["turn_detection"]`.
  - Or nested under `context["realtime"]` with same key names, e.g., `context["realtime"]["turn_detection"]`.
- Logging/observability: no prints; add debug events already captured by model; rely on existing runlog persistence.

## Impacted code
- `gotaglio/azure_openai_realtime.py`
  - `_send_session_config` — resolve and include `voice`, `modalities`, `turn_detection` with validation/normalization.
  - (Optional) add small private helpers for normalization.
- `tests/test_azure_openai_realtime.py`
  - Add unit tests for new configuration cases.
- `documentation/realtime.md`
  - Document configuration keys and examples.
- (Optional) `models.json.template`
  - Add example fields for `voice`, `modalities`, `turn_detection`.

## Edge cases and risks
- Invalid `modalities` values (e.g., ["video"]). We should raise `ValueError` with a clear message.
- Empty `voice` provided; treat as invalid and fall back to default or raise — choose to raise to avoid surprising API calls.
- `turn_detection` dict with unknown `type`; raise `ValueError`.
- `None` handling: normalize to `{ "type": "none" }` for Azure compatibility while documenting that users can set `null` to disable.
- Conflicts between top-level and nested `realtime` overrides; top-level wins by precedence.

## Test plan
- Unit tests:
  - [ ] Default behavior unchanged: `voice == "alloy"`, `modalities == ["text"]`, `turn_detection.type == "none"` in emitted session payload when none provided.
  - [ ] Override `voice` via model config and via `context`; verify in first `session.update` frame.
  - [ ] `modalities=["text","audio"]` via config; invalid value raises `ValueError`.
  - [ ] `turn_detection=None` disables detection (payload `{"type": "none"}`); `server_vad` and `semantic_vad` dicts are passed through with known fields.
  - [ ] Precedence: context override beats model config.
- Contract tests (no network): leverage existing dummy websocket in tests to capture first sent frame and assert payload.

## Migration/compat
- Fully backwards compatible. Defaults preserved. No schema changes required for existing pipelines.

## Rollout
- No feature flag. Expose via model config and per-run context patches.
- Add examples to `documentation/realtime.md` and `samples/realtime/` README.

## Tasks
- [ ] Implement normalization and precedence resolution in `AzureOpenAIRealtime._send_session_config`.
- [ ] Add unit tests for `voice`, `modalities`, `turn_detection` variants and None.
- [ ] Update docs and templates with examples.
- [ ] Optional: add schema/type hints/comments to guide users.

## Links
- Azure OpenAI Realtime docs (WebSocket): https://learn.microsoft.com/azure/ai-services/openai/realtime-websocket
- Existing code: `gotaglio/azure_openai_realtime.py`, `tests/test_azure_openai_realtime.py`
