from abc import ABC, abstractmethod
from pydantic import BaseModel, Field, TypeAdapter, ValidationError
from typing import Any, cast, Literal, Union

from .constants import app_configuration
from .exceptions import ExceptionContext
from .lazy_imports import (
    azure_ai_inference as aai,
    azure_core_credentials as acc,
    azure_identity as aid,
    azure_identity_aio as aida,
    openai,
)
from .shared import read_data_file


class KeyAuth(BaseModel):
    type: Literal["key"]


class OAuth(BaseModel):
    type: Literal["oauth"]


AuthModel = Union[KeyAuth, OAuth]


class AzureAIConfig(BaseModel):
    name: str
    type: Literal["AZURE_AI"]
    endpoint: str
    authentication: AuthModel = Field(default_factory=lambda: KeyAuth(type="key"))
    key: str | None = None


class AzureOpenAIConfig(BaseModel):
    name: str
    type: Literal["AZURE_OPEN_AI"]
    endpoint: str
    deployment: str
    api: str
    authentication: AuthModel = Field(default_factory=lambda: KeyAuth(type="key"))
    key: str | None = None


ModelConfig = Union[AzureAIConfig, AzureOpenAIConfig]
AllModelConfigs = list[ModelConfig]


class Model(ABC):
    # `context` parameter provides entire test case context to
    # assist in implementing mocks that can pull the expected
    # value ouf of the context. Real models ignore the `context`
    # parameter.
    @abstractmethod
    async def infer(self, messages, context=None) -> str:
        pass

    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        pass


class AzureAI(Model):
    def __init__(self, registry, configuration: AzureAIConfig):
        self._config = configuration
        self._client = None
        registry.register_model(configuration.name, self)

    async def infer(self, messages, context=None):
        if not self._client:
            # Logic to choose credential based on self._config.authentication.type
            if self._config.authentication.type == "key":
                if not self._config.key:
                    raise ValueError("Key authentication requires a 'key'")
                self._client = aai.aio.ChatCompletionsClient(
                    endpoint=self._config.endpoint,
                    credential=acc.AzureKeyCredential(self._config.key),
                )
            else:  # "oauth"
                # Add OAuth logic here
                # Add OAuth logic here
                self._client = aai.aio.ChatCompletionsClient(
                    endpoint=self._config.endpoint, credential=aida.AzureCliCredential()
                )
                # raise NotImplementedError(
                #     "OAuth authentication is not implemented yet."
                # )

        response = await self._client.complete(messages=messages)

        return cast(str, response.choices[0].message.content)

    def metadata(self):
        return {k: v for k, v in self._config.model_dump().items() if k != "key"}


class AzureOpenAI(Model):
    def __init__(self, registry, configuration: AzureOpenAIConfig):
        self._config = configuration
        self._client = None
        registry.register_model(configuration.name, self)

    async def infer(self, messages, context=None):
        if not self._client:
            if self._config.authentication.type == "key":
                if not self._config.key:
                    raise ValueError("Key authentication requires a 'key'")
                self._client = openai.AzureOpenAI(
                    api_key=self._config.key,
                    api_version=self._config.api,
                    azure_endpoint=self._config.endpoint,
                )
            else:  # "oauth"
                # Add OAuth logic here
                # Create a token provider for Azure OpenAI using Azure CLI credentials
                token_provider = aid.get_bearer_token_provider(
                    aid.AzureCliCredential(),
                    "https://cognitiveservices.azure.com/.default",
                )
                # token_provider = aid.get_bearer_token_provider(
                #     aid.DefaultAzureCredential(),
                #     "https://cognitiveservices.azure.com/.default",
                # )

                # self._client = openai.AzureOpenAI(
                #     azure_endpoint=self._config.endpoint,
                #     azure_ad_token_provider=token_provider,
                #     api_version="2024-02-01",
                # )

                self._client = openai.OpenAI(
                    base_url=self._config.endpoint,
                    api_key=token_provider
                )
                # raise NotImplementedError(
                #     "OAuth authentication is not implemented yet."
                # )

        response = self._client.chat.completions.create(
            model=self._config.deployment,
            messages=messages,
            max_tokens=800,
            temperature=0.7,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None,
            stream=False,
        )

        return response.choices[0].message.content

    def metadata(self):
        return {k: v for k, v in self._config.model_dump().items() if k != "key"}


def register_models(registry):
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
            # NEW: Use isinstance for type-safe checking
            if isinstance(model_config, AzureAIConfig):
                AzureAI(registry, model_config)
            elif isinstance(model_config, AzureOpenAIConfig):
                AzureOpenAI(registry, model_config)
            else:
                # This case should ideally not be reached if your types are correct
                raise TypeError(f"Unhandled model config type: {type(model_config)}")
