from glom import glom
import os
import sys

# Add the parent directory to the sys.path so that we can import from the
# gotaglio package, as if it had been installed.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gotaglio.dag import Dag
from gotaglio.main import main
from gotaglio.pipeline_spec import (
    ColumnSpec,
    PipelineSpec,
    SummarizerSpec,
)
from gotaglio.pipeline import Internal, Prompt


###############################################################################
#
# Default Configuration Values
#
###############################################################################

configuration = {
    "realtime": {
    # Note: audio_file and instructions now live under infer.model.realtime
    },
    "infer": {
        "model": {
            "name": "azure-realtime",
            # Optional runtime knobs; will be read by AzureOpenAIRealtime
            "settings": {
                "timeout_s": 30,
                "sample_rate_hz": 16000,
            },
            # Optional: place realtime-specific knobs here
            "realtime": {
                # Initial instructions for the realtime session (system prompt)
                "instructions": None,
                # Path to WAV file; used to resolve placeholders in cases
                "audio_file": "samples/realtime/hello.wav",
                # Voice to use for audio output (string)
                # Example values: "alloy", "coral", "sage" (provider-specific)
                #"voice": "alloy",
                # Modalities the model should support: any combination of "text" and "audio"
                # Here we use text-only; to enable speech out, include "audio"
                "modalities": ["text"],
                # Turn detection configuration:
                "turn_detection": None,
            },
        }
    },
}


###############################################################################
#
# Stage Functions
#
###############################################################################
def stages(name, config, registry):
    """
    Minimal realtime pipeline:
      - prepare: resolves the audio file path and prepares an empty message list
      - infer: invokes the realtime model, which streams audio and captures events
      - assess: returns transcript length as a trivial metric
    """

    model = registry.model(glom(config, "infer.model.name"))

    async def prepare(context):
        # Resolve audio from case and config
        audio = context["case"].get("audio")
        cfg_path = glom(config, "infer.model.realtime.audio_file", default=None)

        if isinstance(audio, str) and "{audio_file}" in audio and cfg_path:
            resolved = audio.replace("{audio_file}", str(cfg_path))
        elif isinstance(audio, str):
            resolved = audio
        else:
            resolved = cfg_path

        if not resolved:
            raise ValueError("Audio file path must be provided via case or config")

        context["audio_file"] = resolved
        # Propagate instructions into context so the model can pick them up with precedence
        # Use instructions under infer.model.realtime.instructions
        initial_instructions = glom(config, "infer.model.realtime.instructions", default=None)
        if isinstance(initial_instructions, str) and initial_instructions:
            context["instructions"] = initial_instructions
        # Propagate new realtime options (voice, modalities, turn_detection)
        voice = glom(config, "infer.model.realtime.voice", default=None)
        if isinstance(voice, str) and voice:
            context["voice"] = voice
        modalities = glom(config, "infer.model.realtime.modalities", default=None)
        if isinstance(modalities, list) and modalities:
            context["modalities"] = modalities
        turn_detection = glom(config, "infer.model.realtime.turn_detection", default=None)
        # Allow None to explicitly disable (maps to {"type": "none"} in the model)
        if turn_detection is None or isinstance(turn_detection, dict):
            context["turn_detection"] = turn_detection
        # The realtime model ignores messages content, but we keep structure consistent
        return []

    async def infer(context):
        return await model.infer(context["stages"]["prepare"], context)

    async def assess(context):
        # Simple metric: transcript length
        return len(context["stages"].get("infer", ""))

    stages = {
        "prepare": prepare,
        "infer": infer,
        "assess": assess,
    }

    return Dag.from_linear(stages)


###############################################################################
#
# Summarizer extensions
#
###############################################################################
def transcript_cell(result, turn_index):
    return result["stages"].get("infer", "")


def event_count_cell(result, turn_index):
    events = result.get("realtime_events") or result["stages"].get("realtime_events")
    # Fallback: look in context saved by Director for events on top-level result
    if events is None:
        events = result.get("stages", {}).get("infer_events")
    count = 0 if events is None else len(events)
    return str(count)


###############################################################################
#
# Pipeline Specification
#
###############################################################################
realtime_pipeline_spec = PipelineSpec(
    name="realtime",
    description="Realtime audio→text pipeline using Azure OpenAI Realtime",
    configuration=configuration,
    create_dag=stages,
    summarizer=SummarizerSpec(
        columns=[
            ColumnSpec(name="events", contents=lambda r, i: event_count_cell(r, i)),
            ColumnSpec(name="transcript", contents=lambda r, i: transcript_cell(r, i)),
        ]
    ),
)


def go():
    main([realtime_pipeline_spec])


if __name__ == "__main__":
    go()
