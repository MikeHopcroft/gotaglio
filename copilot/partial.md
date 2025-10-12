Notes about contemplated changes to allow previewing inference of individual turns.

## Scenario

Assist human labeller by using model to suggest an initial label, which can then be corrected if necessary.

## Goals

* Simple pipeline authoring.
* Preview turn preparation stages should have access to all previous turn data.

## Analysis

* Director.process_all_cases()
* Director.process_one_case()
* process_one_case() - in pipeline.py - has no real reason to exist - just calls run_dag() and completed()
* run_dag() - in dag.py, for loop over turns. Likely entry point for preview isolated turn.
* run_turn() - stubs turn data structure in context, handles timing, handles errors
* run_dag_helper() - processes stages in topological order
* make_task()
* run_task() - actaully invoke stage coroutine, handle timing and exceptions.

Dag class type safety:
* PipelineSpec.create_dag()
* Pipeline.get_dag()
* process_one_case()
* run_dag()
* run_turn()
* run_dag_helper() - converts from class Dag to dag dictionary in self.dag
* make_task()
* run_task()

Steps
* DAG_Execution_State data class
  * Factor out visited and live - these are used for graph check
* Create DAG_Execution_State for each run_dag() invocation
* 

## Inquiry

* What is PipelineSpec.expected for? It is for the mock models.

## Recommendations

* All cases are multi-turn. Remove special case for single turn.
  * Downside is that single-turn cases have one more level of indirection.
  * Upside is that library code is simpler.
* Redefine stage coroutine context parameter to include, configuration, results, and parameters.
  * Incorporating configuratation may simplify pipeline factory functions as they may not need to provide configuration values to be lexically captured  by coroutines.
  * Incorporating parameters may simplify plumbing in library because only one parameter is pass vs context, turn, isolated
  * Downside of incorporating configuration is it makes the immutable configuration pattern weaker.
  * Parameters can hold information in whether we're processing an isolated turn, and which turn we're on. This eliminates the need for convenience functions for identifying turns.
* Convert configuration into frozen data class.
* Menu sample extract() should have more robust fence stripping.
* Convert cases to frozen pydantic data classes. Incorporate user pydantic definitions.
* Convert context to dataclass
