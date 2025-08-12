# TODO

* Today
  * Abstract looking up pipeline spec
  * Translate rerun
  * . Translate summarize
  * Continue cleaning up TODOs in Pipeline2.format
  * Naming format, formatter, etc.
  * Dealing with turns in format, summarize, compare
    * Summarizer.summarize status cell
  * Registry becomes Models or ModelRegistry
  * pipelines becomes Pipelines or PipelineRegistry
  * Test default formatter, summarizer, pass_predicate, turn_mapper
  * Consistant turn_mapper name
  * # TODO: move these functions out of registry.
  * # TODO: what about optional uuid_prefix parameter?
  * # TODO: lazy construction of models on first use
  * 'Pipeline2' object has no attribute 'diff_configs'
  * x breaking change notes
  * x directory walk to find configs
  * x configs can be json or yaml
  * .gotaglio.credentials.json/yaml
  * .gotaglio.models.json/yaml
  * x read_data_file
  * x write_data_file
  * x extract tokenizer to own file
  * x passed predicate moves to PipelineSpec
  * pipeline.diff_configs()
  * pipeline preview() operation
  * x Pipelines should have the ability to locally register models.
  * . Extensible format
    * Port cli samples - simple, calculator, menu
    * Port notebooks
    * Create tour demo and docs - show all commands and sub-commands
  * Extensible compare
  * Rewrite samples, update documentation
  * Type annotations everywhere
    * Use modern tpying
    * mypy?
    * search everywhere for `typing`
  * x In pipeline2.py, line 77: "user": turn["user"], # TODO: configurable
  * x Summary
    * x Complete: 6/2 (300.00%) - two cases with three steps each
    * x Pass/fail predicate
    * x keywords column
  * x Log logs\43131cfe-1627-4d6f-ae48-5e4ee5527934.json shows `turn` object and `case` object
  * x Rename TurnSpec to TurnMapping?
    * x Can't copy/remap all fields - should instead get fields from case. e.g. need `user` and `base`
  * x Extensible perfect and flakey models
  * Exception when `expected != "answer"` - summary has no rows
  * Path to models.json and .credentials.json
* Before
  * Configurable pipeline with turns
    * Configurable
      * Initial value field
      * "user" field for summarize()
      * tokenizer
      * repairs
    * mechanism to override summarize() and format()
    * compare() method
  * Lazily load tokenizer
  * Better error formatting in notebooks
    * e.g. missing models.json or .credentials.json
    * gt.run() should write log file, even if summarize() crashes.
  * Understand system configuration options
    * Perhaps have an override for turn count
  * Run individual pipeline turns - for service
  * Read and write JSON or YAML
    * Extension detect
    * utf-8 handling
    * System config for output format when no extension specified
* Top top
  * [Poetry vs uv](https://teams.microsoft.com/l/message/19:f470c3664251434a981ea790c11c7b61@thread.tacv2/1741214705520?tenantId=72f988bf-86f1-41af-91ab-2d7cd011db47&groupId=11dded2c-9d9a-470c-a312-e8eeceb5a1ab&parentMessageId=1741214705520&teamName=IS%20Engineering&channelName=GUILD%20-%20Software%20Engineering&createdTime=1741214705520)
  * Consider jsonl for cases
  * wire up evaluate_boolean_expression for keyword filtering
  * try subcommand - run a pipeline on example specified on command line
  * better/easier standard pipeline reuse
  * option to get config from environment?
    * For lightweight `gotag try 'a large coke'` iteration
  * Gotag.add_ids - option to use filename rather than object
  * Remove test.py, test2.py
  * x app_configuration
  * Recommended vscode extensions
  * x Should not crash if git is not available or repo not found.
  * Jupyter
    * See if progress bar can be used in Notebook.
    * x IPython.display for markdown and newlines. May need to make library calls log or return strings.
    * x Remove print statements from library calls? What about real-time messages?
    * x Accept objects of id prefixes
  * Rename gotag package to gotaglio or vice versa
  * Refactor for Jupyter notebooks
    * Redo/simplify notebook
    * Add Jupyter comments to sample
    * log folder
      * x Likely need a configuration object that provides access to log_path
        * x It is too easy to import with from and get a copy.
      * Save runlog - need to unify code for creating log folder, etc.
      * Ability to set log folder in notebooks
        * Maybe defaulting to the notebook folder is good?
      * format second id can be number or prefix. Number specifies ordinal position.
      * Error handling in get_files_sorted_by_creation() when log folder not found
      * logpath setting
    * Move summarize, format, compare from Registry
    * Convert DAG and menu samples to new architecture
    * Idea
      * Sort out entry points
        * Director.summarize_results()
        * Gotag.summarize()
        * Registry.summarize()
      * x Runtime passes console_factory to pipeline methods or to pipeline constructor
      * x console = console_factory("text/markdown")
      * x console = make_console("text/markdown")
      * x callable instance __call__
    * decide whether shared should be exposed?
      * would it make sense to have one namespace of end-user functions (vs internal functions)
    * x renderer parameter
    * x rendering rich, markdown, html, etc in notebooks
    * x move display(), print_to_string() to shared
    * x run
    * x rerun
    * x summarize
    * x compare
    * x load
    * save
  * Unified error reporting - catch orginal and raise helpful version.
  * Parse key=value parameter values? float, boolean, string?
  * Review statics in Edit, EditType and DiffResult
  * Tool should print help message if models.json not found
  * Tool should print help message if .creadentials.json not found
  * Git release tag and version
  * version subcommand - semver and git sha
  * Improve documentation
  * Documentation for Model.metadata(). What is it used for?
  * Document tree diff algorithm
  * .gitignore models.json
  * Rename .credentials.json and update .gitignore
  * Can models subcommand list pipeline-specific models like perfect, parrot, and flakey?
  * Consider making Summarize, Format and Compare optional
  * Usage should show name of script
  * Utility to test model connection and auth
  * gotag help format should explain what format does. Other subcommands as well.
  * OpenAI and Anthropic APIs
  * The --concurrancy option is task-level. Do we also want stage-level control?
  * Consider use of TaskGroups in dag.py. Exception handling and cancellation.
  * Summarize should print out run configuration details
    * x Really want to call out patches over default_config
    * How to get cases file? Add cases to metadata? Copy cases in rerun?
  * Documentation for a stand-alone BOT application based on gotaglio pipelines
  * x Deal with nested call from compare() to summarize() in simple.py (workaround: removed the call)
  * x Implement menu sample
  * x Merge mhop/refactor1 into main
  * x Merge to main - add a tag?
  * x Test import from other project
  * x GitHub CodeSpaces and dev container and documentation
    * x Make gotag.sh executable
    * x Ensure gotag.sh is on path
    * x Set up venv?
  * x Review all static members
  * x Ability *to* run without models.json - just use built in models.
  * x Merge process_one_case() with run_dag()
    * x Exception handling
  * x Dag and Linear pipeline diagrams for documentation
  * x Rename SamplePipeline to SimplePipeline
  * x Move/reorder pipeline parameter in run
  * x Help subcommand should ignore extra arguments
  * Configuration patching
    * x Prompt class
    * x Internal class
    * x Helpful error message - display glom path and prompt, list other required patches
    * Interactive user prompt for missing config
    * x Better error reporting and usage regarding missing configuration
  * x Rerun should call out patch values that are different
  * simple.py
    * x Rename context parameter in simple.py.
    * x Fix comments for Flakey, Perfect, Parrot.
    * x Implement compare()
    * Update summary() to report errors.
  * In logs\777d0acd-0ed0-495b-ba3d-98496d9cf2b4.json
    * "message": "Context: Extracting numerical answer from LLM response. ...
    * Better wording in case we want to put the first few words in the summary table.
  * Consider removing tree-diff. Might need for menu sample.
  * x One sample that unifies all pipelines? Maybe revert to gotag.bat?
  * Registry.pipeline should actually create the pipeline - needs a config param
  * Better error message
    * when setting infer.model=gpt3.5 instead of infer.model.name=gpt3.5
  * x Deprecate or remove merge_configs()?
  * Samples
    * Move data to samples
    * upgrade api.py - erase
    * upgrade menu.py - keep?
  * Make summarize resilient to missing ids
  * Organize logs by pipeline
      * OPTION: pipeline folder?
      * OPTION: pipeline suffix?
      * Enforce pipeline names can be part of filename. No delimiters.
  * rerun detect git mismatch
  * Diagnose startup time
  * DAG pipelines
  * x Model not found error
    * x python apps\simple.py run data\api\cases.json sample prepare.template=data\api\template.txt infer.model.name=parrot
    * x Detect and report before run summary
    * x List available models
  * x Move run code from Registry
  * x Optional case id for format
  * x Remove gotaglio/tools folder
  * x Template for models.json, .credentials.json
  * x Rename Runner to Registry
    * x runner_factory() => create_registry()?
  * x Rename piplines.py to singular pipeline.py
  * x Rename apps to samples
  * 
  * x User_Fill or CmdLine or User or Param
  * 
  * End-to-end demo
  * Table helper functions for summarize
  * Use better formatting/word wrap for list pipelinesn
  * 
  * Pass config to pipeline?
  * Table formatting utilities
  * Simpler lazy initialization for pipelines
  * Help with compare function
  * Break out log folders by pipeline - enforce pipeline name can be legal file name
  * format command shows pass/fail status and edit distance
  * Examples to README.md
    * Update for new folders - api and menu
    * Also document cases data structure JSON
  * Subcommand to add/remove tags from uuid or LATEST
  * Subcommand to format case as markdown
  * Should logging be in folders named after pipelines?
    * Pipeline names must be legal filenames
  * Don't print out run configuration if command line fails before starting (e.g. bad pipeline name)
* Top
  * prefix search should only find uuid.json files
  * Compare
    * Mention git sha diffs
    * Mention config diffs
    * --compare flag for run and rerun
    * Compare and Summarize don't need to be in runner.py
    * x Short uuids
    * x Summary row with counts
    * x Keywords column
    * x Enforce same pipeline
    * x Check for identical runs
    * x Summmarize cases in common and those in one run only
    * x Group common cases by type of diff
    * x Totals and percentages at bottom
  * example.py
    * Need a way to pass configurations to stages. Runner should do this.
    * Model configuration for infer needs to be passed to model constructor
    * is there any way of removing default values from the config?
    * should summarize() and compare() be static class methods?
    * x Some means of getting static name and description from pipeline before constructing
  * Extract command - extract JSON for specific case in specific run
  * Keyword boolean filter expressions
    * Would these filter the cases in the log file?
  * list_models() should show models introduced by pipeline
  * x Rerun command
    * x Wire up concurrancy for run and rerun
    * x Handle `latest` prefix
    * x Function to get logfilename from prefix or throw
    * x Extract cases from log file
    * x Unified pipeline configuration architecture
  * Convert pipeline into pojo with description and key mapping
    * x name
    * x description
    * key mapping
    * Key-value shortcuts, eg prepare.template => template, infer.model.name => model
    * help
  * Extract flakey and perfect for reusable mocks
  * Use rich consistantly
    * Replace print()
    * bias towards tools/subcommands
    * avoid elsewhere
    * is it ok for pipeline summarization and compare to use rich?
  * Guard against command-line key-value configure of bad paths
    * e.g. infer.model=x instead of infer.model.name=x
    * At least show better error message
    * glom.core.PathAccessError: could not access 'name', part 2 of Path('infer', 'model', 'name'), got error: AttributeError("'str' object has no attribute 'name'")
  * x Remove exception handlers not in stages
  * Exception enhancer
    * Add exception trace when there isn't a context? When the exception is unknown?
    * x Adds context and information to raw exceptions (e.g. which pipeline, which case)
    * Integrate `with ExceptionContext` into codebase
    * Reevaluate need for except statements.
    * with log_context() ...
  * x Remove colorama
  * x Remove Echo model
  * pipeline spec
    * pojo object
      * name
      * description
      * configuration
      * stages
      * static
        * summarize
        * compare
        * oneline summarize
  * infer.mock = flakey | perfect | None
  * . Boolean expression parser
    * Test suite
      * Original
      * Words [a-zA-Z_.][a-zA-Z_.-0-9]
  * Logger architecture
    * Console logging
    * File logging
  * describe command
    * pretty prints a case of a run
  * ability to run each case multiple times
  * from concurrent.futures import ThreadPoolExecutor
    * See https://github.com/Textualize/rich/blob/master/examples/downloader.py
  * . progress bar - https://rich.readthedocs.io/en/latest/progress.html
    * Revisit progress bar hide fix in Runner.go()
  * Clean up summary code
  * . summary keywords
  * x add-ids subcommand
    * x -f or --force
  * x Break out subcommands folder
  * x Flat dict merge algorithm
  * x Table layout algorithm
    * x Do ANSI terminal characters contribute to string length?
  * Schema
    * Header - promoted to database row
    * Config/Metadata - json in database
    * Details - json in database
  * Try out
    * gpt4=mini
    * entire suite
  * BUGS
    * x Summary table score border on right side and curor in score column
    * Why is score 10.99899...? Why not 11? Assuming I subtract .002.
      * phi3 model
      * python apps\example.py summarize 575
    * repair is not mult-threaded - reset id
    * repair doesn't seem to work correctly for first case in
      * python apps\example.py run data\small.json simple2 template=data\template.txt model=gpt3.5
      * See trees at end of this file
      * Also shouldn't have to change attribute quantity to 1 if this is the default
  * Summarize and Compare
    * compare configs (e.g. pipeline, template, model)
    * compare results
      * cases in common
      * cases not in common
      * passes in common
      * failures no in common
    * aggregates
    * detailed compare of two runs
    * brief table compare or summary of n runs
    * Fixed width columns
    * summarize and compare should be able to use SHA prefix of `LAST`
    * display tags
    * option to generate csv
  * keywords and tags
    * show them in the summary and compare output to characterize failures
    * query by Boolean expression
  * Models command
    * Display description
  * Pipelines command
    * Display description
  * Documentation
    * What are the key responsibilities of a pipeline?
  * Assess stage
    * x Modify cases
    * x Bring over tree compare
    * x Update summary
    * Determine whether tree diff is working correctly
  * x Multi-turn
    * x Modify template
  * Architecture
    * How does summarize if pipeline used is no longer available?
    * pipeline registration chicken+egg - name not available when factory registered
    * runner.summarize() should return string
  * Tactical
    * May not always need jinja2 template
    * verify poetry on clean venv
    * x rename run.py to runner.py
    * x gotag.bat conflicts with gotag.py
    * figure out where gotag.py belongs
    * clean up unused code
  * Sample pipeline
    * data folder with cases
    * x pipeline code in separate folder with imports
  * README.md
    * Overview
    * Build instructions
    * Run examples
  * x Create github repo
  * x Refactor for example/gotaglio split
    * x Move load_template() from pipeline.py to templating.py
    * x Move SimplePipeline from pipelines.py to apps/example.py
    * x Pass pipelines dict to main() and Runner constructor.
    * x Convert main() to a class. Make constructor take models and pipelines. Create runner.
    * x Retarget gotag.bat, gotag.sh to apps/example
    * x Remove old gotag.py
  * Links
    * On python modules
      * https://stackoverflow.com/questions/14132789/relative-imports-for-the-billionth-time
      * 


  ~~~
  "extract": {
    "items": [
      {
        "quantity": 1,
        "name": "latte",
        "options": [
          {
            "quantity": 1,
            "name": "half caf"
          },
          {
            "quantity": 1,
            "name": "vanilla syrup",
            "amount": "regular"
          }
        ]
      }
    ]
  },
~~~

~~~
  "query": "a skinny half-caf latte with two pumps of vanilla",
  "expected": {
    "items": [
      {
        "quantity": 1,
        "name": "latte",
        "options": [
          {
            "quantity": 1,
            "name": "half caf"
          },
          {
            "quantity": 1,
            "name": "nonfat milk"
          },
          {
            "quantity": 2,
            "name": "vanilla syrup"
          }
        ]
      }
    ]
  }
~~~

~~~
  "assess": {
    "op": "REPAIR",
    "cost": 4,
    "steps": [
      "0.1:vanilla syrup: change name to `nonfat milk`",
      "0.1:vanilla syrup: remove amount",
      "1.2:vanilla syrup: insert default version",
      "1.2:vanilla syrup: change attribute(quantity) to '2'"
    ]
  }
~~~


## Service

* schemas
    GET returns a list of schemas
    POST creates a new schema and returns its id
* schemas/id
    GET returns the schema description
    DELETE
    Schemas are immutable
    The schema defines the type system for is cases
* schemas/id/cases
    GET returns all cases or those matching query
    POST schemas/id/cases creates a new case and returns its id
* schemas/id/aschemas
    GET returns a list of annotation-schemas
    POST creates a new annotation-schema and returns its id
    The annotation-schema contains templates for the cases and the annotation create/edit form
* schemas/id1/aschems/id2/
    GET returns all annotations or those matching query
    POST creates a new annotation-schema
    PATCH modifies an annotation

## Views

* Table of case join annotation.
    Filtering
    Sorting
    Editing annotation