import asyncio
import pytest

from gotaglio.dag import Dag, run_dag


def test_valid_build():
    async def f(context):
        pass

    spec = [
        {"name": "A", "function": f, "inputs": []},
        {"name": "B", "function": f, "inputs": ["A"]},
        {"name": "C", "function": f, "inputs": ["A"]},
        {"name": "D", "function": f, "inputs": ["B", "C"]},
    ]

    # Should not raise an exception
    Dag.from_spec(spec)


def test_duplicate_name():
    async def f(context):
        pass

    spec = [
        {"name": "A", "function": f, "inputs": []},
        {"name": "A", "function": f, "inputs": ["A"]},
        {"name": "C", "function": f, "inputs": ["A"]},
        {"name": "D", "function": f, "inputs": ["B", "C"]},
    ]

    # Should raise an exception
    with pytest.raises(ValueError) as e:
        Dag.from_spec(spec)
    assert "Duplicate node name 'A'" in str(e.value)


def test_invalid_input():
    async def f(context):
        pass

    spec = [
        {"name": "A", "function": f, "inputs": []},
        {"name": "B", "function": f, "inputs": ["X"]},
        {"name": "C", "function": f, "inputs": ["A"]},
        {"name": "D", "function": f, "inputs": ["B", "C"]},
    ]

    # Should raise an exception
    with pytest.raises(ValueError) as e:
        Dag.from_spec(spec)
    assert "Node B: cannot find input 'X'" in str(e.value)


def test_duplicate_input():
    async def f(context):
        pass

    spec = [
        {"name": "A", "function": f, "inputs": []},
        {"name": "B", "function": f, "inputs": ["A", "A"]},
        {"name": "C", "function": f, "inputs": ["A"]},
        {"name": "D", "function": f, "inputs": ["B", "C"]},
    ]

    # Should raise an exception
    with pytest.raises(ValueError) as e:
        Dag.from_spec(spec)
    assert "Node B: duplicate input 'A'" in str(e.value)


def test_no_root():
    async def f(context):
        pass

    spec = [
        {"name": "A", "function": f, "inputs": ["D"]},
        {"name": "B", "function": f, "inputs": ["A"]},
        {"name": "C", "function": f, "inputs": ["A"]},
        {"name": "D", "function": f, "inputs": ["B", "C"]},
    ]

    # Should raise an exception
    with pytest.raises(ValueError) as e:
        Dag.from_spec(spec)
    assert "No nodes ready to run" in str(e.value)


def test_has_cycle():
    async def f(context):
        pass

    spec = [
        {"name": "A", "function": f, "inputs": []},
        {"name": "B", "function": f, "inputs": ["A", "D"]},
        {"name": "C", "function": f, "inputs": ["A"]},
        {"name": "D", "function": f, "inputs": ["B", "C"]},
    ]

    # Should raise an exception
    with pytest.raises(ValueError) as e:
        Dag.from_spec(spec)
    assert "Cycle detected: A -> B -> D -> B" in str(e.value)


def test_unreachable_nodes():
    async def f(context):
        pass

    spec = [
        {"name": "A", "function": f, "inputs": []},
        {"name": "B", "function": f, "inputs": ["A"]},
        {"name": "C", "function": f, "inputs": ["A"]},
        {"name": "D", "function": f, "inputs": ["B", "C"]},
        {"name": "E", "function": f, "inputs": ["F"]},
        {"name": "F", "function": f, "inputs": ["E"]},
    ]

    # Should raise an exception
    with pytest.raises(ValueError) as e:
        Dag.from_spec(spec)
    assert "The following nodes are unreachable: E, F" in str(e.value)

def test_valid():
    async def f(context):
        pass

    spec = [
        {"name": "A", "function": f, "inputs": []},
        {"name": "B", "function": f, "inputs": ["A"]},
        {"name": "C", "function": f, "inputs": ["A"]},
        {"name": "D", "function": f, "inputs": ["B", "C"]},
    ]

    # Should not raise an exception
    Dag.from_spec(spec)


@pytest.mark.asyncio
async def test_run():
    counter = 0

    def sequence():
        nonlocal counter
        counter += 1
        return counter

    async def work(name, time):
        start = sequence()
        await asyncio.sleep(time)
        end = sequence()
        return {
            "name": name,
            "start": start,
            "end": end,
        }


    async def a(context):
        return await work("A", 0.01)


    async def b(context):
        return await work("B", 0.01)


    async def c(context):
        return await work("C", 0.02)


    async def d(context):
        return await work("B", 0.01)

    spec = [
        {"name": "A", "function": a, "inputs": []},
        {"name": "B", "function": b, "inputs": ["A"]},
        {"name": "C", "function": c, "inputs": ["A"]},
        {"name": "D", "function": d, "inputs": ["B", "C"]},
    ]

    # Should not raise an exception
    dag = Dag.from_spec(spec)

    context = {"stages": {}}
    await run_dag(dag, context)

    a = context["stages"]["A"]
    b = context["stages"]["B"]
    c = context["stages"]["C"]
    d = context["stages"]["D"]

    assert a["end"] - a["start"] == 1
    assert a["end"] <= b["start"]
    assert a["end"] <= c["start"]

    # b and c start in some order, b ends
    assert b["end"] - a["end"] == 3
    assert b["end"] <= d["start"]

    # b and c start in some order, b ends, c ends
    assert c["end"] - a["end"] == 4
    assert c["end"] <= d["start"]

    assert d["end"] - d["start"] == 1


@pytest.mark.asyncio
async def test_stage_timing_detailed_and_positive():
    async def a(context):
        await asyncio.sleep(0.01)
        return "A-ok"

    async def b(context):
        await asyncio.sleep(0.02)
        return {"n": 1}

    spec = [
        {"name": "A", "function": a, "inputs": []},
        {"name": "B", "function": b, "inputs": ["A"]},
    ]
    dag = Dag.from_spec(spec)
    context = {"stages": {}}
    await run_dag(dag, context)

    A = context["metadata"]["stages"]["A"]
    B = context["metadata"]["stages"]["B"]

    # Timing metadata stored under top-level metadata.stages
    assert set(A.keys()) >= {"start", "end", "elapsed", "succeeded"}
    assert set(B.keys()) >= {"start", "end", "elapsed", "succeeded"}

    def parse_elapsed(s):
        h, m, rest = s.split(":")
        sec = float(rest)
        return (int(h) * 3600) + (int(m) * 60) + sec

    assert parse_elapsed(A["elapsed"]) > 0
    assert parse_elapsed(B["elapsed"]) > 0

    # Values preserved in raw stages
    assert context["stages"]["A"] == "A-ok"
    assert context["stages"]["B"]["n"] == 1


@pytest.mark.asyncio
async def test_multi_turn_timing_is_per_turn_only():
    async def a(context):
        await asyncio.sleep(0.001)
        return "A"

    async def b(context):
        await asyncio.sleep(0.001)
        return "B"

    spec = [
        {"name": "A", "function": a, "inputs": []},
        {"name": "B", "function": b, "inputs": ["A"]},
    ]
    dag = Dag.from_spec(spec)
    context = {
        "case": {
            "turns": [{"user": "t1"}, {"user": "t2"}],
        }
    }
    await run_dag(dag, context)

    # No top-level stages_detailed for multi-turn runs
    assert "stages_detailed" not in context

    assert len(context["turns"]) == 2
    for turn in context["turns"]:
        # Stage values remain raw
        stages = turn.get("stages")
        assert stages is not None
        assert set(stages.keys()) == {"A", "B"}
        # Timing metadata is stored under turn.metadata.stages
        md_stages = turn["metadata"].get("stages")
        assert md_stages is not None
        assert set(md_stages.keys()) == {"A", "B"}
        for name in ("A", "B"):
            md = md_stages[name]
            assert set(md.keys()) >= {"start", "end", "elapsed", "succeeded"}