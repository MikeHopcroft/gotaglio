from pydantic import TypeAdapter, ValidationError
from typing import Callable, Optional

from .constants import app_configuration
from .exceptions import ExceptionContext
from .mcp_tools import AzureFoundryModel, CustomModelConfig, MCPServer, Model, ModelConfig
from .shared import format_list, read_data_file

ModelFactory = Callable[[Optional[MCPServer]], Model]

class Registry:
    def __init__(self, registry: Optional["Registry"] = None):
        self._registry = registry
        self._models: dict[str, ModelFactory] = {}

    def register_standard_model(self, config: ModelConfig):
        if config.name in self._models:
            raise ValueError(f"Attempting to register duplicate model '{config.name}'.")
        self._models[config.name] = lambda mcp_tools: AzureFoundryModel(
            config, mcp_tools
        )

    def register_custom_model(
        self,
        factory: Callable[[CustomModelConfig, Optional[MCPServer]], Model],
        config: CustomModelConfig,
    ):
        if config.name in self._models:
            raise ValueError(f"Attempting to register duplicate model '{config.name}'.")
        # Placeholder for custom model registration logic
        self._models[config.name] = lambda mcp_tools: factory(config, mcp_tools)

    def model(
        self, name: str, mcp_tools: Optional[MCPServer] = None
    ) -> Model:
        factory = self._model_helper(name)
        if not factory:
            # If the model is not found in the current registry, raise an error.
            all_model_names = []
            self.list_models(all_model_names)
            all_model_names.sort()
            names = format_list([k for k in all_model_names])
            raise ValueError(
                f"Model '{name}' not found. Available models include {names}."
            )
        return factory(mcp_tools)

    def _model_helper(
        self, name: str
    ) -> ModelFactory | None:
        if name not in self._models:
            if self._registry is not None:
                return self._registry._model_helper(name)
            else:
                return None

        return self._models[name]

    def list_models(self, result: list[str]) -> None:
        if self._registry is not None:
            self._registry.list_models(result)
        for name in self._models:
            result.append(name)

def register_models(registry: Registry) -> None:
    config_files = app_configuration["model_config_files"]
    credentials_files = app_configuration["model_credentials_files"]

    # Read the model configuration file (logic remains the same)
    raw_config = None
    for config_file in config_files:
        raw_config = read_data_file(config_file, True, True)
        if raw_config:
            break

    # Read the credentials file (logic remains the same)
    credentials = None
    for credentials_file in credentials_files:
        credentials = read_data_file(credentials_file, True, True)
        if credentials:
            break

    if not raw_config:
        return  # No models to register

    # Merge in keys from credentials file before validation
    if credentials:
        for model_dict in raw_config:
            if model_dict.get("name") in credentials:
                model_dict["key"] = credentials[model_dict["name"]]

    # NEW: Parse and validate the raw config into Pydantic models
    try:
        # TypeAdapter will convert the list of dicts into a list of
        # either AzureAIConfig or AzureOpenAIConfig objects.
        # Pydantic's discriminated union handles this automatically based on the 'type' field.
        adapter = TypeAdapter(list[ModelConfig])
        validated_configs = adapter.validate_python(raw_config)
    except ValidationError as e:
        # Provide a much richer error message if validation fails
        raise ValueError(f"Invalid model configuration: {e}") from e

    # Construct and register models from the validated Pydantic objects
    for model_config in validated_configs:
        with ExceptionContext(f"While registering model '{model_config.name}':"):
            registry.register_standard_model(model_config)
