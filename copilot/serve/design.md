
## Overview

We're in the process of adding functionality to gotaglio to serve an http api endpoint that uses a pipeline to perform inference and schema validation. The main functionality will reside in gotaglio/serve.py. Code in gotaglip/subcommands/serve_cmd and gotaglio/gotag.py wires up the functionality for usage from the CLI or in a notebook via an instance of the Gotaglio class, respectively.

## Technologies
The server should be based on FastAPI, uvcorn, and pydantic. CLI and the Gotaglio objects should start uvcorn, instead of leaving this to the user.

The server should run indefinitely, with the expectation that the user will kill the process.

## API Routes
Because the server will eventually serve up a single page react app, the routes for the api will start with `api`. There will be two routes: `api/infer` and `api/validate`.

The infer API takes a JSON dictionary with two fields: `case` and `turn`. The `case` field has a gotaglio test case data structure. The `turn` field is an int that indicates which turn of the test case should be run.

The validate API takes a single JSON object and returns and object with two fields: `valid` and `error`. `valid` is a boolean, indicating whether the JSON object was valid, according to the pipeline schema. If `valid` is False, `error` will have an error message.

# Next Step
We will build this incrementally. I have already stubbed out the wiring from the CLI and the Gotaglio class. 

1. Let's create a serve() entry point in serve.py that can be called to complete the integration.
2. Add FastAPI and uvcorn to the project and stub out the two API routes with mocks. I would like to test these with curl.
3. Only after we are satisfied with the curl results, will we proceed to integrate with the pipeline.

# Rules
For now, let's limit the changes to pyproject.toml, gotaglio/subcommands/serve_cmd.py, gotaglio/gotag.py, and the new file, gotaglio/serve.py.


