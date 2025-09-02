# Azure OpenAI Realtime (WebSocket) — gotaglio integration

This document describes how to use the Azure OpenAI Realtime API (WebSocket) through a gotaglio model.

## Overview
- Model type: `AZURE_OPEN_AI_REALTIME`
- Class: `AzureOpenAIRealtime` (in `gotaglio/models.py`)
- Input: audio file path or bytes via `context`
- Output: transcript string and captured events at `context["realtime_events"]`

## Configuration
Add a model entry in your models configuration file (see `models.json`/credentials setup):

```jsonc
{
  "name": "azure-realtime",
  "type": "AZURE_OPEN_AI_REALTIME",
  "endpoint": "${AZURE_OPENAI_ENDPOINT}",
  "api": "2024-06-01",
  "deployment": "gpt-4o-realtime-preview",
  "key": "${AZURE_OPENAI_API_KEY}",
  "sample_rate_hz": 16000,
  "timeout_s": 45,
  "voice": "alloy",
  "modalities": ["text", "audio"]
}
```

Environment variables are recommended for secrets.

## Using in a stage

```python
from gotaglio.pipeline_spec import get_turn

async def realtime_stage(context):
    turn = get_turn(context)
    audio = turn.get("audio")  # may be a placeholder like "{audio_file}"
    # Resolve placeholder from pipeline config (not shown here)
    model = context["registry"].model("azure-realtime")
    transcript = await model.infer(messages=[], context={"audio_file": audio})
    # Events available at context["realtime_events"]
    return {"transcript": transcript, "events_count": len(context.get("realtime_events", []))}
```

## Cases and placeholders
- Single-turn: `{ "uuid": "...", "audio": "{audio_file}" }`
- Multi-turn: `{ "uuid": "...", "turns": [ { "audio": "{audio_file}" } ] }`
- Provide placeholder value via CLI patches: `realtime.audio_file=path/to/file.wav`

## CLI example

```bash
gotag run my-pipeline \
  --cases cases/realtime.json \
  realtime.audio_file=samples/audio/hello.wav
```

## Troubleshooting
- Timeout: Increase `timeout_s`; check network/firewall for WebSocket egress
- No transcript: Verify deployment supports realtime and you sent valid audio
- Event capture: Inspect `context["realtime_events"]` in run logs; persist as JSONL in a stage if needed
