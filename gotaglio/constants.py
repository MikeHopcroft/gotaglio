from pathlib import Path

app_configuration_values = {
    "base_folder": "",
    "log_folder": "logs",
    "model_config_files": ["models.json", "models.yaml", "models.yml"],
    "model_credentials_files": [".credentials.json", ".credentials.yaml", ".credentials.yml"],
    "default_concurrancy": 2,
    "program_name": "gotag",
}

class AppConfiguration:
    def __init__(self, config):
        self._config = config
        self.base_relative = ["log_folder"]

    def __getitem__(self, key):
        if key in self.base_relative:
            return str(Path(self._config["base_folder"]).joinpath(self._config[key]).as_posix())
        return self._config[key]

    def __setitem__(self, key, value):
        self._config[key] = value

    def __contains__(self, key):
        return key in self._config

    def __repr__(self):
        return str(self._config)

app_configuration = AppConfiguration(app_configuration_values)

# Model capability allowlists
# Models whose type is in this set are considered capable of ingesting direct audio input
# (e.g., raw audio bytes or an audio file path on the case).
AUDIO_INPUT_MODEL_TYPES = {"AZURE_OPEN_AI_REALTIME"}
