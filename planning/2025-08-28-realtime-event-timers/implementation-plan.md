# Implementation plan — Realtime event timers

This plan defines discrete, verifiable steps to add UTC timestamps and a monotonic elapsed timer to realtime events without changing other functionality.

## Pre-flight

- [ ] Confirm no new dependencies needed (use stdlib: time, datetime)
- [ ] Ensure no breaking API changes; fields are additive only

## Implementation

- [ ] Update `gotaglio/azure_openai_realtime.py` in `AzureOpenAIRealtime.infer`:
  - [ ] In the closure around `append_event`, add `audio_start_monotonic_ns: int | None = None`.
  - [ ] Modify `append_event(event: dict)` to:
    - [ ] Compute `timestamp` as today (existing behavior) and keep it.
    - [ ] Add `timestamp_utc` via `datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')`.
    - [ ] If `event['type'] == 'input_audio_buffer.append'` and `audio_start_monotonic_ns is None`, set baseline via `time.monotonic_ns()`.
    - [ ] Compute `elapsed_ms_since_audio_start` as `None` if baseline is not set; else `(time.monotonic_ns() - audio_start_monotonic_ns) // 1_000_000`.
    - [ ] Preserve existing `sequence` behavior.
- [ ] Do not modify websocket payloads or other logic.

## Validation

- [ ] Update `tests/test_azure_openai_realtime.py`:
  - [ ] In `test_infer_sends_expected_sequence_and_events`, assert each event has `timestamp_utc` (string) and `elapsed_ms_since_audio_start` key.
  - [ ] Assert pre-audio events have `elapsed_ms_since_audio_start is None`.
  - [ ] Assert the first `input_audio_buffer.append` has `elapsed_ms_since_audio_start == 0`.
  - [ ] In timeout test, ensure fields are present as well.

## Samples and documentation

- [ ] None required; behavior is internal to event logs.

## Rollout

- [ ] No dependency changes.
- [ ] No README changes required.
