from typing import Optional

from .make_console import MakeConsole
from .models import Model
from .shared import format_list


class Registry:
    def __init__(self, registry: Optional['Registry'] = None):
        self._registry = registry
        self._models = {}
        self._pipelines = {}
        pass

    def register_model(self, name: str, model: Model):
        if name in self._models:
            raise ValueError(f"Attempting to register duplicate model '{name}'.")
        self._models[name] = model

    def model(self, name: str) -> Model:
        result = self._model_helper(name)
        if not result:
            # If the model is not found in the current registry, raise an error.
            all_model_names = []
            self.list_models(all_model_names)
            all_model_names.sort()
            names = format_list([k for k in all_model_names])
            raise ValueError(
                f"Model '{name}' not found. Available models include {names}."
            )
        return result

    def _model_helper(self, name: str) -> Model | None:
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

