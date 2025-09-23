I don't like the complexity of the run_dag() function (and the in-progress prototype of its successor, partial_run_dag()). The function executes an directed acyclic graph of asynchronous coroutines, while logging return values and errors.

The code is complex because it handles a number of co-mingled concerns:
- Orchestrating the execution of co-routines and logging results and errors over a single DAG.
- Running the DAG iteratively, once for each turn in a multi-turn test case. This involves detecting the multi-turn case, and providing coroutines with information about the current turn. The convention is for the coroutines to infer the turn number from the length of the turns[] array in the context. Note that the structure of the log is different for cases with and without turns.
- Performing a partial run for scenarios where one would like to know the output of a single coroutine inside a single turn, without expending the costs of running the entire DAG over all of the turns. The common scenario is support for a labeling tool which is collecting expected inference results for LLM test cases. In this scenario it would be desirable to sometimes start from the actual LLM's best guess. Since this is in the context of test case development, expected inference values already exist for all previous turns, so these can be used in lieu of rerunning the entire DAG over all of the turns.

Another form of complexity is for co-routine authors. They must know whether they are running in the context of a single turn (and must synthesize results from earlier turns) or a sequence of turns where the earlier results are available.

They also need to know which turn they are executing and where to find earlier turn results. I provided convenience functions to help here.

I would like to discuss strategies for reducing complexity, while also avoiding wholesale code duplication (in the case where I write separate functions for each case). I am open to suggestions for the existing approach or questions about the problem framing.