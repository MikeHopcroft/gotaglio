from abc import ABC, abstractmethod
import os

from .constants import app_configuration
from .exceptions import ExceptionContext
from .lazy_imports import azure_ai_inference, azure_core_credentials, openai
from .shared import read_data_file


class Model(ABC):
    # `context` parameter provides entire test case context to
    # assist in implementing mocks that can pull the expected
    # value ouf of the context. Real models ignore the `context`
    # parameter.
    @abstractmethod
    def infer(self, message, context=None):
        pass

    @abstractmethod
    def metadata(self):
        pass


class AzureAI(Model):
    def __init__(self, registry, configuration):
        self._config = configuration
        self._client = None
        registry.register_model(configuration["name"], self)

    async def infer(self, messages, context=None):
        if not self._client:
            endpoint = self._config["endpoint"]
            key = self._config["key"]
            self._client = azure_ai_inference.ChatCompletionsClient(
                endpoint=endpoint,
                credential=azure_core_credentials.AzureKeyCredential(key),
            )

        response = self._client.complete(messages=messages)

        return response.choices[0].message.content

    def metadata(self):
        return {k: v for k, v in self._config.items() if k != "key"}


class AzureOpenAI(Model):
    def __init__(self, registry, configuration):
        self._config = configuration
        self._client = None
        registry.register_model(configuration["name"], self)

    async def infer(self, messages, context=None):
        if not self._client:
            endpoint = self._config["endpoint"]
            key = self._config["key"]
            api = self._config["api"]
            self._client = openai.AzureOpenAI(
                api_key=key,
                api_version=api,
                azure_endpoint=endpoint,
            )

        response = self._client.chat.completions.create(
            model=self._config["deployment"],
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
        return {k: v for k, v in self._config.items() if k != "key"}


def register_models(registry):
    config_files = app_configuration["model_config_files"]
    credentials_files = app_configuration["model_credentials_files"]

    # Read the model configuration file
    config = None
    for config_file in config_files:
        config = read_data_file(config_file, True, True)
        if config:
            break

    # Read the credentials file
    credentials = None
    for credentials_file in credentials_files:
        credentials = read_data_file(credentials_file, True, True)
        if credentials:
            break

    if config and credentials:
        # Merge in keys from credentials file
        for model in config:
            if model["name"] in credentials:
                model["key"] = credentials[model["name"]]

    if config:
        # Construct and register models.
        # TODO: lazy construction of models on first use
        for model in config:
            with ExceptionContext(f"While registering model '{model['name']}':"):
                if model["type"] == "AZURE_AI":
                    AzureAI(registry, model)
                elif model["type"] == "AZURE_OPEN_AI":
                    AzureOpenAI(registry, model)
                else:
                    raise ValueError(
                        f"Model {model['name']} has unsupported model type: {model['type']}"
                    )
