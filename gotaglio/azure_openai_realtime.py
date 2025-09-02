from typing import Any
import logging

# Import Model from models; this works because models defines Model before importing us
from .models import Model  # type: ignore
from .lazy_imports import websockets


class AzureOpenAIRealtime(Model):
    """
    Azure OpenAI Realtime (WebSocket) model wrapper for streaming audio input and
    capturing streamed events. MVP uses WebSocket transport only.

    Expected config keys:
    - name: str
    - type: "AZURE_OPEN_AI_REALTIME"
    - endpoint: Azure resource endpoint (e.g., https://<resource>.openai.azure.com)
    - api: api version (e.g., 2024-06-01)
    - deployment: realtime-capable deployment name (e.g., gpt-4o-realtime-preview)
    - key: API key
    Optional:
    - sample_rate_hz: default 16000
    - timeout_s: default 60
    - voice: optional voice name
    - modalities: optional list, e.g., ["text", "audio"]
    - convert_to_pcm16: bool, default False; if True, send audio as PCM16 mono 24kHz
    """

    def __init__(self, registry, configuration):
        self._config = configuration
        registry.register_model(configuration["name"], self)

    async def infer(self, messages, context=None):
        """
        `messages` are ignored for realtime audio; use `context` for:
          - context["audio_file"]: path to audio file to send
          - context["audio_bytes"]: raw audio bytes
        Returns a best-effort final text response. Also attaches captured events to
        context under `context["realtime_events"]`.
        """
        # Resolve inputs
        audio_bytes = None
        audio_path = None
        if context is not None:
            audio_bytes = (context or {}).get("audio_bytes")
            audio_path = (context or {}).get("audio_file")

        if audio_bytes is None and audio_path:
            with open(str(audio_path), "rb") as f:
                audio_bytes = f.read()

        if not audio_bytes:
            raise ValueError(
                "AzureOpenAIRealtime.infer requires audio_file or audio_bytes in context"
            )

        timeout_s = float(self._config.get("timeout_s", 60))

        # Event capture
        events: list[dict[str, Any]] = []
        seq = 0
        # Monotonic baseline captured when audio first starts streaming (first append)
        audio_start_monotonic_ns: int | None = None

        def create_event(ev_type: str) -> dict:
            return {"type": ev_type}
        
        def create_error_event(ev_type: str,error_message):
            ev=create_event(ev_type)
            ev["message"]=error_message
            return ev

        def create_audio_event(ev_type: str, audio_bytes: bytes) -> dict:
            """Create a REDACTED audio event for logs.
            We intentionally do NOT include the raw/base64 audio in the event log.
            """
            return {"type": ev_type, "size": len(audio_bytes), "redacted": True}

        def create_response_event(ev_type: str, message=None) -> dict:
            ev = create_event(ev_type)
            if message is not None:
                ev["message"] = message
            return ev

        async def append_event(event: dict):
            nonlocal seq, audio_start_monotonic_ns
            record = dict(event)
            record["sequence"] = seq
            # Attach timestamps and elapsed metrics for observability
            try:
                import time
                # Also include a UTC timestamp string for human-friendly logs
                from datetime import datetime, timezone
                record["timestamp_utc"] = (
                    datetime.now(timezone.utc)
                    .isoformat(timespec="microseconds")
                    .replace("+00:00", "Z")
                )
                # Establish or compute elapsed time since audio started streaming
                t_now_ns = time.monotonic_ns()
                if record.get("type") == "input_audio_buffer.append" and audio_start_monotonic_ns is None:
                    audio_start_monotonic_ns = t_now_ns
                if audio_start_monotonic_ns is None:
                    record["elapsed_ms_since_audio_start"] = None
                else:
                    # Ensure first append reports 0ms
                    record["elapsed_ms_since_audio_start"] = int(max(0, (t_now_ns - audio_start_monotonic_ns) // 1_000_000))
            except Exception:
                # If clock retrieval fails (unlikely), omit timing gracefully
                pass
            events.append(record)
            seq += 1

        # Pre-connection debug info
        try:
            await append_event(create_event("audio.resolved"))
            await append_event(create_event("debug.ws"))
        except Exception:
            pass

        import json as _json

        final_text: str | None = None
        # Validate session configuration early to raise on invalid inputs
        try:
            resolved_voice, resolved_modalities, resolved_turn_detection = self._resolve_session_params(context)
        except Exception:
            # Mirror missing-audio behavior: raise validation errors before connecting
            raise
        try:
            async with self._connect_websocket(context) as ws:
                await append_event(create_event("session.connected"))
                logging.getLogger(__name__).info("WebSocket connection established")

                # Send session configuration as the first message
                await self._send_session_config(ws, context, pre_resolved={
                    "voice": resolved_voice,
                    "modalities": resolved_modalities,
                    "turn_detection": resolved_turn_detection,
                })
                # Append a minimal event indicating config was sent
                await append_event(create_event("session.update"))
                # callers should provide compatible audio. We only base64-encode the bytes here.

                # Determine whether to convert based on context override, else model config (default True)
                convert_flag = False
                if context is not None and isinstance(context.get("convert_to_pcm16"), bool):
                    convert_flag = context.get("convert_to_pcm16")

                if convert_flag:
                    # Attempt to convert audio to PCM16 mono @ 24 kHz (Azure Realtime expectation).
                    # If conversion fails (e.g., bytes not a WAV), gracefully fall back to original bytes.
                    try:
                        converted_bytes, converted = self._convert_to_pcm16_mono_24k(audio_bytes)
                        if converted:
                            await append_event(create_audio_event("audio.converted.pcm16_24k", converted_bytes))
                            audio_bytes = converted_bytes
                    except Exception as conv_exc:
                        # Log conversion error but continue with original bytes
                        await append_event(create_error_event("audio.convert.error", str(conv_exc)))
                else:
                    # Explicitly skipped conversion
                    await append_event(create_event("audio.convert.skip"))

                # Send audio bytes (single chunk for MVP)
                # Build the full send frame including base64 audio, but log a redacted event.
                send_frame = self._make_audio_append_message(audio_bytes, context)
                await ws.send(_json.dumps(send_frame))
                await append_event(create_audio_event("input_audio_buffer.append", audio_bytes))

                # Commit audio and request response
                commit = create_event("input_audio_buffer.commit")
                await ws.send(_json.dumps(commit))
                await append_event(commit)

                create = create_event("response.create")
                await ws.send(_json.dumps(create))
                await append_event(create)

                # Mid-session prompt update via configuration is disabled; only initial session.update is sent

                # Receive and process responses
                final_text = await self._receive_responses(
                    ws,
                    timeout_s,
                    create_response_event,
                    append_event,
                )

        except Exception as e:
            # Log a simple error event; details can be inspected in logs
            await append_event(create_error_event("error", str(e)))

        # Attach events to context for assessment
        if context is not None:
            context["realtime_events"] = events

        return final_text or ""


    def _make_audio_append_message(self, audio_bytes: bytes, context=None):
        """Create the audio buffer append payload in the expected format.
        Returns a JSON-serializable dict with base64 data under the 'audio' key.
        This implementation does not perform conversion; callers should supply
        PCM16 mono @ 24kHz for best results.
        """
        import base64
        return {
            "type": "input_audio_buffer.append",
            "audio": base64.b64encode(audio_bytes).decode("ascii"),
        }

    async def _receive_responses(
        self,
        ws,
        timeout_s: float,
        create_response_event,
        append_event,
    ):
        """Receive messages from the websocket and aggregate final text.
        Records events via append_event and returns the aggregated final text.
        """
        import asyncio
        import json as _json

        done = False
        while not done:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=timeout_s)
            except asyncio.TimeoutError:
                await append_event(create_response_event("error.timeout"))
                break

            # Ignore binary frames entirely
            if isinstance(raw, (bytes, bytearray)):
                continue

            try:
                message = _json.loads(raw)
            except Exception:
                # Non-JSON, ignore body content
                continue

            if not isinstance(message, dict):
                continue

            t = message.get("type")

            # Errors
            if t == "error":
                await append_event(create_response_event("response.error", message))
                continue

            # Only record selected response events (include common delta naming variants)
            if t in ("response.text.delta", "response.output_text.delta", "response.done"):
                await append_event(create_response_event(t, message))
            # If response.done is received close the websocket
            if t == "response.done":
                try:
                    if hasattr(ws, "close"):
                        await ws.close()
                except Exception:
                    await append_event(create_response_event("ws.close_error"))
                done = True
            continue


    async def _send_session_config(self, ws, context=None, pre_resolved: dict | None = None):
        """
        Send the initial session.update payload to configure the Azure Realtime session.
        Modeled after endpoints/realtime.py but using the websockets API.
        """
        import json as _json

        # Resolve instructions with precedence:
        # 1) context["instructions"]
        # 2) context["realtime"]["instructions"]
        # 3) model config self._config["instructions"]
        # No default fallback: if none specified, omit instructions to use service defaults
        resolved_instructions: str | None = None
        if context:
            cand = context.get("instructions")
            if isinstance(cand, str) and cand:
                resolved_instructions = cand
            else:
                cand = (context.get("realtime", {}) or {}).get("instructions")
                if isinstance(cand, str) and cand:
                    resolved_instructions = cand
        if not resolved_instructions:
            cand = self._config.get("instructions")
            if isinstance(cand, str) and cand:
                resolved_instructions = cand

        # Resolve and validate realtime configuration (voice, modalities, turn_detection)
        if pre_resolved is not None:
            voice = pre_resolved["voice"]
            modalities = pre_resolved["modalities"]
            turn_detection = pre_resolved["turn_detection"]
        else:
            voice, modalities, turn_detection = self._resolve_session_params(context)

        payload = {
            "type": "session.update",
            "session": {
                "modalities": modalities,
                "voice": voice,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": turn_detection,
                "tools": [],
                "tool_choice": "auto",
            },
        }

        # Only include instructions if explicitly provided
        if resolved_instructions is not None:
            payload["session"]["instructions"] = resolved_instructions

        await ws.send(_json.dumps(payload))

    def _resolve_session_params(self, context=None):
        """Resolve and validate (voice, modalities, turn_detection) using precedence rules.
        Returns a tuple: (voice: str, modalities: list[str], turn_detection: dict)
        """
        voice = self._resolve_opt(context, "voice", self._config.get("voice", "alloy"))
        if not isinstance(voice, str) or not voice.strip():
            raise ValueError("voice must be a non-empty string")
        modalities_raw = self._resolve_opt(context, "modalities", self._config.get("modalities", ["text"]))
        modalities = self._normalize_modalities(modalities_raw)
        turn_det_raw = self._resolve_opt(context, "turn_detection", None)
        turn_detection = self._normalize_turn_detection(turn_det_raw)
        return voice, modalities, turn_detection

    def _resolve_opt(self, context, key: str, default):
        """Resolve an option from context or model config with precedence.
        Order: context[key] > context.get("realtime", {}).get(key) > self._config.get(key, default) > default
        """
        if context and key in context and context[key] is not None:
            return context[key]
        if context and isinstance(context.get("realtime"), dict):
            rt = context.get("realtime") or {}
            if key in rt and rt[key] is not None:
                return rt[key]
        return self._config.get(key, default)

    def _normalize_modalities(self, value):
        """Validate and normalize modalities into a deduped, order-preserving list of ['text','audio']."""
        allowed = {"text", "audio"}
        if isinstance(value, list):
            seen = set()
            out: list[str] = []
            for v in value:
                if not isinstance(v, str):
                    raise ValueError("modalities must be a list of strings")
                lv = v.strip()
                if lv not in allowed:
                    raise ValueError(f"invalid modality: {lv}")
                if lv not in seen:
                    seen.add(lv)
                    out.append(lv)
            if not out:
                raise ValueError("modalities cannot be empty")
            return out
        raise ValueError("modalities must be a list of 'text' and/or 'audio'")

    def _normalize_turn_detection(self, value):
        """Normalize turn_detection config to an Azure-compatible dict.
        Accepts:
          - None -> {"type": "none"}
          - {"type": "server_vad", ...}
          - {"type": "semantic_vad", ...}
          - {"type": "none"}
        Other types raise ValueError. Unknown keys are dropped; known keys are preserved.
        """
        if value is None:
            return {"type": "none"}
        if not isinstance(value, dict):
            raise ValueError("turn_detection must be a dict or None")

        t = value.get("type")
        if t == "none":
            return {"type": "none"}
        if t == "server_vad":
            allowed = {"threshold", "prefix_padding_ms", "silence_duration_ms", "create_response", "interrupt_response"}
            return {k: v for k, v in value.items() if k in allowed or k == "type"}
        if t == "semantic_vad":
            allowed = {"eagerness", "create_response", "interrupt_response"}
            return {k: v for k, v in value.items() if k in allowed or k == "type"}

        raise ValueError(f"unsupported turn_detection type: {t}")

    def _connect_websocket(self, context=None):
        """
        Create and return a websockets connection context manager to Azure OpenAI Realtime.
        Validates config, builds URL and headers, and applies sensible timeouts.
        Returns the async context manager so callers can `async with` it for proper cleanup.
        """
        # Validate required config
        required = ["endpoint", "api", "deployment", "key"]
        missing = [k for k in required if not self._config.get(k)]
        if missing:
            raise ConnectionError(f"Missing required config: {', '.join(missing)}")

        endpoint = str(self._config["endpoint"]).rstrip("/")
        api = self._config["api"]
        deployment = self._config["deployment"]
        key = self._config["key"]
        timeout_s = float(self._config.get("timeout_s", 60))

        base_url = endpoint.replace("https://", "wss://")
        url = f"{base_url}/openai/realtime?api-version={api}&deployment={deployment}"
        headers = {"api-key": key}

        # Return context manager; handshake occurs when entering the context
        return websockets.connect(url, extra_headers=headers, ping_timeout=timeout_s)

    def metadata(self):
        return {k: v for k, v in self._config.items() if k != "key"}
