import json
from typing import Any, Callable, Optional

from .mcp_tools import CustomModelConfig, MCPServer, Model
from .registry import Registry


class Fails(Model):
    """
    A mock model class that cycles through
      1. returning the expected answer
      2. returning "hello world"
      3. raising an exception
    """

    @classmethod
    def register(cls, registry: Registry, expected: Callable[[dict[str, Any]], Any]):
        configuration = CustomModelConfig(
            name="fails", type="CUSTOM_MODEL", parameters=expected
        )
        registry.register_custom_model(cls, configuration)

    def __init__(self, configuration: CustomModelConfig, mcp_tools: Optional[MCPServer]):
        self._expected = configuration.parameters

    async def infer(self, messages, context: dict[str, Any] | None = None):
        raise Exception("Fails model failed")

    def metadata(self):
        return {}


class Flakey(Model):
    """
    A mock model class that cycles through
      1. returning the expected answer
      2. returning "hello world"
      3. raising an exception
    """
    @classmethod
    def register(cls, registry: Registry, expected: Callable[[dict[str, Any]], Any]):
        configuration = CustomModelConfig(
            name="flakey", type="CUSTOM_MODEL", parameters=expected
        )
        registry.register_custom_model(cls, configuration)
    
    def __init__(self, configuration: CustomModelConfig, mcp_tools: Optional[MCPServer]):
        self._counter = -1
        self._expected = configuration.parameters

    async def infer(self, messages, context: dict[str, Any] | None = None):
        if context is None:
            raise ValueError("Context is required for Flakey model inference.")
        self._counter += 1
        if self._counter % 3 == 0:
            return to_llm_string(self._expected(context))
        elif self._counter % 3 == 1:
            return "hello world"
        else:
            raise Exception("Flakey model failed")

    def metadata(self):
        return {}


class Perfect(Model):
    """
    A mock model class that always returns the expected answer
    from result["case"]["answer"]
    """
    @classmethod
    def register(cls, registry: Registry, expected: Callable[[dict[str, Any]], Any]):
        configuration = CustomModelConfig(
            name="perfect", type="CUSTOM_MODEL", parameters=expected
        )
        registry.register_custom_model(cls, configuration)

    def __init__(self, configuration: CustomModelConfig, mcp_tools: Optional[MCPServer]):
        self._expected = configuration.parameters

    async def infer(self, messages, context: dict[str, Any] | None = None):
        if context is None:
            raise ValueError("Context is required for Perfect model inference.")
        return to_llm_string(self._expected(context))

    def metadata(self):
        return {}


def to_llm_string(value):
    # The value is pulled from the test case expected field,
    # so it might be an object that must first be serialized
    # to a string, to appear as an LLM completion.
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
