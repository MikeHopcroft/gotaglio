import json
from typing import Any, Callable

from .models import Model
from .pipeline_spec import get_turn


class Fails(Model):
    """
    A mock model class that cycles through
      1. returning the expected answer
      2. returning "hello world"
      3. raising an exception
    """

    def __init__(
        self, registry, expected: Callable[[dict[str, Any]], Any], configuration
    ):
        self._expected = expected
        registry.register_model("fails", self)

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

    def __init__(
        self, registry, expected: Callable[[dict[str, Any]], Any], configuration
    ):
        self._counter = -1
        self._expected = expected
        registry.register_model("flakey", self)

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

    def __init__(
        self, registry, expected: Callable[[dict[str, Any]], Any], configuration
    ):
        registry.register_model("perfect", self)
        self._expected = expected

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
