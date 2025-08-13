import json

from .models import Model
from .pipeline_spec import MappingSpec

class Flakey(Model):
    """
    A mock model class that cycles through
      1. returning the expected answer
      2. returning "hello world"
      3. raising an exception
    """

    def __init__(self, registry, mappings: MappingSpec, configuration):
        self._counter = -1
        self._mappings = mappings
        registry.register_model("flakey", self)

    async def infer(self, messages, result=None):
        self._counter += 1
        if self._counter % 3 == 0:
            return f'{result["case"][self._mappings.expected]}'
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

    def __init__(self, registry, mappings: MappingSpec, configuration):
        registry.register_model("perfect", self)
        self._mappings = mappings

    async def infer(self, messages, result=None):
        # TODO: need to JSON serialize for non-strings
        value = result["case"][self._mappings.expected]
        if isinstance(value, str):
            return value
        else:
            return json.dumps(value, ensure_ascii=False)
        # return f'{result["case"][self._mappings.expected]}'

    def metadata(self):
        return {}
