# Models

TODO: coming soon. 

* Instructions for configuring models.json and credentials.json.
* Instructions for building custom model adapters.

## Configuring Models

Models can be configured in `models.json` in the current working directory. The repo contains a [models.json.template](../models.json.template) file that shows the parameters for each available model API.

GoTaglio currently supports the following model API types:
* AZURE_AI - for access to most models in Azure.
* AZURE_OPEN_AI - for access to OpenAI models hosted in Azure (GPT-3.5/4 family).
* AZURE_OPEN_AI_5 - for access to Azure OpenAI GPT-5 family models.

The `models.json` file is structured as an array of model definitions. Here's an example:

~~~json
[
  {
    "name": "phi3",
    "description": "Phi-3 medium 128k",
    "type": "AZURE_AI",
    "endpoint": <ENDPOINT>,
    "key": "From .credentials.json"
  },
  {
    "name": "gpt3.5",
    "description": "GPT-3.5-turbo 16k",
    "type": "AZURE_OPEN_AI",
    "endpoint": <ENDPOINT>,
    "deployment": "gpt-35-turbo-16k-0613",
    "key": "From .credentials.json",
    "api": "2024-07-01-preview"
  },
  {
    "name": "gpt4o",
    "description": "gpt-4o-2024-11-20",
    "type": "AZURE_OPEN_AI",
    "endpoint": <ENDPOINT>,
    "deployment": "gpt-4o-2024-11-20",
    "key": "From .credentials.json",
    "api": "2024-08-01-preview"
  },
  {
    "name": "gpt5",
    "description": "GPT-5 deployment",
    "type": "AZURE_OPEN_AI_5",
    "endpoint": <ENDPOINT>,
    "deployment": "gpt-5-2025-xx-xx",
    "key": "From .credentials.json",
    "api": "2025-01-01-preview"
  }
]
~~~

### GPT-5 specifics (AZURE_OPEN_AI_5)

When using the GPT-5 family via `AZURE_OPEN_AI_5`:
* The token limit parameter is `max_completion_tokens` (not `max_tokens`).
* The parameters `temperature` and `top_p` are not supported and should be omitted from runtime settings.
* Other supported settings remain the same (for example: `frequency_penalty`, `presence_penalty`).

If you define per-pipeline model settings (e.g., in a pipeline config), prefer:

~~~json
{
  "infer": {
    "model": {
      "name": "gpt5",
      "settings": {
        "max_completion_tokens": 800,
        "frequency_penalty": 0,
        "presence_penalty": 0
      }
    }
  }
}
~~~

For backward compatibility, GoTaglio will also honor `max_tokens` if present, but `max_completion_tokens` takes precedence when using GPT-5.

## Supplying Credentials

GoTaglio looks for a file called `.credentials.json` in the current working directory. This file is a JSON dict that maps model names to keys. You should .gitignore this file in your repo to avoid accidentally checking in credentials. GoTaglio includes a [template credential file](../.credentials.json.template).

~~~json
{
  "phi3": <PHI3 KEY>,
  "gpt3.5": <GPT 3.5 KEY>,
  "gpt4o": <GPT 4o KEY>,
  "gpt5": <GPT 5 KEY>
}
~~~

COMING SOON: other authentication methods

## Building Custom Model Adapters

You can build your own model adapters by creating a class that derives from `Model`. Here's an example of the `perfect` model mock from the [simple.py](../samples/simple/simple.py) sample:

~~~python
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
~~~

Here is the code to the AzureAI model from [models.py](../gotaglio/models.py):

~~~python
class AzureAI(Model):
    def __init__(self, registry, configuration):
        self._config = configuration
        self._client = None
        registry.register_model(configuration["name"], self)

    async def infer(self, messages, context=None):
        if not self._client:
            endpoint = self._config["endpoint"]
            key = self._config["key"]
            self._client = ChatCompletionsClient(
                endpoint=endpoint, credential=AzureKeyCredential(key)
            )

        response = self._client.complete(messages=messages)

        return response.choices[0].message.content

    def metadata(self):
        return {k: v for k, v in self._config.items() if k != "key"}
~~~
