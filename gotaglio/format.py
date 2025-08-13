from typing import Callable

from .helpers import IdShortener
from .pipeline_spec import PipelineSpec
from .shared import to_json_string
from .tokenizer import tokenizer


# If uuid_prefix is specified, format those cases whose uuids start with
# uuid_prefix. Otherwise, format all cases.
def format(
    spec: PipelineSpec,
    make_console: Callable,
    runlog: dict[str, any],
    uuid_prefix: str | None = None,
) -> None:
    console = make_console("text/markdown")
    if callable(spec.formatter):
        spec.formatter(console, runlog)
    else:
        formatter_spec = spec.formatter
        mapping_spec = spec.mappings
        using_turns = mapping_spec.turns is not None

        # compress = (
        #     str(glom(runlog, "metadata.pipeline.prepare.compress", default="False"))
        #     == "True"
        # )

        # complete = format_menu(self.type_defs, compress)
        # complete_tokens = len(self._tokenizer.encode(complete))

        console.print(f"## Run: {runlog['uuid']}")

        results = runlog["results"]
        if len(results) == 0:
            console.print("No results.")
        else:
            # To make the summary more readable, create a short, unique prefix
            # for each case id.
            short_id = IdShortener([result["case"]["uuid"] for result in results])

            for result in results:
                if uuid_prefix and not result["case"]["uuid"].startswith(uuid_prefix):
                    continue
                turn_count = (
                    f" ({len(result['stages']['turns'])} turn{'s' if len(result['stages']['turns']) != 1 else ''})"
                    if using_turns
                    else ""
                )
                console.print(f"## Case: {short_id(result['case']['uuid'])}{turn_count}")

                if formatter_spec.before_case:
                    console.print(formatter_spec.before_case(result))

                # TODO: configurable
                console.print(
                    f"**Keywords:** {', '.join(result['case'].get('keywords', []))}  "
                )
                console.print()

                turns = result["stages"]["turns"] if using_turns else [result]
                for index, turn_result in enumerate(turns):
                    if index > 0:
                        console.print("---")
                    else:
                        console.print()
                    if turn_result["succeeded"]:
                        cost = turn_result["stages"][
                            "assess"
                        ]  # TODO: configurable - use passed predicate
                        if cost == 0:
                            console.print(f"### Turn {index + 1}: **PASSED**  ")
                        else:
                            console.print(
                                f"### Turn {index + 1}: **FAILED:** cost={cost}  "
                            )
                        console.print()

                        if formatter_spec.before_turn:
                            console.print(formatter_spec.before_turn(turn_result))
                        # TODO: configurable
                        input_tokens = sum(
                            len(tokenizer.encode(message["content"]))
                            for message in turn_result["stages"][
                                "prepare"
                            ]  # TODO: configurable ["messages"]
                        )
                        # console.print(f"Complete menu tokens: {complete_tokens}  ")
                        console.print(
                            f"Input tokens: {input_tokens}, output tokens: {len(tokenizer.encode(turn_result['stages']['infer']))}"
                        )
                        console.print()

                        for x in turn_result["stages"][
                            "prepare"
                        ]:  # TODO: configurable ["messages"]
                            if (
                                x["role"] == "assistant" or x["role"] == "system"
                            ):  # TODO: configurable
                                console.print(f"**{x['role']}:**")
                                console.print("```json")
                                console.print(x["content"])
                                console.print("```")
                            elif x["role"] == "user":
                                console.print(f"**{x['role']}:** _{x['content']}_")
                            console.print()
                        console.print(f"**assistant:**")
                        console.print("```json")
                        console.print(to_json_string(turn_result["stages"]["extract"]))
                        console.print("```")
                        console.print()

                        if formatter_spec.after_turn:
                            console.print(formatter_spec.after_turn(turn_result))

                        # TODO: configurable
                        if cost > 0:
                            console.print(f"**expected {turn_result["case"]["answer"]}:**")
                            # console.print("**Repairs:**")
                            # for step in turn_result["stages"]["assess"]["steps"]:
                            #     console.print(f"* {step}")
                        # else:
                        #     console.print("**No repairs**")

                        console.print()
                        # console.print("**Pruning query**:")
                        # for x in turn_result["stages"]["prepare"]["full_query"]:
                        #     console.print(f"* {x}")
                        # console.print()

                    else:
                        console.print(f"### Turn {index + 1}: **ERROR**  ")
                        console.print(f"Error: {turn_result['exception']['message']}")
                        console.print("~~~")
                        console.print(f"Traceback: {turn_result['exception']['traceback']}")
                        console.print(f"Time: {turn_result['exception']['time']}")
                        console.print("~~~")

                if formatter_spec.after_case:
                    console.print(formatter_spec.after_case(result))
