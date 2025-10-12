import asyncio
import pytest

from gotaglio.dag import Dag, run_dag


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

    context = await run_dag(dag, {})

    a1 = context["stages"]["A"]
    b1 = context["stages"]["B"]
    c1 = context["stages"]["C"]
    d1 = context["stages"]["D"]

    assert a1["end"] - a1["start"] == 1
    assert a1["end"] <= b1["start"]
    assert a1["end"] <= c1["start"]

    # b and c start in some order, b ends
    assert b1["end"] - a1["end"] == 3
    assert b1["end"] <= d1["start"]

    # b and c start in some order, b ends, c ends
    assert c1["end"] - a1["end"] == 4
    assert c1["end"] <= d1["start"]

    assert d1["end"] - d1["start"] == 1
