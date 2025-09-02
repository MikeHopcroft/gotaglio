# Feature: Validate audio test cases use an audio-capable model

## Problem
When a test case provides direct audio input (e.g., samples/realtime/data/cases.yaml with an `audio:` field), the run should fail fast if the configured model cannot consume raw audio. Today, only `AZURE_OPEN_AI_REALTIME` supports direct audio input. There is no validation and users may accidentally run audio cases against text-only models, leading to confusing runtime errors.

## Goals (acceptance criteria)
- [ ] Detect audio cases by the presence of an `audio` attribute in the case (e.g., `audio: "path.wav"`).
- [ ] When any case has an `audio` attribute, validate that the configured model is in the allowlist of audio-capable model types.
- [ ] For now, the allowlist contains only `AZURE_OPEN_AI_REALTIME`.
- [ ] Clear, actionable error message citing the bad model name and allowed types; occurs before any network calls.
- [ ] Backward compatible: existing non-audio cases and pipelines continue to run unchanged.

## Non-goals
- Audio format conversion/validation (sample rate, channels, encoding).
- Expanding support to other providers/models (future work).
- Changing pipeline stage contracts.

- ## Design
- Case schema:
  - Optional field on a case: `audio: <string>` where the value is a file path or placeholder (e.g., `{audio_file}`) that the pipeline will resolve.
  - Audio detection is based solely on the presence of the `audio` attribute; no new `type` property is introduced.
- Validation hook:
  - Add a new validation in `Director.process_all_cases` via `validate_cases(cases)` or a new helper, executed after cases are loaded but before DAG execution.
  - The validator needs access to the configured model for the current pipeline. We can do this in two ways:
    1) Pass the active Pipeline config into `validate_cases` or
    2) Add a new `validate_cases_against_config(cases, pipeline_config, registry)` method in `Director` and call it before running.
  - Use `Registry.model(name)` to resolve the model instance and inspect its declared type/capabilities. The model type is in the model config available from `model.metadata()` or the original configuration stored by model wrappers.
- Capability detection:
  - Introduce a minimal capability predicate on model instances, e.g., a method `supports_audio_input()` on `Model` with default `False`, overridden by `AzureOpenAIRealtime` to return `True`.
  - Alternatively (lower-touch), inspect `model.metadata()["type"]` and check membership in a static allowlist `{ "AZURE_OPEN_AI_REALTIME" }`. Start with metadata approach to avoid changing base class; keep method hook as a future enhancement.
- Error surface:
  - Raise `ValueError` with message: "Audio case requires an audio-capable model. Configured model '<name>' (type '<type>') is not in allowed types: AZURE_OPEN_AI_REALTIME."
- Extensibility:
  - Centralize allowlist in `gotaglio/constants.py` as `AUDIO_INPUT_MODEL_TYPES = {"AZURE_OPEN_AI_REALTIME"}` so future additions are one line.

## Impacted code
- `gotaglio/director.py`: extend `validate_cases` (or add a sibling function) to perform audio-case vs model-type validation given the active pipeline config and registry access via the Pipeline/Director.
- `gotaglio/pipeline.py`: no change to stages; ensure `Pipeline.get_config()` remains available for model name lookup `infer.model.name`.
- `gotaglio/registry.py`: no change; used to resolve model instance by name.
- `gotaglio/models.py` and `gotaglio/azure_openai_realtime.py`: ensure `metadata()` includes `type` so validator can read it (it does already).
- `gotaglio/constants.py`: add `AUDIO_INPUT_MODEL_TYPES` set.
- `samples/realtime/data/cases.yaml`: keep using the `audio:` attribute (no `type` field added).
- `tests/`: add unit tests:
  - happy path: audio case + AZURE_OPEN_AI_REALTIME model passes validation.
  - failure: audio case + non-realtime model raises before run.
  - back-compat: case with `audio:` but no `type` still validated as audio.

## Edge cases and risks
- Mixed suites: both audio and non-audio cases. Validation should require audio-capable model if any case is audio; or we validate per-case at execution time. For simplicity and clearer UX, fail upfront if any case is audio and model is not audio-capable.
- Missing model configuration: raise the existing configuration error paths first; do not mask them.

## Test plan
- Unit tests in `tests/` exercising validation function directly via a minimal Director/Pipeline setup (mock Registry with a stub model exposing metadata type).
- Integration: run `samples/realtime` pipeline with `azure-realtime` to ensure no validation error; and run it with a text-only model (e.g., `gpt4o`) expecting fast failure.

## Migration/compat
- No schema change. Existing cases with `audio:` gain early validation.

## Rollout
- No feature flags; the behavior is validation-only.
- Log remains unchanged. Error raised before network IO.

## Tasks
- [ ] Add `AUDIO_INPUT_MODEL_TYPES` constant.
- [ ] Implement validation in Director with access to pipeline config.
- [ ] Tests for happy path and failure scenarios based on presence of `audio`.
- [ ] Docs: update `documentation/realtime.md` to mention `audio`-based validation.

## Links
- Planning templates in `planning/`
- Current realtime model wrapper: `gotaglio/azure_openai_realtime.py`
- Samples: `samples/realtime`
