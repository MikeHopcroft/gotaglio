import argparse
from copy import deepcopy
from glom import assign, glom
import json
import os
from pathlib import Path
import platform
import yaml

from .templating import jinja2_template
from .constants import app_configuration


def format_list(values):
    if not values:
        return ""
    elif len(values) == 1:
        return values[0]
    elif len(values) == 2:
        return f"{values[0]} and {values[1]}"
    else:
        return f"{', '.join(values[:-1])}, and {values[-1]}"


def parse_key_value_args(args):
    """Parse key=value arguments into a dictionary."""
    config = {}
    for arg in args:
        if "=" not in arg:
            raise argparse.ArgumentTypeError(
                f"Invalid format: '{arg}'. Expected key=value."
            )
        key, value = arg.split("=", 1)
        config[key] = value
    return config


def get_files_sorted_by_creation(folder_path):
    """
    Get a list of file names in a folder, sorted by creation date.

    Args:
        folder_path (str or Path): Path to the folder.

    Returns:
        list: File names sorted by creation date.
    """
    # Ensure the folder path is a Path object
    folder = Path(folder_path)

    # Get a list of files in the folder (excluding directories)
    files = [(f.stem, get_creation_time(f)) for f in folder.iterdir() if f.is_file()]

    # Sort files by creation time
    sorted_files = sorted(files, key=lambda f: f[1])

    return sorted_files


def get_creation_time(path):
    if platform.system() == "Windows":
        return os.path.getctime(path)
    elif platform.system() == "Darwin":  # macOS
        return os.stat(path).st_birthtime
    else:  # Linux and other Unix-like systems
        return os.stat(path).st_ctime


def get_filenames_with_prefix(folder_path, prefix):
    """
    Returns a list of filenames in the specified folder that start with the given prefix.

    :param folder_path: Path to the folder to search.
    :param prefix: The prefix to filter filenames.
    :return: List of filenames that start with the prefix.
    """
    filenames = [
        filename
        for filename in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, filename))
        and filename.startswith(prefix)
    ]
    return filenames


def read_log_file_from_prefix(prefix):
    return read_json_file(log_file_name_from_prefix(prefix))


def log_file_name_from_prefix(prefix):
    log_folder = app_configuration["log_folder"]
    if prefix.lower() == "latest":
        filenames = get_files_sorted_by_creation(log_folder)
        if not filenames:
            raise ValueError(f"No runs found in {log_folder}'.")
        return os.path.join(log_folder, filenames[-1][0] + ".json")
    else:
        filenames = get_filenames_with_prefix(log_folder, prefix)
        if not filenames:
            raise ValueError(f"No runs found with prefix '{prefix}'.")
        if len(filenames) > 1:
            raise ValueError(
                f"Multiple runs found with prefix '{prefix}':\n{'\n'.join([f"  {os.path.join(log_folder, n)}" for n in filenames])}"
            )

        return os.path.join(log_folder, filenames[0])


def read_text_file(filename):
    with open(filename, "r", encoding="utf-8") as file:
        result = file.read()
    return result


def read_json_file(filename, optional=False):
    if optional and not os.path.isfile(filename):
        return {}
    with open(filename, "r", encoding="utf-8") as file:
        result = json.load(file)
    return result


def read_data_file(filename, optional=False, search=False):
    """
    Find and read a json or yaml file and return its content.
    The file format is determined by the file extension.
      .json files are parsed as JSON.
      .yaml .yml files are parsed as YAML.

    If `search` is True, the function will search for the file in folders
    along the path from the current working directory to the root directory.

    If the file does not exist and `optional` is True, return an empty
    dictionary. Otherwise, raise a FileNotFoundError.

    :param filename: The path to the file to read.
    :param optional: If True, return an empty dictionary if the file does not exist.
    :param search: If True, search for the file in parent directories.
    :return: The content of the file as a dictionary or an empty dictionary if the file does not exist.
    """

    def find_file(filename, search_path=None):
        """Helper function to find a file, optionally searching parent directories."""
        if search_path is None:
            search_path = Path.cwd()

        # First try the direct path
        file_path = Path(filename)
        if file_path.is_absolute():
            return file_path if file_path.exists() else None

        # If not absolute, try relative to search_path
        candidate = search_path / filename
        if candidate.exists():
            return candidate

        # If search is enabled, look in parent directories
        if search:
            current = search_path
            while current != current.parent:  # Stop at root
                candidate = current / filename
                if candidate.exists():
                    return candidate
                current = current.parent

        return None

    # Find the file
    file_path = find_file(filename)

    if file_path is None:
        if optional:
            return {}
        else:
            raise FileNotFoundError(f"File not found: {filename}")

    # Determine file format from extension
    suffix = file_path.suffix.lower()

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            if suffix == ".json":
                return json.load(file)
            elif suffix in [".yaml", ".yml"]:
                return yaml.safe_load(file)
            else:
                raise ValueError(
                    f"Unsupported file format: {suffix}. Only .json, .yaml, and .yml are supported."
                )
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise ValueError(f"Error parsing {suffix} file '{file_path}': {e}")
    except Exception as e:
        raise RuntimeError(f"Error reading file '{file_path}': {e}")


def write_json_file(filename, data):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def write_data_file(filename, data):
    """
    Write data to a file in JSON or YAML format based on the file extension.
    If the file extension is .json, the data will be written as JSON.
    If the file extension is .yaml or .yml, the data will be written as YAML.

    :param filename: The path to the file to write.
    :param data: The data to write to the file.
    """
    suffix = Path(filename).suffix.lower()
    with open(filename, "w", encoding="utf-8") as file:
        if suffix == ".json":
            json.dump(data, file, indent=2, ensure_ascii=False)
        elif suffix in [".yaml", ".yml"]:
            yaml.safe_dump(data, file, allow_unicode=True)
        else:
            raise ValueError(f"Unsupported file format: {suffix}. Only .json, .yaml, and .yml are supported.")


def to_json_string(data):
    """
    Convert a Python object to a JSON string with UTF-8 encoding.

    :param data: The Python object to convert.
    :return: A JSON string representation of the object.
    """
    return json.dumps(data, indent=2, ensure_ascii=False)


def parse_patches(path_bindings):
    """Parse key=value arguments into a dictionary."""
    patch = {}
    for binding in path_bindings:
        if "=" not in binding:
            raise ValueError(f"Invalid patch: '{binding}'. Expected key=value.")
        key, value = binding.split("=", 1)
        key = key.strip()
        value = value.strip()
        patch[key] = value
    return patch


def apply_patch(target_dict, patches):
    """
    Create a new dictionary that results from applying a series of
    dot-separated key-value pairs as a patch to a a deep copy of an
    existing dictionary.

    :param target_dict: The dictionary to be copied and patched.
    :param patches: A dictionary with dot-separated keys and their corresponding values.
    """
    result = deepcopy(target_dict)
    apply_patch_in_place(result, patches)
    return result


def apply_patch_in_place(target_dict, patches):
    """
    Modify an existing dictionary by applying a series of dot-separated
    key-value pairs as a patch to a a deep copy of an existing dictionary.

    :param target_dict: The dictionary to be patched.
    :param patches: A dictionary with dot-separated keys and their corresponding values.
    """
    for key, value in patches.items():
        # Ensure value is not a dict
        if isinstance(value, dict):
            raise ValueError(f"Invalid patch for '{key}'. Value cannot be a dict.")
        # Ensure result[key] is not a dict
        node = glom(target_dict, key, default=None)
        if isinstance(node, dict):
            candidates = [k for k in node.keys() if not isinstance(node[k], dict)]
            tip = (
                "Did you mean\n" + "\n".join(f"  {key}.{k}" for k in candidates)
                if len(candidates) > 0
                else ""
            )
            raise ValueError(
                f"Invalid patch for '{key}={value}'. Patch would overwrite a dict. {tip}"
            )
        assign(target_dict, key, value, missing=dict)


def flatten_dict(d, parent_key="", sep="."):
    """
    Recursively flattens a hierarchical dictionary.

    Args:
        d (dict): The dictionary to flatten.
        parent_key (str): The base key for recursion (used for nested levels).
        sep (str): Separator used to join keys.

    Returns:
        dict: A flattened dictionary, where keys are glom-style.
              See https://glom.readthedocs.io/en/latest/.
    """
    items = {}
    for key, value in d.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, dict):
            # Recurse into nested dictionaries
            items.update(flatten_dict(value, new_key, sep=sep))
        else:
            # Add the value with the flattened key
            items[new_key] = value
    return items


def minimal_unique_prefix(uuids):
    """
    Given a list of UUIDs, return a list of minimal length prefixes
    that uniquely identify each UUID. All prefixes will have the length
    of the longest required prefix.

    :param uuids: List of UUID strings
    :return: List of minimal unique prefixes with uniform length
    """
    prefixes = []
    max_length = 0

    # First pass: determine the minimal unique prefix for each UUID
    for uuid in uuids:
        for length in range(1, len(uuid) + 1):
            prefix = uuid[:length]
            # Check if prefix is unique among all UUIDs
            if all(not other.startswith(prefix) or other == uuid for other in uuids):
                prefixes.append(prefix)
                max_length = max(max_length, length)
                break

    return max_length


def build_template(config, template_file, template_source_text):
    # If we don't have the template source text, load it from a file.
    if not isinstance(
        glom(config, template_source_text, default=None),
        str,
    ):
        assign(
            config,
            template_source_text,
            read_text_file(glom(config, template_file)),
        )

    # Compile the template.
    return jinja2_template(glom(config, "prepare.template_text"))
