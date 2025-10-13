from typing import List, TypeAlias, Union

SerializableValue: TypeAlias = Union[
    str, int, float, bool, None,
    dict[str, 'SerializableValue'],
    List['SerializableValue']
]

SerializableDict = dict[str, SerializableValue]

Case = SerializableDict
Configuration = SerializableDict
