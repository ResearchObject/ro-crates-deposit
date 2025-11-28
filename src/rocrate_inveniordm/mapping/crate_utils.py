from __future__ import annotations

from rocrate_inveniordm.mapping.mapping_utils import clean_key, MappingException


def dereference(
    rc: dict, entity_or_dict: dict, key: str, index: int | None = None
) -> dict | str | int | float | None:
    """Returns the desired value or array element, finding the referenced entity in the
    RO-Crate if appropriate.

    :param rc:  Dictionary of RO-Crate metadata
    :param entity_or_dict: The RO-Crate entity or regular dictionary which contains the
        key
    :param key: The key to dereference. It may start with $ but should not contain [].
    :param index: The index of the desired array element, if applicable. Defaults to
        None.
    :return: A dictionary with the dereferenced entity
    """
    # if the key expects references to other entities,
    # find the referenced entity
    if key.startswith("$"):
        return get_referenced_entity(rc, entity_or_dict, key, index)
    # otherwise, use the raw value
    elif index and index != -1:
        return entity_or_dict[key][index]
    else:
        return entity_or_dict[key]


def rc_get_rde(rc):
    """
    Retrieves the Root Date Entity from the given RO-Crate.

    :param rc: The RO-Crate to retrieve the RDE from.
    :return: The Root Data Entity of the given RO-Crate.
    """

    # Following the RO-Crate specification
    # (https://www.researchobject.org/ro-crate/specification/1.2-DRAFT/root-data-entity.html#finding-the-root-data-entity),
    # use the following algorithm to find the RDE:
    #
    # For each entity in @graph array
    # .. if the @id is ro-crate-metadata.json
    # …. from this entity’s about object, keep the @id URI as variable root
    # .. if the @id is ro-crate-metadata.jsonld
    # …. from this entity’s about object, keep the @id URI as variable legacyroot
    # For each entity in @graph array
    # .. if the entity has an @id URI that matches a non-null root return it
    # For each entity in @graph array
    # .. if the entity has an @id URI that matches a non-null legacyroot return it
    # Fail with unknown root data entity.

    # Build a map of all entities using their @id as keys
    entity_map = {e["@id"]: e for e in rc["@graph"]}

    # First, try to find the root from ro-crate-metadata.json
    metadata_entity = entity_map.get("ro-crate-metadata.json")
    root = None
    if metadata_entity and "about" in metadata_entity:
        root = metadata_entity["about"]["@id"]

    # If root not found, try to find legacy root from ro-crate-metadata.jsonld
    if not root:
        legacy_metadata_entity = entity_map.get("ro-crate-metadata.jsonld")
        if legacy_metadata_entity and "about" in legacy_metadata_entity:
            root = legacy_metadata_entity["about"]["@id"]

    # Look up the root entity using the found @id
    if root and root in entity_map:
        return entity_map[root]

    # Fail if root entity cannot be found
    raise ValueError("Unknown root data entity")


def get_value_from_rc(rc, from_key, path=[]):
    """
    Retrieves the value of the given key from the given RO-Crate.
    A key consists of multiple subkeys, separated by a dot (.).
    If a subkey starts with a $, then it is a reference to another key.

    :param rc: The RO-Crate to retrieve the value from.
    :param from_key: The key to retrieve the value from.
    :param path: The path to the value, used to disambiguate arrays.
    :return: The value of the given key in the given RO-Crate.
    """
    result = None

    if not from_key:
        return None

    print(f"\t\t|- Retrieving value {from_key} with path {path} from RO-Crate.")
    keys = from_key.split(".")
    # print(keys)
    current_entity = rc_get_rde(rc)

    for key in keys:
        cleaned_key = clean_key(key)
        print(f"\t\t|- Cleaned key: {cleaned_key}")
        if key.startswith("$"):
            # we need to dereference the key
            index = None
            if key.endswith("[]"):
                index = path[0]
                path = path[1:]
                current_entity = get_referenced_entity(
                    rc, current_entity, "$" + cleaned_key, index
                )
            else:
                current_entity = get_referenced_entity(
                    rc, current_entity, "$" + cleaned_key
                )

            if current_entity is None:
                return None

        elif cleaned_key not in current_entity.keys():
            # The key could not be found in the RO-Crate
            return None

        else:
            if key.endswith("[]"):
                index = path[0]
                path = path[1:]
                if index == -1:
                    current_entity = current_entity.get(cleaned_key)
                else:
                    current_entity = current_entity.get(cleaned_key)[index]
            else:
                current_entity = current_entity.get(cleaned_key)

    result = current_entity

    print(f"\t\t|- Value for key {from_key} is {result}")

    return result


def get_referenced_entity(
    rc: dict, parent: dict, from_key: str, index: int | None = None
) -> dict | None:
    """
    Retrieves the entity referenced by the given $-prefixed key from the given RO-Crate.

    Example: Calling get_rc_ref(rc, parent, "$affiliation") on the following RO-Crate

    rc: {
        ...
        {
            "@id": "https://orcid.org/0000-0002-8367-6908",
            "@type": "Person",
            "name": "J. Xuan"
            "affiliation": {"@id": "https:/abc"}
        }
        {
            "@id": "https:/abc",
            "@type": "Organization",
            "name": "ABC University"
        }
    }

    parent: {
            "@id": "https://orcid.org/0000-0002-8367-6908",
            "@type": "Person",
            "name": "J. Xuan"
            "affiliation": {"@id": "https:/abc"}
        }

    returns {
            "@id": "https:/abc",
            "@type": "Organization",
            "name": "ABC University"
        }
    """
    print(f"\t\t|- Retrieving referenced entity {from_key} from RO-Crate.")

    if from_key and not from_key.startswith("$"):
        raise MappingException(f"$-prefixed key expected, but {from_key} found.")

    id_val = parent.get(from_key[1:])
    if isinstance(id_val, list):
        if index is None or index == -1:
            raise ValueError(
                f"Value of {from_key} is a list, but no index was provided."
            )
        id_val = id_val[index]
    elif index is not None and index != -1:
        raise ValueError(
            f"Value of {from_key} is not a list, but an index was provided."
        )

    if isinstance(id_val, dict):
        id = id_val.get("@id")
        print(f"\t\t\t|- Id is {id}")
    else:
        return None

    # find matching entity in crate
    all_entities = rc.get("@graph", [])
    assert isinstance(all_entities, list)

    for entity in all_entities:
        assert isinstance(entity, dict)
        if entity.get("@id") == id:
            print(f"\t\t\t|- Found entity {entity}")
            return entity

    return None


def get_referenced_entity_from_root(rc, from_key):
    """
    Retrieves the entity referenced by the given $-prefixed key from the given RO-Crate.

    :param rc: The RO-Crate to retrieve the referenced entity from.
    :param from_key: The $-prefixed key to retrieve the referenced entity from.
    :return: The referenced entity of the given RO-Crate.
    """
    print(f"\t\t|- Retrieving referenced entity {from_key} from RO-Crate.")
    if from_key and not from_key.startswith("$"):
        raise MappingException(f"$-prefixed key expected, but {from_key} found.")

    keys = from_key.split(".")
    root = rc_get_rde(rc)
    if root.get(keys[0][1:]) is None:
        print(
            f"\t\t|- Key {keys[0]} not found in RO-Crate Root Data Entity "
            f'({root["@id"]}).'
        )
        return None
    target_entity_id = root.get(keys[0][1:]).get("@id")
    target_entity = None

    for entity in rc.get("@graph"):
        if entity.get("@id") == target_entity_id:
            target_entity = entity
            break
    return target_entity
