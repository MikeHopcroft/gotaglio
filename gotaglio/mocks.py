from .models import Model

class Flakey(Model):
    """
    A mock model class that cycles through
      1. returning the expected answer
      2. returning "hello world"
      3. raising an exception
    """

    def __init__(self, registry, configuration):
        self._counter = -1
        registry.register_model("flakey", self)

    async def infer(self, messages, result=None):
        self._counter += 1
        if self._counter % 3 == 0:
            return f'{result["case"]["answer"]}'
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

    def __init__(self, registry, configuration):
        registry.register_model("perfect", self)

    async def infer(self, messages, result=None):
        return f'{result["case"]["answer"]}'

    def metadata(self):
        return {}
