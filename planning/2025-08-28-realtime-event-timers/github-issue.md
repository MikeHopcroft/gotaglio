# Realtime: Add UTC timestamps and monotonic elapsed timer to events

Summary

Add `timestamp_utc` and `elapsed_ms_since_audio_start` to all events captured by `AzureOpenAIRealtime.infer`, keeping existing `timestamp` and without changing any other behavior.

Motivation

- Improve observability and correlation across systems.
- Provide consistent latency metrics from the moment audio begins streaming to subsequent events.

Acceptance criteria

- All events include `timestamp_utc` (ISO 8601 UTC string) and `elapsed_ms_since_audio_start` (ms or null).
- First audio append sets the monotonic baseline; it reports 0ms. Pre-audio events report null.
- Websocket payloads, event ordering, sequence numbers, and other functionality remain unchanged.

Scope

- Localized changes inside `gotaglio/azure_openai_realtime.py` event appending logic.
- Unit tests updated to assert new fields.

Out of scope

- Changing modalities, audio conversion, or session configuration logic.
- Multi-chunk audio support enhancements.

Design overview

- Use `datetime` for UTC timestamps and `time.monotonic_ns()` for elapsed measurement.
- Detect first `input_audio_buffer.append` to set baseline and compute elapsed for subsequent events.

Impacted code

- `gotaglio/azure_openai_realtime.py`: modify `append_event` closure and add baseline variable.
- `tests/test_azure_openai_realtime.py`: assertions for new fields.

Test plan

- Extend existing tests to check for the presence and correctness of the new fields, including timeout path.

Risks and mitigations

- Minimal risk; fields are additive. Ensure not to mutate outbound frames.

Definition of Done

- All tests pass; events contain the new fields with correct semantics; no functional regressions.
