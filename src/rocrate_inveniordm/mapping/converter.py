from __future__ import annotations

import json
import sys

import rocrate_inveniordm.mapping.condition_functions as cf
import rocrate_inveniordm.mapping.processing_functions as pf
from rocrate_inveniordm.mapping.mapping_utils import (
    MappingException,
    load_mapping_json,
    get_arrays_from_from_values,
    contains_atatthis,
    clean_key,
    format_value,
    setup_dc,
)
from rocrate_inveniordm.mapping.crate_utils import (
    dereference,
    rc_get_rde,
    get_value_from_rc,
)


def main():
    """
    For test purposes only.
    """
    if len(sys.argv) != 2:
        print("Usage: python converter.py <input_file> <output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = input_file.replace(".rc.json", ".dc.json")
    f = open(input_file)
    rc = json.load(f)

    output = convert(rc)

    with open(output_file, "w") as outfile:
        json.dump(output, outfile, indent=4)

    return


def convert(rc: dict, metadata_only: bool = False) -> dict:
    """
    Convert a RO-Crate to a DataCite object

    :param rc: The RO-Crate
    :param metadata_only: Whether it is a metadata-only DataCite
    :return: Dictionary containing DataCite metadata
    """

    rc = merge_authors_and_creators(rc)

    m = load_mapping_json()

    dc = setup_dc()
    if metadata_only:
        dc["files"]["enabled"] = False
    print(dc)

    try:
        root_rules = m["$root"]
    except KeyError:
        raise MappingException("Mapping does not contain a '$root' key.")

    for mapping_class in root_rules:
        print()

        # Ignore mappings that are marked as ignored
        if "_ignore" in root_rules.get(mapping_class).keys():
            print(f"|x Ignoring {mapping_class}")
            continue

        print(f"|- Applying rule collection {mapping_class}")

        root_mappings = root_rules.get(mapping_class)

        mappings = root_mappings.get("mappings")

        mapping_paths = get_mapping_paths(rc, mappings)

        print(f"\t\t|- Paths: {mapping_paths}")

        is_any_present = False

        for mapping_key in mappings:
            print(f"\t|- Applying mapping {mapping_key}")

            mapping = mappings.get(mapping_key)
            dc, any_present = apply_mapping(mapping, mapping_paths, rc, dc, mapping_key)
            is_any_present = is_any_present or any_present

        if not is_any_present:
            none_present_value = root_mappings.get("ifNonePresent")
            if none_present_value is not None:
                print(f"\t|- Applying ifNonePresent rule {none_present_value}")
                for none_present_key in none_present_value:
                    none_present_mapping_value = none_present_value.get(
                        none_present_key
                    )
                    dc = set_dc(dc, none_present_key, none_present_mapping_value)

    return dc


def get_mapping_paths(rc: dict, mappings: dict) -> dict:
    """Get the RO-Crate metadata paths relating to a set of mappings.
    A path is a location within the RO-Crate metadata where data relating to a
    particular mapping can be found. For example, the "creators_mapping" mapping looks
    for the "author" property on entities within the RO-Crate.

    :param rc: The RO-Crate metadata to find paths in
    :param mappings: A dictionary containing mapping classes
    :raises MappingException: Something is wrong with the loaded mapping
    :return: A dictionary with mapping classes as keys and relevant paths as values
    """

    # retrieve all array values
    all_from_values = []
    for key in mappings:
        mapping = mappings.get(key)
        if not isinstance(mapping, dict):
            raise MappingException(f"Mapping key {key} does not map to a dictionary.")
        from_value = mapping.get("from")
        if from_value is not None:
            all_from_values.append(from_value)

    array_values = get_arrays_from_from_values(all_from_values)

    # Extract all possible paths (used for arrays)
    mapping_paths = {}
    for i in array_values:
        mapping_paths[i] = get_paths(rc, i)

    return mapping_paths


def apply_mapping(mapping, mapping_paths, rc, dc, mapping_key):  # noqa: C901
    """Convert RO-Crate metadata to DataCite according to the specified mapping and
    paths.

    The following steps are performed for each defined mapping:
    1. Get the value from the RO-Crate (from)
    2. Check if the rule should be applied (onlyIf)
    3. Process the value (processing)
    4. Put the value into the correct format (value)
    5. Add the value to the DataCite object (to)


    :param mapping: Dictionary describing how to map a particular RO-Crate field to
        DataCite
    :param mapping_paths: A list of paths, used to disambiguate array values
    :param rc: Dictionary of RO-Crate metadata
    :param dc: Dictionary of DataCite metadata
    :param mapping_key: The key of the mapping being applied
    :return: tuple containing the updated dictionary of DataCite metadata, and a boolean
        indicating whether the rule was applied
    """
    rule_applied = False

    if "_ignore" in mapping.keys():
        return dc, rule_applied

    from_mapping_value = mapping.get("from")
    to_mapping_value = mapping.get("to")
    value_mapping_value = mapping.get("value")
    processing_mapping_value = mapping.get("processing")
    only_if_value = mapping.get("onlyIf")

    # Get the correct mapping paths. change this. now it is overriden
    paths = [[]]

    if from_mapping_value:
        delimiter_index = from_mapping_value.rfind("[]")
    else:
        delimiter_index = -1

    if delimiter_index != -1:
        processed_string = from_mapping_value[: delimiter_index + 2]
        paths = mapping_paths.get(processed_string)
        print(f"\t\t|- Paths: {paths}")

    for i, path in enumerate(paths):
        if mapping_key.startswith("publisher_mapping") and i > 0:
            # RO-Crate can have a list of publishers, but DataCite only supports one
            # publisher. So, we only apply the first one.
            print(
                f"\t\t|- Skipping path {i} for mapping {mapping_key} to avoid "
                "overwriting previous values."
            )
            continue
        new_path = path.copy()
        from_value = get_value_from_rc(rc.copy(), from_mapping_value, new_path)

        if from_value and isinstance(from_value, dict):
            # If the value is a JSON object, then we ignore the rule (since another rule
            # must be implemented on how to handle it)
            print(
                "\t\t|- Result is a JSON object, so this rule cannot be applied. "
                "Skipping to next path."
            )
            from_value = None

        if from_value is None:
            continue

        if only_if_value is not None:
            print(f"\t\t|- Checking condition {only_if_value}")
            if not check_condition(only_if_value, from_value):
                return dc, rule_applied

        if processing_mapping_value:
            from_value = process(processing_mapping_value, from_value)

        if value_mapping_value:
            from_value = transform_to_target_format(value_mapping_value, from_value)

        if from_value is not None:
            print(
                f"\t\t|- Adding {from_value} to {to_mapping_value} with path "
                f"{path.copy()}"
            )
            rule_applied = True
            dc = set_dc(dc, to_mapping_value, from_value, path.copy())
            print(dc)

    return dc, rule_applied


def get_paths(rc: dict, key: str) -> list[list]:
    """
    Get all possible paths for a given key

    :param rc: The RO-Crate
    :param key: The key to get the paths for
    :return: A list of lists, where each list represents a path
    """
    print(f"\t\t|- Getting paths for {key}")
    keys = key.split(".")
    temp = rc_get_rde(rc)
    paths: list[list] = []
    get_paths_recursive(rc, temp, keys, paths, [])
    print(f"\t\t\t|- Found paths {paths}")
    return paths


def get_paths_recursive(
    rc: dict,
    entity_or_dict: dict | str | int | float | None,
    keys: list[str],
    paths: list,
    path: list,
):
    """Recursively find paths within an RO-Crate for a list of keys.

    :param rc: Dictionary containing the RO-Crate metadata to find paths in
    :param entity_or_dict: The RO-Crate entity or regular dictionary which contains the
        first key in the list. If a non-dict is provided, returns None.
    :param keys: A list of keys. Each key should represent a dict or reference to an
        entity which contains the next key in the list, except the final key which may
        represent anything. e.g. ["$author[]", "name"]
    :param paths: Current list of known paths (modified in place)
    :param path: List of components of the current path, e.g. ["author",1,"name"]
    """

    # end of the recursive chain
    if len(keys) == 0:
        paths.append(path)
        return

    current_key = keys[0]

    # clean key and check it is in the current entity
    cleaned_key = clean_key(current_key)
    if (
        entity_or_dict is None
        or not isinstance(entity_or_dict, dict)
        or cleaned_key not in entity_or_dict.keys()
    ):
        return

    # if the key indicates that it may be an array, get paths for every element in the
    # array
    if current_key.endswith("[]"):
        new_current_key = current_key
        if current_key.startswith("$"):
            new_current_key = current_key[1:]
        value = entity_or_dict[new_current_key[:-2]]
        # if value for this key is a list, get paths recursively for each item
        if isinstance(value, list):
            for i in range(len(value)):
                new_path = path.copy()
                new_path.append(i)

                new_temp = dereference(rc, entity_or_dict, current_key[:-2], i)

                # find paths within the next entity/dict using subsequent keys in the
                # list
                get_paths_recursive(rc, new_temp, keys[1:], paths, new_path)

        # value is not a list
        else:
            new_path = path.copy()
            new_path.append(-1)  # indicate we are not navigating a list
            new_temp = dereference(rc, entity_or_dict, current_key[:-2])

            # find parts within the next entity/dict using subsequent keys in the list
            get_paths_recursive(rc, new_temp, keys[1:], paths, new_path)

    # key is not for an array
    else:
        entity_or_dict = dereference(rc, entity_or_dict, current_key)

        # find parts within the next entity/dict using subsequent keys in the list
        get_paths_recursive(rc, entity_or_dict, keys[1:], paths, path)

    return


def transform_to_target_format(format, value):
    """
    Transforms the given value to the given format.
    The format parameter is a string, which can contain the following special values:
        - @@this: The value of the key itself

    :param format: The format to apply to the value.
    :param value: The value to format.
    :return: The formatted value.
    """
    if format is not None:
        if value:
            print(f"\t\t|- Formatting value {value} according to {format}.")
            format = format_value(format, value)
            return format
        elif value is None and contains_atatthis(format):
            format = None
            return format
        print(f"\t\t|- Formatted value {value} is {format}")
    return format


def set_dc(dictionary, key, value=None, path=[]):
    """
    Sets the value of the given key in the given dictionary to the given value.
    If the key does not exist, it is created.
    If the key ends with "[]", the value is appended to the list of values for the key.

    :param dictionary: The dictionary to set the value in.
    :param key: The key to set the value for.
    :param value: The value to set.
    :param path: The path to the key.
    """
    keys = key.split(".")
    current_dict = dictionary
    index = -1
    for key_part in keys:
        print(f"\t\t\t|- Key part: {key_part}")
        if len(path) > 0:
            index = path[0]
        else:
            index = 0
        if key_part.endswith("[]") and not key_part[:-2] in current_dict:
            path = path[1:]
            current_dict[key_part[:-2]] = [{}]
            last_val = current_dict[key_part[:-2]]
            current_dict = current_dict[key_part[:-2]][
                0
            ]  # index is 0 here (if we assume that paths is in ascending order)

        elif key_part.endswith("[]") and key_part[:-2] in current_dict:
            path = path[1:]
            last_val = current_dict[key_part[:-2]]

            while len(current_dict[key_part[:-2]]) <= index:
                current_dict[key_part[:-2]].append(
                    {}
                )  # It expands 1 by 1 anyway, since no empty paths can remain after
                # a mapping rule is applied

            current_dict = current_dict[key_part[:-2]][index]

        elif key_part not in current_dict and not key_part.endswith("[]"):
            last_val = current_dict
            current_dict[key_part] = {}
            current_dict = current_dict[key_part]

        else:
            last_val = current_dict
            current_dict = current_dict[key_part]

    last_key = keys[-1]
    if last_key.endswith("[]"):
        last_val[index] = value
    else:
        last_val[last_key] = value
    return dictionary


def check_condition(condition_rule, value):
    """
    Checks if a value matches a condition rule.
    The condition rule is a string that starts with ? and is followed by the name of the
    function to apply.
    The function must be defined in condition_functions.py.

    :param condition_rule: The condition rule to apply.
    :param value: The value to check.
    :return: True if the value matches the condition, False otherwise.
    """
    if not condition_rule.startswith("?"):
        raise ValueError(f"Condition rule {condition_rule} must start with ?")
    try:
        function = getattr(cf, condition_rule[1:])
    except AttributeError:
        raise NotImplementedError(f"Function {condition_rule} not implemented.")
    return function(value)


def process(process_rule, value):
    """
    Processes a value according to a processing rule.
    The processing rule is a string that starts with $ and is followed by the name of
    the function to apply.
    The function must be defined in processing_functions.py.

    :param process_rule: The processing rule to apply.
    :param value: The value to process.
    :return: The processed value.
    """
    if not process_rule.startswith("$"):
        raise ValueError(f"Processing rule {process_rule} must start with $")
    try:
        function = getattr(pf, process_rule[1:])
    except AttributeError:
        raise NotImplementedError(f"Function {process_rule} not implemented.")
    return function(value)


def merge_authors_and_creators(rc: dict):
    """
    Copy creators to authors in the RO-Crate, so they can be processed in a single
    mapping. Mapping from 'author' to 'creators' and later from 'creator' to
    'creators' causes overwritings.
    """

    for rde in rc["@graph"]:
        if "creator" in rde:
            for person_or_org in rde["creator"]:
                if isinstance(person_or_org, str):
                    added_authors = [item for item in rde["author"]]
                    if person_or_org not in added_authors:
                        rde["author"].append(person_or_org)
                    continue
                urls_orcid = [
                    item["@id"]
                    for item in rde["author"]
                    if isinstance(item, dict) and "@id" in item
                ]
                if person_or_org["@id"] not in urls_orcid:
                    rde["author"].append(person_or_org)

    return rc


if __name__ == "__main__":
    main()
