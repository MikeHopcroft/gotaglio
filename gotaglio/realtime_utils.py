from typing import Iterable, Mapping, Any


def save_events_jsonl(events: Iterable[Mapping[str, Any]], path: str) -> None:
    """
    Persist a list/iterable of event dicts to a JSONL file, one event per line.
    Events are written in the order provided.
    """
    import json

    with open(path, "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")


def assert_strictly_increasing_sequences(events: Iterable[Mapping[str, Any]]) -> None:
    """
    Raise AssertionError if the 'sequence' fields are not strictly increasing by 1.
    """
    last = None
    for ev in events:
        seq = ev.get("sequence")
        if last is None:
            last = seq
            continue
        if not isinstance(seq, int) or not isinstance(last, int) or seq <= last:
            raise AssertionError("Event sequences are not strictly increasing")
        last = seq
