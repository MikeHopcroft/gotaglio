# Realtime prompt update via session.update (pipeline-configurable)

Summary
Add first-class support to configure and update the Azure Realtime model’s instructions (system prompt) from the pipeline. Send the initial instructions via `session.update` at connect time, and optionally send a mid-session `session.update` when requested. Capture session update events in the run context for observability.

Motivation
Pipelines need deterministic, declarative control over the realtime model’s prompt, not hardcoded defaults. Configurable instructions improve reproducibility and enable prompt changes between runs or even mid-session without code edits.

Acceptance criteria
- [ ] Pipeline can define initial instructions for the realtime session (e.g., `context["realtime"]["instructions"]` or equivalent pipeline key)
- [ ] Model sends an initial `session.update` at connect time using instructions with clear precedence
- [ ] Optional mid-session `session.update` can be triggered by a context/pipeline value (e.g., `context["session_update_instructions"]` or `context["realtime"]["session_update_instructions"]`)
- [ ] All session update sends are captured in `context["realtime_events"]` with sequence and timestamp
- [ ] Backward compatible: when no instructions provided, current behavior remains (no breaking changes)

Scope
- Resolve instructions: context > pipeline key > model config > default
- Send initial `session.update` in `_send_session_config`
- Optionally send a second `session.update` after `response.create` when configured
- Capture both updates in the events list
- Update docs and add tests

Out of scope
- Multi-turn conversational orchestration
- Tool execution and configuration
- UI for editing prompts (CLI/pipeline only)

Design overview
- Instructions resolution precedence:
  1. `context.get("instructions")` or `context.get("realtime", {}).get("instructions")`
  2. `self._config.get("instructions")`
  3. Existing default behavior (env/template fallback)
- Initial `session.update` sent in `_send_session_config` using resolved instructions
- Optional mid-session `session.update`:
  - After sending `response.create`, if `context.get("session_update_instructions")` (or `context["realtime"]["session_update_instructions"]`) is present, send a second `session.update` with updated instructions
- Event capture:
  - Reuse existing event capture; ensure an event is appended whenever `session.update` is sent

Impacted code
- `gotaglio/azure_openai_realtime.py`
  - `_send_session_config`: include resolved instructions in payload
  - `infer`: conditionally send a second `session.update`; record events
  - Replace prints with `logging.getLogger(__name__)`
- Documentation
  - `documentation/realtime.md`: configuration keys, precedence, optional mid-session update
- Samples
  - `samples/realtime/`: example using pipeline-configured instructions and optional update
- Tests
  - `tests/test_azure_openai_realtime.py`: precedence and `session.update` behavior

Tasks
- [ ] Wire instruction resolution in `_send_session_config` (context > pipeline key > model config > default)
- [ ] Add optional mid-session `session.update` in `infer` after `response.create` when configured
- [ ] Ensure events are appended for each `session.update` send
- [ ] Replace print statements with logging
- [ ] Tests:
  - [ ] Initial `session.update` includes pipeline instructions when provided
  - [ ] Fallback to model config when pipeline is absent
  - [ ] No instructions provided => default behavior preserved
  - [ ] Mid-session update is sent and captured when configured; not sent otherwise
- [ ] Docs: add/update section in `documentation/realtime.md`
- [ ] Sample: update `samples/realtime/` with a minimal example

Test plan
- Unit tests (mock websocket):
  - Assert initial `session.update` payload contains expected instructions by precedence
  - Assert optional mid-session `session.update` is sent and captured when configured
  - Assert no mid-session update when not configured
  - Assert event ordering and the presence of `session.update` entries in `context["realtime_events"]`
- Optional integration test (skipped without creds) to validate event sequence with a small audio input

Risks and mitigations
- Timing of mid-session update may not affect the first response: document behavior and timing; send immediately after `response.create`.
- Conflicting instruction sources: precedence rules avoid ambiguity.
- Large instructions: rely on service limits; document recommended sizes.

Definition of Done
- Feature implemented with tests passing (`pytest -q`)
- Docs and sample updated
- No prints in code path; uses logging
- Backward compatibility preserved
