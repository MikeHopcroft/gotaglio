# Feature: Configurable Realtime session (voice, turn_detection, modalities)

Summary
- Enable configuration of `voice`, `modalities`, and `turn_detection` for Azure OpenAI Realtime sessions, with validation and clear precedence rules. This allows audio output, voice selection, and server-side VAD controls per model and per run.

Motivation
- Current implementation hardcodes `voice` ("alloy"), `modalities` (["text"]) and `turn_detection` ("none"). Users need to enable audio modalities, customize voice, and control turn detection (server_vad/semantic_vad) including disabling it. This unlocks richer realtime experiences and aligns with Azure Realtime capabilities.

Acceptance criteria
- [ ] Model accepts and validates config for `voice`, `modalities`, and `turn_detection` via model config and per-run context overrides.
- [ ] Modalities limited to ["text", "audio"]; validation errors on invalid entries.
- [ ] Voice must be a non-empty string when provided.
- [ ] turn_detection supports `server_vad` (threshold, prefix_padding_ms, silence_duration_ms, create_response, interrupt_response), `semantic_vad` (eagerness, create_response, interrupt_response), or `None` to disable.
- [ ] Precedence: context > context.realtime > model config > defaults.
- [ ] Emitted session.update reflects resolved values; `None` maps to `{ "type": "none" }`.
- [ ] Unit tests cover defaults, overrides, invalid inputs, and precedence.

Scope
- Update `AzureOpenAIRealtime._send_session_config` and add small private helpers to resolve and validate options.
- Update tests to assert payload contents.
- Update docs and templates (models.json.template and documentation/realtime.md) with examples.

Out of scope
- WebRTC transport; non-Azure realtime providers; mid-session dynamic updates beyond initial `session.update`.

Design overview
- Resolve options with precedence: top-level context > context["realtime"] > model config > defaults.
- Normalize modalities to an order-preserving, duplicate-free list containing only "text" and/or "audio".
- Normalize turn_detection: dicts for `server_vad`/`semantic_vad` pass through known keys; `None` -> `{ "type": "none" }`; unknown `type` -> ValueError.

Impacted code
- `gotaglio/azure_openai_realtime.py` — helper functions + `_send_session_config` updates
- `tests/test_azure_openai_realtime.py` — new tests
- `documentation/realtime.md`, `models.json.template` — examples and guidance

Tasks
- [ ] Implement `_resolve_opt`, `_normalize_modalities`, `_normalize_turn_detection`
- [ ] Update `_send_session_config` to include normalized values
- [ ] Add unit tests for defaults, overrides, precedence, and invalid inputs
- [ ] Update docs and templates
- [ ] Update planning README index

Test plan
- Use dummy websocket tests to inspect the first `session.update` frame.
- Cases for: default payload; voice override; modalities override valid/invalid; turn_detection None/server_vad/semantic_vad; precedence behaviors.

Risks and mitigations
- Invalid configs: raise clear ValueError to fail fast.
- Backward compatibility risk: defaults unchanged when no new config provided.

Definition of Done
- Tests passing; docs/templates updated; feature plans committed; emitted payloads include the configured fields; backward-compatible behavior maintained.
