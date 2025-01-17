from .templating import load_template

from abc import ABC, abstractmethod
import json


class Pipeline(ABC):
    @abstractmethod
    def stages(self):
        pass

    @abstractmethod
    def metadata(self):
        pass


class SimplePipeline(Pipeline):
    def __init__(self, runner, config):
        self._config = config
        self._name = "simple"
        self._runner = runner

        # Template is lazily loaded in self.stages()
        if "template" not in self._config:
            raise ValueError(f"{self._name} pipeline: missing 'template=<filename>' parameter.")
        self._template_file = self._config["template"]
        self._template = None
        self._template_text = None

        #
        # Lookup the model
        #
        if "model" not in config:
            raise ValueError("{self._name} pipeline: requires model=<name> parameter.")
        self._model = runner.model(config["model"])

    def stages(self):
        try:
            if not self._template:
                (self._template_text, self._template) = load_template(
                    self._template_file
                )
        except Exception as e:
            raise ValueError(f"{self._name} pipeline: {e}")

        async def prepare(result):
            messages = [
                {"role": "system", "content": await self._template(result)},
                {"role": "user", "content": result["case"]["text"]},
            ]
            return messages

        async def infer(result):
            return await self._model.infer(result["stages"]["prepare"])

        async def extract(result):
            try:
                return json.loads(result["stages"]["infer"])
            except json.JSONDecodeError as m:
                raise ValueError(f"Error decoding JSON: {m}")

        return {"prepare": prepare, "infer": infer, "extract": extract}

    def summarize(self, results):
        summary = [
            {"uuid": result["case"]["uuid"], "succeeded": result["succeeded"]}
            for result in results["results"]
        ]
        if len(summary) == 0:
            print("No results.")
        else:
            for item in summary:
                print(f"{item['uuid']} {"OK" if item['succeeded'] else "ERROR"}")

    def metadata(self):
        return {
            "name": self._name,
            "config": self._config,
            "template": self._template_text,
        }


def register_pipelines(runner):
    # This is error-prone as the key might not match the hard-coded self._name field.
    runner.register_pipeline("simple", SimplePipeline)
