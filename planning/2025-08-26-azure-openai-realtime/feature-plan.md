# Support Azure OpenAI Realtime API in pipelines

## Problem
We need to run speech-in/speech-out and streamed text/audio interactions against Azure OpenAI Realtime API from a gotaglio pipeline. The API streams many event types over WebSocket or WebRTC. Today, gotaglio lacks a first-class pipeline step that:
- Accepts local audio input (file/bytes/stream)
- Initiates a Realtime session (WS first; optional WebRTC later)
- Sends audio and receives streamed events
- Captures and persists all events for assessment/analysis
- Exposes a simple contract for downstream steps and CLI users

## Goals (acceptance criteria)
- [ ] New Model class in `gotaglio/models.py` (e.g., `AzureOpenAIRealtime`) that performs realtime inference against Azure OpenAI over WebSocket (MVP)
- [ ] Input: audio file path or bytes (16 kHz mono PCM/WAV/MP3/Opus; document supported codecs)
- [ ] Output: final transcript text return value; complete ordered list of raw streamed events captured onto the `context` for assessment
- [ ] Capture 100% of event frames/messages with timestamps and types for assessment
- [ ] Config via model options: endpoint, api version, deployment, key/credential, timeouts, sampling rate, optional voice/modalities
- [ ] Works within existing pipelines by calling the model from a DAG stage (no new pipeline step type required)
- [ ] Graceful handling of reconnects/timeouts; partial session captured with error metadata
- [ ] Unit tests with mocked WebSocket; deterministic event capture ordering
- [ ] CLI example and sample stage that calls the model
- [ ] Leverage existing gotaglio conventions: standard logging via `logging.getLogger(__name__)`, run logs via `Director`/`shared.write_log_file`, case structure and CLI key=value patches

## Non-goals
- Full WebRTC support in MVP (plan and interface slots included, implemented later)
- Browser client or UI; this is headless pipeline integration
- Multi-turn session orchestration beyond single audio input (can extend later)

## Design

### High-level flow
1. Resolve model configuration (Azure endpoint, api-version, deployment, key)
2. Open Realtime connection (WebSocket MVP)
3. Initialize session parameters (voice, modalities, transcription settings)
4. Stream or upload audio content
5. Receive streamed events; normalize to internal `RealtimeEvent` records and append to `EventCapture`
6. Derive convenience outputs: final transcript, final text response(s), optional audio output references if provided by API
7. Close connection and return `RealtimeResult`

### Public model API
- Class: `AzureOpenAIRealtime` (registered by `register_models` when `type` is `AZURE_OPEN_AI_REALTIME`)
- Config fields:
  - `endpoint`, `api` (api-version), `deployment`, `key`
  - Optional: `sample_rate_hz` (default 16000), `timeout_s` (default 60), `voice`, `modalities`
- Methods:
  - `async infer(messages, context=None) -> str`
    - Messages ignored for realtime audio; use `context` to pass `audio_file` or `audio_bytes`
    - Returns final transcript text (or "" if none). Captured events attached to `context["realtime_events"]`.
  - Optional convenience: `async realtime_infer(audio_file: str, **opts) -> str` delegating to `infer`
- Event capture contract:
  - Model attaches a list of normalized events at `context["realtime_events"]` in arrival order; each event has `sequence`, `type`, `ts`, and `payload`.

### Integration with gotaglio conventions
- Logging
  - Use `logging.getLogger(__name__)` consistent with `endpoints/realtime.py`
  - Avoid prints; surface high-level run details through `Director` runlog and persist via `shared.write_log_file`
- CLI
  - Reuse existing `gotaglio/subcommands/run_cmd.py` flow; no new top-level commands
  - Accept config via key=value patches (e.g., `realtime.audio_file=...`), leveraging `Pipeline.Prompt` where needed
- Test cases
  - Cases are `list[dict]` with required `uuid`; turns supported via `case["turns"]`
  - Define a placeholder for input audio file in cases; resolve from pipeline configuration provided via CLI patches

### Data structures
- RealtimeEvent
  - `type`: str (e.g., "session.created", "response.delta", "response.completed", "input_audio.buffer.committed", "error")
  - `ts`: float (monotonic or utc iso string)
  - `payload`: dict (raw event content)
  - `sequence`: int (incremental index for ordering)
- EventCapture
  - Methods: `append(event)`, `to_jsonl(fp)`, `summary()`
- RealtimeResult
  - Aggregates events and derived fields (transcript, responses)

### Transport inside model
- MVP: WebSocket using a lightweight async client (e.g., `websockets`) implemented inside the model class
- Optional future: WebRTC using `aiortc` (behind feature flag), still encapsulated in the model

### Authentication
- Azure OpenAI Realtime requires the Azure resource endpoint, API version, and either API key or AAD bearer token
- Support API key via `AZURE_OPENAI_API_KEY` or model-level `key` resolved from env

### Event normalization
- Maintain received order using a local `sequence` counter
- Add `received_at` timestamp for latency analysis
- Preserve raw payload for later parsing; derive transcript/responses using event types defined by Azure Realtime

### Persistence
- Model will attach events to `context` for inclusion in run logs; a calling stage may also persist events to JSONL (optional `save_events_path` in pipeline config)
- Optional: store audio copy into sibling folder for reproducibility

### Error handling
- Timeouts: cancel send/recv tasks, return partial events with `meta.error`
- Protocol errors: include last event and server error payloads
- Network errors: retry connect once (configurable), annotate in `meta`

### CLI example
- Example run via existing CLI `gotag run` with cases file and a DAG stage that calls the model

### Case schema (placeholder for input file)
- Single-turn case example:
  - `{ "uuid": "...", "audio": "{audio_file}", "answer": "<optional expected>" }`
- Multi-turn case example:
  - `{ "uuid": "...", "turns": [ { "audio": "{audio_file}" } ] }`
- Placeholder resolution:
  - The calling stage will substitute `{audio_file}` from pipeline config key `realtime.audio_file`
  - Provide at runtime with CLI patch: `realtime.audio_file=path/to/file.wav`
  - If the case specifies a concrete path, it takes precedence; if missing and no config provided, raise a clear error

## Impacted code
- `gotaglio/models.py`: add `AzureOpenAIRealtime` model class and any helper DTOs
- `gotaglio/models.py::register_models`: support type `AZURE_OPEN_AI_REALTIME`
- `samples/` and `documentation/`: add sample stage and docs
- Optional: a small utility in a stage to persist `context["realtime_events"]` to JSONL using `shared.write_log_file`

## Edge cases and risks
- Large audio files causing long send times or server-side truncation
- Unsupported codecs or sample rates; require conversion (follow-up: ffmpeg/sox integration)
- Clock skew in timestamps; we use local receive time for ordering
- Partial sessions due to disconnects; ensure events flushed to disk
- Secrets handling in logs; scrub keys and auth headers
- Azure deployment model differences (region, apiVersion variability)

## Test plan
- Unit tests (mocked transport):
  - Connect -> send audio -> receive deterministic sequence of events -> verify `events`, `transcript`, `responses`
  - Timeout path returns partial events and proper meta
  - Persistence: JSONL written and loadable
  - Case placeholder expansion: case with `"audio": "{audio_file}"` resolves using CLI patch `realtime.audio_file=...`
- Integration tests (optional, skipped w/o creds):
  - Real connect to Azure with short sample audio; verify at least basic event flow
- Contract tests:
  - Validation errors when audio input missing in context

## Migration/compat
- Backwards compatible; implemented as an additional model type. No breaking changes.
- Env vars: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT` (usable defaults when not specified at model config)

## Rollout
- Feature flag: `GOTAGLIO_ENABLE_REALTIME` (default on if deps available)
- Log metrics: total events, bytes sent/received, duration, error count
- Docs: add `documentation/realtime.md` and sample pipeline
- Dependencies: add `websockets` (or `aiohttp`) to project deps

## Example usage in a stage (illustrative)
```python
from gotaglio.pipeline_spec import get_turn

async def realtime_stage(context):
    turn = get_turn(context)
    audio = turn.get("audio")  # may be "{audio_file}" placeholder
    # Resolve placeholder from pipeline config (not shown here)
    model = context["registry"].model("azure-realtime")  # name from models.json
    transcript = await model.infer(messages=[], context={"audio_file": audio})
    # Attach transcript to stage result; events are in context["realtime_events"]
    return {"transcript": transcript, "events_count": len(context.get("realtime_events", []))}
```

CLI usage example (placeholder via CLI patches):

```bash
gotag run my-pipeline \
  --cases cases/realtime.json \
  realtime.audio_file=samples/audio/hello.wav
```

## Tasks
- [ ] Define DTOs: `RealtimeEvent` (normalized event), optional capture helper
- [ ] Implement model `AzureOpenAIRealtime` (WS MVP): connect, send audio, receive events, normalize, capture on context
- [ ] Register in `register_models` for type `AZURE_OPEN_AI_REALTIME`
- [ ] Sample audio and example pipeline stage under `samples/realtime/`
- [ ] Docs page `documentation/realtime.md`
- [ ] Unit tests with transport mocks; contract tests for missing audio
- [ ] Optional (follow-up): WebRTC transport via `aiortc`

## Links
- Azure OpenAI Realtime: https://learn.microsoft.com/azure/ai-services/openai/realtime-overview
- Example event types: https://learn.microsoft.com/azure/ai-services/openai/realtime-websocket
- Gotaglio files: `gotaglio/pipeline.py`, `gotaglio/pipeline_spec.py`, `gotaglio/models.py`, `gotaglio/registry.py`
