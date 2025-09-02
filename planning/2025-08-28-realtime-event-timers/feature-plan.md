# Realtime event timers — Feature plan

## Problem

Realtime events emitted by `AzureOpenAIRealtime.infer` currently include only a floating epoch `timestamp` added at append-time. We lack:
- A standard UTC timestamp string for human-friendly logs and cross-system correlation.
- A consistent latency metric relative to when audio streaming started. Today, there is no monotonic elapsed timer to compare the timing of commit, response.create, and response.* events to the start of audio.

This makes it harder to reason about ordering, latency, and regressions in end-to-end timing.

## Goals (acceptance criteria)

- Every event captured in `context["realtime_events"]` includes a `timestamp_utc` field in ISO 8601/RFC 3339 UTC (e.g., `2025-08-28T17:20:45.123456Z`).
- Introduce a monotonic baseline taken the moment we append the first `input_audio_buffer.append` event, and add `elapsed_ms_since_audio_start` to every subsequent event.
  - For the first audio append event, `elapsed_ms_since_audio_start == 0`.
  - For events appended before audio starts streaming, `elapsed_ms_since_audio_start` is `None` (field present, value null in JSON).
- Do not change any other functionality or event sequencing. Maintain existing `timestamp` (float seconds since epoch) and `sequence` numbering.
- No changes to the websocket payloads sent to the service.

## Non-goals

- Introducing new event types or changing event order.
- Changing audio handling, conversion behavior, or session configuration.
- Multi-chunk audio handling; we only baseline on the first append per current MVP.

## Design

- Scope the change to the local `append_event` helper inside `AzureOpenAIRealtime.infer`.
- Maintain current float `timestamp` field for backward compatibility.
- Add two fields on every event when appended:
  - `timestamp_utc`: timezone-aware UTC in ISO 8601 with trailing `Z`.
  - `elapsed_ms_since_audio_start`: integer milliseconds since first audio append using `time.monotonic_ns()`. Before the first audio append, set to `None`.
- Determine the start moment by detecting when `event.get("type") == "input_audio_buffer.append"` is being appended; capture and store `audio_start_monotonic_ns` the first time this occurs.
- Keep implementation local to `azure_openai_realtime.py`; no external dependencies.

Data shape additions to each event record:
- `timestamp_utc: str`
- `elapsed_ms_since_audio_start: int | None`

## Impacted code

- `gotaglio/azure_openai_realtime.py`
  - Inner function `append_event` in `AzureOpenAIRealtime.infer`: add UTC timestamp and monotonic elapsed fields; track `audio_start_monotonic_ns` in closure.
- `tests/test_azure_openai_realtime.py`
  - Add assertions ensuring new fields exist with expected semantics.

## Edge cases and risks

- Events that occur before audio append (e.g., `audio.resolved`, `debug.ws`, `session.connected`, `session.update`) get `elapsed_ms_since_audio_start = None`.
- Timeout or error paths still include new fields.
- Only the first `input_audio_buffer.append` sets the baseline; subsequent ones (if ever introduced) won’t reset it in this MVP.
- `time.monotonic_ns()` is monotonic but not related to wall time; that’s intended for elapsed calculations.

## Test plan

- Update existing realtime tests or add a new one to validate:
  - All captured events contain `timestamp_utc` (str) and `timestamp` (float) fields.
  - `elapsed_ms_since_audio_start` is `None` for pre-audio events; `0` for the first append; and non-negative integers thereafter.
  - No changes to websocket send payloads or event types captured.
  - Works in timeout path.

## Migration/compat

- Backward compatible: the original `timestamp` remains and event shape only grows.
- No config changes or feature flags required.

## Rollout

- Unit-test only; no runtime configuration.
- Monitor via existing tests; no telemetry changes.

## Links

- `gotaglio/azure_openai_realtime.py`
- `tests/test_azure_openai_realtime.py`
