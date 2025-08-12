from glom import glom
from typing import Any

from .dag import build_dag_from_spec
from .director import process_one_case
from .exceptions import ExceptionContext
from .mocks import Flakey, Perfect
from .registry import Registry
from .shared import apply_patch, flatten_dict
from .pipeline_spec import PipelineSpec, TurnMappingSpec


class Pipeline2:
    def __init__(
        self,
        spec: PipelineSpec,
        replacement_config: dict[str, Any] | None,
        flat_config_patch: dict[str, Any],
        global_registry: Registry,
    ):
        self._spec = spec

        # Merge and validate configurations.
        self._config = apply_patch(
            (
                replacement_config
                if replacement_config is not None
                else spec.configuration
            ),
            flat_config_patch,
        )
        ensure_required_configs(spec.name, spec.configuration, self._config)

        # Construct and register some model mocks, specific to this pipeline.
        # NOTE: this must be done before spec.create_dag, which accesses
        # models from the registry.
        registry = Registry(global_registry)
        Flakey(registry, {})
        Perfect(registry, {})

        # Create the DAG.
        turn_dag = spec.create_dag(spec.name, self._config, registry)
        if spec.turns is not None:
            # Wrap the single-turn DAG to handle multiple turns.
            self._dag = create_turns_dag(spec.turns, turn_dag)
        else:
            # Just running a single turn.
            self._dag = turn_dag

    def get_config(self):
        return self._config

    def get_dag(self):
        return self._dag


def create_turns_dag(turn_spec: TurnMappingSpec, turn_dag):
    async def turns(context):
        initial = turn_spec.initial
        expected = turn_spec.expected
        observed = turn_spec.observed

        case = context["case"]

        # The turn field in the context controls whether the
        # pipeline executes a single turn or all turns.
        turn_index = glom(context, "turn", default=None)
        if turn_index is None:
            # We're running all of the turns
            turns = case["turns"]
            # When running all turns, start with the initial value for the case.
            value = case[initial]
        else:
            # We're running a single turn in isolation
            # Start with the value from the previous turn.
            turns = [case["turns"][turn_index]]
            value = glom(case, f"turns[{turn_index - 1}].{expected}", default=None)

        results = []
        for turn in turns:
            turn_case = turn.copy()
            turn_case[initial] = value

            result = await process_one_case(turn_case, turn_dag, None)

            results.append(result)
            value = glom(result, f"stages.{observed}", default=None)
            if result["succeeded"] == False or value is None:
                # If the extraction failed, we stop processing remaining turns.
                break

        return results

    return build_dag_from_spec([{"name": "turns", "function": turns, "inputs": []}])


# Value in Pipeline configuration, indicating the value should be supplied by
# key=value pairs on the command line.
class Prompt:
    def __init__(self, description):
        self._description = description


# Value in Pipeline configuration, indicating the value will be supplied by the
# Pipeline runtime. Using a value of Internal will prevent the corresponding
# key from being displayed in help messages.
class Internal:
    def __init__(self):
        pass


# TODO: where is this used? Compare?
def format_config(x):
    if isinstance(x, Prompt):
        return "PROMPT"
    else:
        return x


def ensure_required_configs(name, default_config, config):
    """
    Raises a ValueError if any required configuration setting is missing.

    Args:
        name (str): The name of the pipeline.
        config (dict): The configuration dictionary to validate.

    Raises:
        ValueError: If any setting in the configuration is `None`.
    """
    settings = flatten_dict(config)
    with ExceptionContext(f"Pipeline '{name}' checking settings."):
        for k, v in settings.items():
            if isinstance(v, Prompt):
                lines = [
                    f"{name} pipeline: missing '{k}' parameter.",
                    "",
                    "Required settings:",
                ]
                prompts = [
                    (k, v)
                    for k, v in flatten_dict(default_config).items()
                    if isinstance(v, Prompt)
                ]
                lines.extend([f"  {k}: {v._description}" for k, v in prompts])
                raise ValueError("\n".join(lines))
