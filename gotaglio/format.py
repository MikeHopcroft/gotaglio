from glom import glom

from .helpers import IdShortener
from .make_console import MakeConsole
from .pipeline_spec import PipelineSpec


# If uuid_prefix is specified, format those cases whose uuids start with
# uuid_prefix. Otherwise, format all cases.
def format(
    spec: PipelineSpec,
    runlog: dict[str, any],
    uuid_prefix: str | None = None,
) -> None:
    console_buffer = MakeConsole()
    console = console_buffer("text/markdown")
    if callable(spec.formatter):
        spec.formatter(console, runlog)
    else:
        formatter_spec = spec.formatter
        mapping_spec = spec.mappings
        using_turns = mapping_spec.turns is not None

        # TODO: model for saving state between formatter spec function calls
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
                # The uuid_prefix is used to filter out cases that do not match the prefix.
                if uuid_prefix and not result["case"]["uuid"].startswith(uuid_prefix):
                    continue
                turn_count = (
                    f" ({len(result['stages']['turns'])} turn{'s' if len(result['stages']['turns']) != 1 else ''})"
                    if using_turns
                    else ""
                )
                passed = (
                    # When using turns, check if all turns passed
                    all(
                        [
                            spec.passed_predicate(turn_result)
                            for turn_result in glom(result, "stages.turns", default=[])
                        ]
                    )
                    if using_turns
                    else spec.passed_predicate(result)
                )

                console.print(
                    f"## Case: {short_id(result['case']['uuid'])}{turn_count} - {"PASSED" if passed else "FAILED"}"
                )
                console.print(
                    f"**Keywords:** {', '.join(glom(result, 'case.keywords', default=[]))}  "
                )
                console.print()

                if formatter_spec and formatter_spec.before_case:
                    formatter_spec.before_case(console, result)

                turns = result["stages"]["turns"] if using_turns else [result]
                for index, turn_result in enumerate(turns):
                    format_one_turn(
                        spec, formatter_spec, console, index, result, turn_result
                    )

                if formatter_spec and formatter_spec.after_case:
                    console.print(formatter_spec.after_case(result))
    console_buffer.render()

def format_one_turn(spec, formatter_spec, console, index, result, turn_result):
    if index > 0:
        console.print("---")
    else:
        console.print()
    if turn_result["succeeded"]:
        if formatter_spec and formatter_spec.format_turn:
            formatter_spec.format_turn(console, index, turn_result)
        else:
            format_messages(
                console, turn_result["stages"]["prepare"], collapse=["system"]
            )
            console.print(f"**assistant:**")
            format_response(
                console, turn_result["stages"]["extract"]
            )
            console.print()

        console.print()
    else:
        console.print(f"### Turn {index + 1}: **ERROR**  ")
        console.print(f"Error: {turn_result['exception']['message']}")
        console.print("~~~")
        console.print(f"Traceback: {turn_result['exception']['traceback']}")
        console.print(f"Time: {turn_result['exception']['time']}")
        console.print("~~~")


def format_messages(console, messages, collapse: list[str] | None = None):
    """
    Format a list of messages for display.
    Each message is a dictionary with 'role' and 'content' keys.
    """
    for x in messages:
        if x["role"] == "assistant" or x["role"] == "system":
            console.print(f"**{x['role']}:**")
            should_collapse = collapse and x["role"] in collapse and large_text_heuristic(x["content"])
            if should_collapse:
                console.print("<details>\n<summary>Click to expand</summary>\n")
            format_response(console, x["content"])
            if should_collapse:
                console.print("\n</details>\n&nbsp;  \n")
        elif x["role"] == "user":
            console.print(f"**{x['role']}:** _{x['content']}_")
        console.print()

def format_response(console, value):
    if isinstance(value, dict):
        console.print("```json")
        console.print(x["content"])
        console.print("```")
    else:
        console.print(str(value))

def large_text_heuristic(text: str) -> bool:
    return len(text.splitlines()) > 20 or len(text) > 200

