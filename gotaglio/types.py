from dataclasses import dataclass                                                   
from typing import Generic, TypeVar

CASE = TypeVar('CASE')
RESULT = TypeVar('RESULT')
STAGE = TypeVar('STAGE')

@dataclass
class Result(Generic[CASE]):
    result: CASE

@dataclass
class Context2(Generic[CASE, RESULT]):
    turn: int
    isolated: bool
    case: CASE
    result: Result[CASE]

@dataclass
class Status:
    succeeded: bool
    start: str
    end: str
    elapsed: float

@dataclass
class Stage(Generic[STAGE]):
    succeeded: bool
    value: STAGE | Exception