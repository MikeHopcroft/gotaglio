# Implementation plan — Azure OpenAI Realtime model

This plan defines discrete, verifiable steps for the agent to implement the feature. Check off each step as it’s completed.

## Pre-flight
- [x] Confirm dependencies: choose `websockets` (or `aiohttp`) for WS client; add to `pyproject.toml`
- [x] Verify lazy import pattern in `gotaglio/lazy_imports.py` and add import for chosen client
- [x] Ensure no step-type changes are required (model-based implementation only)

## Model implementation
- [x] Create `AzureOpenAIRealtime` class in `gotaglio/models.py`
  - [x] Constructor stores config, registers model by name
  - [x] `metadata()` returns config without secrets
  - [x] `async infer(messages, context=None) -> str` implemented
- [x] Input resolution in `infer`
  - [x] Accept `context["audio_file"]` or `context["audio_bytes"]`
  - [x] Read file bytes if path provided; error if neither present
- [x] Connection details
  - [x] Build WS URL from `endpoint`, `api` (api-version), and `deployment`
  - [x] Send `api-key` header
- [x] Session setup and streaming
  - [x] Optionally send `session.update` with `voice` and `modalities`
  - [x] Send `input_audio_buffer.start` with `sample_rate_hz`
  - [x] Transmit audio bytes (single chunk MVP)
  - [x] Send `input_audio_buffer.commit`
  - [x] Send `response.create`
- [x] Receive loop and event capture
  - [x] Append ordered events with `sequence`, `type`, `ts`, `payload`
  - [x] Accumulate `final_text` from `response.delta` events
  - [x] Stop on `response.completed` or `session.completed` (or timeout)
  - [x] Attach events to `context["realtime_events"]`
- [x] Error handling
  - [x] Timeout handling with partial events annotated
  - [x] Add structured error event on exceptions

## Registration
- [x] Update `register_models` in `gotaglio/models.py` to handle `AZURE_OPEN_AI_REALTIME`

## Samples and docs
- [x] Add `samples/realtime/` with a small WAV file and a sample pipeline stage calling the model (README and cases.json added; user to add WAV)
- [x] Add `documentation/realtime.md` describing configuration, case placeholder, and CLI usage

## Tests
- [x] Unit tests using a mocked WS client
  - [x] Happy path: connect, send audio, receive deltas and completed
  - [ ] Timeout path: ensure partial events and error recorded (deferred)
  - [x] Missing audio: raise validation error
  - [ ] Event order: strictly increasing `sequence` (implicitly checked by append order; explicit assertion deferred)
- [x] Ensure tests run via `pytest -q`

## Integration and telemetry
- [ ] Ensure logs flow through Python logging; no prints
- [ ] Optional: persist events to JSONL in a stage helper using `shared.write_log_file`

## Rollout
- [ ] Add `websockets` (or `aiohttp`) to `pyproject.toml`
- [ ] Note feature flag `GOTAGLIO_ENABLE_REALTIME` (if applicable)
- [ ] Update `README.md` or `documentation/realtime.md`
