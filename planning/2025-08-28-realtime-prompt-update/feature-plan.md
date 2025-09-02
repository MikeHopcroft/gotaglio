# Realtime prompt update via session.update (configured in pipeline)

## Problem
We need a first-class way to set and update the Azure OpenAI Realtime model's instructions (system prompt) from a pipeline configuration, and to support runtime updates via the `session.update` event. Today, the model hardcodes or ad-hoc builds instructions; pipelines can’t declaratively control the prompt or update it mid-run.

## Goals (acceptance criteria)
- [ ] Pipeline config defines initial instructions for the realtime session (e.g., `pipeline.prompt` or model-level `instructions`)
- [ ] The realtime model sends an initial `session.update` using instructions from pipeline config at connect time
- [ ] Provide a simple mechanism to trigger an additional `session.update` mid-session from a pipeline step (opt-in), with new instructions merged/overridden
- [ ] Events for session updates are captured in `context["realtime_events"]` with sequence and timestamp
- [ ] Backwards compatible: defaults maintain existing behavior when no instructions are provided

## Non-goals
- Multi-turn conversational orchestration (beyond the single audio upload flow)
- UI for editing prompts; this is CLI/pipeline-driven
- Advanced tool specification and tool execution (tools list can remain empty in MVP)

## Design
- Configuration
  - Prefer pipeline-level configuration for the prompt to align with existing patterns (e.g., `Pipeline.Prompt` or a `realtime.instructions` key). The model also accepts `instructions` in its model config; pipeline values override model defaults.
  - Optional runtime update key on context (e.g., `context["session_update_instructions"]`) to trigger a follow-up `session.update` after the first response is created or at a defined hook.
- Realtime flow
  - On connect, `_send_session_config` builds the body using `instructions` from pipeline/model config.
  - If `context["session_update_instructions"]` is present and non-empty, send a second `session.update` event at a deterministic point (e.g., immediately after `response.create` is sent) and capture an event entry.
- Event capture
  - Continue using `context["realtime_events"]` to store ordered events including both config updates.
- Logging/observability
  - Use standard logging, avoid prints; include minimal observability in events.

## Public API / CLI
- Pipeline config
  - `realtime.instructions`: string (initial instructions)
  - Optional: `realtime.session_update_instructions`: string (additional update applied mid-session)
- Model config
  - `instructions`: default instructions at model definition level (overridden by pipeline value)
- Behavior precedence
  - Context value > Pipeline step config > Model config default

## Impacted code
- `gotaglio/azure_openai_realtime.py`
  - `_send_session_config`: read instructions from context/pipeline/model; build and send payload
  - `infer`: optionally send a follow-up `session.update` if `context["session_update_instructions"]` present
- `gotaglio/pipeline.py` / `gotaglio/pipeline_spec.py`
  - Ensure pipeline can carry `realtime.instructions` and pass into the model context
- Documentation
  - `documentation/realtime.md`: add section on configuring and updating instructions
- Samples
  - `samples/realtime/`: example pipeline with instructions and an optional update

## Edge cases and risks
- Empty or excessively large instructions; truncate or send as-is (document limits)
- Conflicts when both model and pipeline provide instructions; clarify precedence
- Timing of mid-session update; sending too late may have no effect on the first response

## Test plan
- Unit tests
  - Initial `session.update` includes instructions from pipeline when provided
  - Fallback to model config when pipeline value is absent
  - When `context["session_update_instructions"]` is provided, a second `session.update` is sent and captured
  - No instructions provided: default behavior preserved
- Integration (optional)
  - With mocked WS, assert order: connect -> session.update (initial) -> audio append -> commit -> response.create -> session.update (optional) -> responses

## Migration/compat
- No breaking changes. Existing pipelines without instructions continue to work. Model defaults remain valid.

## Rollout
- No feature flag required. Document new pipeline keys and precedence.

## Tasks
- [ ] Add pipeline keys and documentation
- [ ] Update `_send_session_config` to source instructions from context/pipeline/model
- [ ] Add optional mid-session `session.update` hook in `infer`
- [ ] Add tests covering initial and mid-session update behavior
- [ ] Update documentation and samples

## Links
- Azure Realtime WebSocket: https://learn.microsoft.com/azure/ai-services/openai/realtime-websocket
- Existing planning: `planning/2025-08-26-azure-openai-realtime/`
