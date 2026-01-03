# Sample Applications

GoTaglio includes a number of samples:
* TODO: Calc added. Simple seems to be gone.
* [simple.py](../samples/simple/simple.py) - demonstration of a simple 4 stage linear pipeline that uses a language model as a calculator.
* [dag.py](../samples/dag/dag.py) - demonstration of a [directed acyclic graph](https://en.wikipedia.org/wiki/Directed_acyclic_graph) (DAG) pipeline.
* [menu.py](../samples/menu/menu.py) - a restaurant ordering bot

You need a properly configured development to run the samples.

## Development Environments

The easiest way to try out the samples is in a [GitHub Codespace](./codespaces.md). This approach spins up a fully configured dev container connected to an instance of [Visual Studio Code](https://code.visualstudio.com/), running in your browser.

You can also clone the repo on your local workstation, install some tools and PyPi packages and then run the samples locally.

Here are instructions for both approaches:
* [GitHub Codespace](codespaces.md)
* [Cloning to Local Repo](clone.md)

## Using Built-in LLM Mocks

Once you are able to access the samples, you can run them without further configuration, using built-in LLM mocks.

All of the samples are accessible via the `gotag` command.
As you can see from the `help` subcommand, the `gotag` tool provides a lot of functionality.

~~~sh
% gotag help
usage: gotag [-h] {add-ids,compare,help,history,models,pipelines,rerun,run,format,summarize} ...

A tool for managing and running ML pipelines.

positional arguments:
  {add-ids,compare,help,history,models,pipelines,rerun,run,format,summarize}
                        Subcommands
    add-ids             Add uuids to a suite
    compare             Compare two or more label sets
    help                Show help for gotaglio commands
    history             Show information about recent runs
    models              List available models
    pipelines           List available pipelines
    rerun               Rerun an experiment with modifications.
    run                 Run a named pipeline
    format              Pretty print a run
    summarize           Summarize a run

options:
  -h, --help            show this help message and exit
~~~

We can use the `pipelines` subcommand to see the list of built-in sample pipelines.

~~~sh
% gotag pipelines
Available pipelines:
  dag: An example of a directed acyclic graph (DAG) pipeline.
  menu: An example pipeline for an LLM-based food ordering bot.
  simple: An example pipeline for an LLM-based calculator.
~~~

We can use the `run` sub-command to run a pipeline. Let's look at the help message for `run`:
~~~
% gotag help run
usage: gotag run [-h] [-c CONCURRENCY] pipeline cases [key_values ...]

positional arguments:
  pipeline              The name of the pipeline to run
  cases                 The name of a file with cases
  key_values            key=value arguments to configure pipeline

options:
  -h, --help            show this help message and exit
  -c CONCURRENCY, --concurrency CONCURRENCY
                        Maximum concurrancy for tasks
~~~

Running a pipeline, involves specifying the pipeline's name, a JSON file of cases to run, and some configuration values. The following example runs the `simple` pipeline on a list of cases in `samples/simple/cases.json`.

The `perfect` model is a mock provided by the `simple` pipeline. This mock always gives the correct answer. The `flakey` mock cycles between correct answers, incorrect answers, and exceptions. The `simple` and `menu` pipelines include both mocks.

The model mocks are useful for kicking the tires before configuring external models and they are helpful when debugging your custom pipeline implementation.

~~~sh
% gotag run simple samples/simple/cases.json prepare.template=samples/simple/template.txt infer.model.name=perfect
Run configuration
  id: d940443f-4869-45a7-9a98-4497cf8e539e
  cases: samples\simple\cases.json
  pipeline: simple
    prepare.template: PROMPT => samples\simple\template.txt
    infer.model.name: PROMPT => perfect
  concurrancy: 2

    Summary for d940443f-4869-45a7-9a98-4497cf8e539e                                                                                                 
┏━━━━━┳━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  id ┃ run      ┃ score ┃ keywords                     ┃
┡━━━━━╇━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ ed6 │ COMPLETE │  0.00 │ addition, p0                 │
│ e09 │ COMPLETE │  0.00 │ addition, multiplication, p0 │
│ e86 │ COMPLETE │  0.00 │ division, hexidecimal        │
│ d73 │ COMPLETE │  0.00 │ division, hexidecimal, fails │
└─────┴──────────┴───────┴──────────────────────────────┘

Total: 4
Complete: 4/4 (100.00%)
Error: 0/4 (0.00%)
Passed: 4/4 (100.00%)
Failed: 0/4 (0.00%)

Results written to logs\d940443f-4869-45a7-9a98-4497cf8e539e.json
~~~

At this point you should have enough knowledge to run any of the samples:
* [simple](simple.md)
* [menu](menu.md)
* [dag](dag.md)

## Configuring Access to Cloud Models

GoTaglio includes adapters for connecting to model endpoints hosted in Azure. You can use these built-in adapters or implement your own by subclassing `Model`.

Here are instructions for [configuring model endpoints and authentication](models.md).
