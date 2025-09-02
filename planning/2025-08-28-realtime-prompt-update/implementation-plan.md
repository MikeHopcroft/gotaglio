# Implementation plan — Realtime prompt update via session.update

## Pre-flight
- [x] Confirm where pipeline-level config flows into model context (inspect `pipeline.py`, `pipeline_spec.py`)
  - Findings: `Pipeline` passes `configuration` to `spec.create_dag(name, config, registry)`. Stage factories (e.g., `samples/realtime/realtime.py::stages`) close over `config` and populate `context` (e.g., `context["audio_file"]`). Models can read runtime keys from `context` (e.g., `AzureOpenAI` reads `context["model_settings"]`). We’ll pass prompt instructions via `context` (e.g., `context["instructions"]` and optionally `context["session_update_instructions"]`) from the stage using values in `config["realtime"]`.
- [x] No new dependencies needed; reuse existing `websockets` and logging
  - Findings: `pyproject.toml` already includes `websockets = "^12.0"`. Logging is available project-wide; we will replace the lone `print` in `azure_openai_realtime.py` with `logging.getLogger(__name__)` during implementation.
- [x] Ensure no breaking changes to model constructor or registration
  - Findings: `gotaglio/models.py::register_models` constructs `AzureOpenAIRealtime(registry, model)` when `type == "AZURE_OPEN_AI_REALTIME"`. Our changes are internal to the class (config sourcing and optional extra `session.update`) and do not alter the constructor or registration.

## Implementation
- [ ] `_send_session_config`:
  - [ ] Resolve instructions by precedence: `context.get("instructions")` or `context.get("realtime", {}).get("instructions")` (pipeline), else `self._config.get("instructions")`, else current default behavior
  - [ ] Preserve existing options (voice, modalities, formats)
  - [ ] Send `session.update` payload
- [ ] `infer` mid-session update:
  - [ ] After sending `response.create`, check `context.get("session_update_instructions")` or `context.get("realtime", {}).get("session_update_instructions")`
  - [ ] If present and non-empty, send a second `session.update` with only the `instructions` field (or full session body) and append an event
- [ ] Event capture
  - [ ] Reuse existing `append_event` to record `session.update` sends (already done for the initial one); add a separate marker for the mid-session update
- [ ] Logging
  - [ ] Use `logging.getLogger(__name__)`; remove any stray prints in this path

## Validation
- [ ] Unit tests in `tests/test_azure_openai_realtime.py` or new test file
  - [ ] Test initial instructions precedence (context > pipeline key > model config > default)
  - [ ] Test that a mid-session update is sent when configured
  - [ ] Test that no update is sent when not configured
- [ ] Run `pytest -q`

## Samples and documentation
- [ ] Update `documentation/realtime.md` with instructions section
- [ ] Add example in `samples/realtime/` showing pipeline config with `realtime.instructions` and optional `realtime.session_update_instructions`

## Rollout
- [ ] No dependency updates required
- [ ] Note precedence in `README.md` if relevant
