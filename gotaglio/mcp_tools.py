from abc import ABC, abstractmethod
from fastmcp import FastMCP, Client
import json
from pydantic import BaseModel, Field, TypeAdapter, ValidationError
from typing import Any, Callable, cast, Optional, Literal, Union, TYPE_CHECKING

# if TYPE_CHECKING:
from openai.types.chat import ChatCompletionMessageParam

from .constants import app_configuration
from .exceptions import ExceptionContext
from .lazy_imports import azure_identity as aid, openai
from .registry import Registry
from .shared import format_list, read_data_file


class KeyAuth(BaseModel):
    type: Literal["key"]


class OAuth(BaseModel):
    type: Literal["oauth"]


AuthModel = Union[KeyAuth, OAuth]


class AzureFoundryModelConfig(BaseModel):
    name: str
    type: Literal["AZURE_OPEN_AI"]
    endpoint: str
    deployment: str
    api: str
    authentication: AuthModel = Field(default_factory=lambda: KeyAuth(type="key"))
    key: str | None = None


class CustomModelConfig(BaseModel):
    name: str
    type: Literal["CUSTOM_MODEL"]
    parameters: Any = Field(default_factory=dict)


ModelConfig = Union[AzureFoundryModelConfig]


class MCPTools:
    def __init__(self, mcp: FastMCP[Any]):
        """
        Initialize with path to the MCP server script.

        Args:
            server_script_path: Path to the Python file containing the MCP server
        """
        self._mcp = mcp
        self._client = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = Client(self._mcp)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)

    async def get_tools(self) -> list[dict[str, Any]]:
        """
        Convert MCP tools to OpenAI tools format.

        Returns:
            List of tool definitions suitable for OpenAI's tools parameter
        """
        if self._client is None:
            raise RuntimeError("MCPTools must be used within an async context manager.")
        tools_response = await self._client.list_tools()

        openai_tools = []
        for tool in tools_response:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema,
                },
            }
            openai_tools.append(openai_tool)

        return openai_tools

    async def invoke_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """
        Invoke an MCP tool and return the result.

        Args:
            tool_name: Name of the tool to invoke
            arguments: Dictionary of arguments to pass to the tool

        Returns:
            String representation of the tool result
        """
        if self._client is None:
            raise RuntimeError("MCPTools must be used within an async context manager.")
        result = await self._client.call_tool(tool_name, arguments)

        # Extract the result - FastMCP client returns structured data
        if isinstance(result, str):
            return result
        elif hasattr(result, "content") and result.content:
            # Extract text from content blocks
            return "\n".join(
                getattr(item, "text")
                for item in result.content
                if hasattr(item, "text")
            )
        else:
            return json.dumps(result, ensure_ascii=False)


class Model(ABC):
    # `context` parameter provides entire test case context to
    # assist in implementing mocks that can pull the expected
    # value ouf of the context. Real models ignore the `context`
    # parameter.
    @abstractmethod
    async def infer(self, messages: list[ChatCompletionMessageParam], context=None) -> str:
        pass

    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        pass


class AzureFoundryModel(Model):
    def __init__(self, config: AzureFoundryModelConfig, mcp_tools: Optional[MCPTools]):
        self._config = config
        self._mcp_tools = mcp_tools
        self._tools = None

        # Get a token provider using your default Azure credentials.
        # This assumes you are logged in with `az login` in your terminal.
        self._token_provider = aid.get_bearer_token_provider(
            aid.DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
        )

        self._client = None

    async def infer(
        self, messages: list[ChatCompletionMessageParam], context=None
    ) -> str:
        MAX_STEPS = 5
        try:
            client = await self._lazy_get_client()
            for _ in range(MAX_STEPS):

                resp = client.chat.completions.create(
                    model=self._config.deployment,  # Use the deployment name for the model
                    messages=messages,
                    **(
                        {"tools": self._tools, "tool_choice": "auto"}
                        if self._tools
                        else {}
                    ),
                )
                msg = resp.choices[0].message
                if msg.tool_calls:
                    # print("Model requested tool calls.")
                    if self._mcp_tools is None:
                        raise RuntimeError(
                            "MCPModel was not initialized with MCPTools."
                        )
                    async with self._mcp_tools as mcp_tools:
                        # 1. Append assistant message WITH tool_calls
                        messages.append(
                            cast(ChatCompletionMessageParam, msg.model_dump())
                        )

                        # 2. Execute each tool call and append results
                        for tool_call in msg.tool_calls:
                            function_name = tool_call.function.name  # type: ignore[union-attr]
                            function_args = json.loads(tool_call.function.arguments)  # type: ignore[union-attr]

                            print(f"Calling tool: {function_name}({function_args})")
                            result = await mcp_tools.invoke_tool(
                                function_name, function_args
                            )

                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": result,
                                }
                            )
                        continue

                # No tool calls → final answer
                final_content = msg.content or ""
                messages.append(
                    {
                        "role": "assistant",
                        "content": final_content,
                    }
                )
                print(json.dumps(messages, indent=2))
                return final_content
            else:
                raise RuntimeError("Max steps exceeded")

        except Exception as e:
            print(f"\nAn error occurred: {e}")
            raise

    def metadata(self):
        # Filter out the 'key' field from metadata as we don't want to expose
        # the API key in logs.
        return {k: v for k, v in self._config.model_dump().items() if k != "key"}

    async def _lazy_get_client(self):
        if self._client is None:
            if self._mcp_tools:
                async with self._mcp_tools:
                    self._tools = await self._mcp_tools.get_tools()
                    # print(f"Using tools: {self._tools}")
            else:
                self._tools = None
            print(
                f"Creating AzureOpenAI client: {self._config.endpoint}, deployment: {self._config.deployment}"
            )
            self._client = openai.AzureOpenAI(
                azure_endpoint=self._config.endpoint,
                api_version=self._config.api,
                azure_ad_token_provider=self._token_provider,
                timeout=10.0,
            )
            # print("AzureOpenAI client created successfully.")
        return self._client


ModelFactory = Callable[[Optional[MCPTools]], Model]


class Registry2:
    def __init__(self, registry: Optional["Registry2"] = None):
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
        factory: Callable[[CustomModelConfig, Optional[MCPTools]], Model],
        config: CustomModelConfig,
    ):
        if config.name in self._models:
            raise ValueError(f"Attempting to register duplicate model '{config.name}'.")
        # Placeholder for custom model registration logic
        self._models[config.name] = lambda mcp_tools: factory(config, mcp_tools)

    def model(
        self, name: str, mcp_tools: Optional[MCPTools] = None
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

def register_models2(registry: Registry2) -> None:
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
