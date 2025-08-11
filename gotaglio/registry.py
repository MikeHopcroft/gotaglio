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

    # TODO: rewmove this.
    def register_pipeline(self, pipeline):
        name = pipeline.name()
        if name in self._pipelines:
            raise ValueError(f"Attempting to register duplicate pipeline '{name}'.")
        self._pipelines[name] = pipeline

    # TODO: rewmove this.
    def pipeline(self, name):
        if name not in self._pipelines:
            names = format_list([k for k in self._pipelines.keys()])
            raise ValueError(
                f"Pipeline '{name}' not found. Available pipelines include {names}."
            )
        return self._pipelines[name]

    # TODO: move these functions out of registry.
    def summarize(self, results):
        pipeline = self.create_pipeline(results)
        console = MakeConsole()
        pipeline.summarize(console, results)
        console.render()

    def format(self, results, case_uuid_prefix):
        pipeline = self.create_pipeline(results)
        console = MakeConsole()
        pipeline.format(console, results, case_uuid_prefix)
        console.render()

    def compare(self, results_a, results_b):
        pipeline = self.create_pipeline(results_a)
        console = MakeConsole()
        pipeline.compare(console, results_a, results_b)
        console.render()

    def create_pipeline(self, results):
        pipeline_name = results["metadata"]["pipeline"]["name"]
        pipeline_config = results["metadata"]["pipeline"]["config"]
        pipeline_factory = self.pipeline(pipeline_name)
        pipeline = pipeline_factory(self, pipeline_config, {})
        return pipeline