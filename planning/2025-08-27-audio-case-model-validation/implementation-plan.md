# Implementation plan — Audio case vs model validation

## Pre-flight
- [ ] No new dependencies required.
- [ ] No lazy imports needed.
- [ ] Backward compatible; no feature flag.

## Implementation
- [ ] Add `AUDIO_INPUT_MODEL_TYPES = {"AZURE_OPEN_AI_REALTIME"}` to `gotaglio/constants.py`.
- [ ] In `Director`, add a new helper `validate_audio_cases_against_model(cases)` that:
  - reads pipeline config via `self._pipeline.get_config()`.
  - resolves `infer.model.name` to a model instance via `Registry` already bound in `Pipeline`/Director; either expose `self._pipeline._dag`-> no, prefer storing the `Registry` or pass it to validator. If not directly accessible, use `self._pipeline.get_config()` for the name, then rely on model registry which was created in Director's `__init__` (keep the `registry` as a field on Director).
  - inspects model `metadata()["type"]`.
  - checks if any case is audio: presence of the `audio` key on the case (string path or placeholder).
  - if any audio case and model type not in allowlist, raise ValueError.
- [ ] Call this validator from `process_all_cases` right after `validate_cases(cases)`.

## Validation
- [ ] Unit tests: create stub registry/model with metadata type to cover both allowed and disallowed paths, or use existing model types from `models.json` in a controlled test.
- [ ] Integration smoke: run `pytest -q` and ensure existing tests pass. Add new tests under `tests/`.

## Samples and documentation
- [ ] Keep `samples/realtime/data/cases.yaml` as-is (with `audio:`); optionally add a comment noting validation behavior.
- [ ] Update `documentation/realtime.md` with a short section on `audio` attribute based validation behavior.

## Rollout
- [ ] No manifest changes.
- [ ] No README changes required, optional link from docs.
