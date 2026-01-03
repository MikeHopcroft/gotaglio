import re

from gotaglio.shared import minimal_unique_prefix


def IdShortener(composite_ids):
    parts = [parse_id(uuid) for uuid in composite_ids]

    using_uuids = all(parts)
    if not using_uuids:
        raise ValueError("Each case must have a valid composite id (uuid.n).")

    #
    # Ensure every case has a unique uuid.
    #
    unique = set(composite_ids)
    if len(composite_ids) != len(unique):
        raise ValueError("Each case must have a unique composite id (uuid.n).")

    prefix_len = max(minimal_unique_prefix([x[0] for x in parts]), 3)

    return lambda uuid: shorten(uuid, prefix_len)


def shorten(composite_id: str, prefix_len: int) -> str | None:
    """
    Shorten a composite id of the form uuid.n to a minimal unique prefix.
    If the id is not in the expected format, return None.
    """
    parts = parse_id(composite_id)
    if parts is None:
        return None
    uuid, n = parts
    return f"{uuid[:prefix_len]}{'.' + str(n) if n is not None else ''}"


def parse_id(id: str) -> tuple[str, int | None] | None:
    """
    Parse an id string of the form uuid or uuid.n where uuid is a uuid v4 and
    n is a non-negative integer.
    Return a tuple of (uuid, n). If the ID is just a uuid, return (uuid, None).
    If the ID is not in the expected format, return None.
    """

    # TODO: REVIEW: Why do we need to check for a uuid v4 prefix here?
    match = re.match(
        r"^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})(?:\.(\d+))?$",
        id,
    )
    if match:
        uuid, n = match.groups()
        return uuid, int(n) if n is not None else None
    return None

