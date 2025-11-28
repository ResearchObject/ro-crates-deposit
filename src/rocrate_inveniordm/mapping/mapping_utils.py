import json
import copy
from importlib import resources
import rocrate_inveniordm.mapping as mapping


class MappingException(RuntimeError):
    """Used for errors that relate to the loaded mapping."""

    def __init__(self, message):
        self.message = (
            f"The loaded mapping is invalid: {message} "
            "Please inform the rocrate-inveniordm package maintainers by raising an "
            "issue on GitHub: "
            "https://github.com/ResearchObject/ro-crate-inveniordm/issues"
        )
        super().__init__(self.message)


def load_mapping_json() -> dict:
    """Load the mappings from the mapping.json file included with the package

    :return: Dictionary containing the mapping
    """
    mapping_file = resources.files(mapping) / "mapping.json"
    with mapping_file.open("r") as f:
        mapping_json = json.load(f)
    return mapping_json


def get_arrays_from_from_values(input_list: list) -> list:
    """Given a list of "from-values" for a mapping, find which of them may be arrays.
    "From-values" describe RO-Crate metadata fields which will be converted to DataCite
    fields.

    For example, the from-value "$author[].name" relates to the "name" property within
    any entity which is listed as an "author" of another entity. The $ indicates a
    cross-reference, and the [] indicates that the "author" property may be a dict or
    an array.

    :param input_list: A list of from-values.
    :return: A list of paths which include arrays.
    """
    output_set = set()
    for string in input_list:
        delimiter_index = string.rfind("[]")
        if delimiter_index != -1:
            processed_string = string[
                : delimiter_index + 2
            ]  # Include the "[]" in the output
            output_set.add(processed_string)
    output_list = list(output_set)
    return output_list


def contains_atatthis(value):
    """
    Checks if the given value contains the string "@@this".
    The value can be a string or a dictionary.

    :param value: The value to check.
    :return: True if the value contains "@@this", False otherwise.
    """
    if isinstance(value, str):
        return "@@this" in value
    elif isinstance(value, dict):
        for key, v in value.items():
            if isinstance(v, str):
                if "@@this" in v:
                    return True
            else:
                return contains_atatthis(value[key])

    return False


def clean_key(key: str) -> str:
    """Given a key from the mapping, return the key as it would appear inside an entity,
    Essentially, this strips any $ and [] characters which are used in the mapping keys.

    :param key: The mapping key to clean
    :return: The cleaned key
    """
    return key.replace("[]", "").replace("$", "")


def format_value(format, value):
    """
    Formats the given value according to the given format.
    The format can be a string or a dictionary.
    If the format is a string, the value is inserted at the position of @@this.
    If the format is a dictionary, the value is inserted at the position of @@this in
    each value of the dictionary.
    TODO rename to be less ambiguous about purpose

    For example, if the format is {"a": "@@this", "b": "c"}, and the value is "d", the
    result is {"a": "d", "b": "c"}.

    :param format: The format to use.
    :param value: The value to insert.
    :return: The formatted value.
    """

    # If not copied, generates a bug when arrays are used at "from" in the mapping
    new_value = copy.deepcopy(format)

    if isinstance(new_value, str):
        return new_value.replace("@@this", value)
    elif isinstance(new_value, dict):
        for key, v in new_value.items():
            new_value[key] = format_value(v, value)
        return new_value
    elif isinstance(new_value, bool):
        return new_value
    else:
        raise TypeError(
            f"Format must be a string, dictionary, or bool, but is {type(new_value)}."
        )


def setup_dc() -> dict:
    """Create an template for the DataCite metadata. Assumes that the record and its
    files will be public and not embargoed.

    See https://inveniordm.docs.cern.ch/reference/metadata/#metadata for details on the
    DataCite format.

    :return: Dictionary in DataCite metadata format
    """
    dc = {
        "access": {
            "record": "public",  # public or restricted; 1
            "files": "public",  # public or restricted; 1
            "embargo": {"active": False},  # 0-1
        },
        "metadata": {},
        "files": {"enabled": True},
    }
    return dc
