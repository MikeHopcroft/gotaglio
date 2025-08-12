import uuid

from ..shared import read_json_file, write_json_file

def add_ids(filename, force):
    print(f"Adding IDs to {filename}. Force: {force}")

    cases = read_json_file(filename, False)
    add_count = 0
    for case in cases:
        if "uuid" not in case or force:
            case["uuid"] = str(uuid.uuid4())
            add_count += 1

    write_json_file(filename, cases)

    print(f"Total cases: {len(cases)}")
    print(f"UUIDs added: {add_count}")
