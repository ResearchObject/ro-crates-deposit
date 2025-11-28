from test.unit.utils import (
    add_entity_to_template,
    get_single_mapping,
    load_template_rc,
    set_field_in_template_rde,
)

import pytest

from rocrate_inveniordm.mapping.converter import (
    apply_mapping,
    get_mapping_paths,
    setup_dc,
)

publisher_string = "Test University"
publisher_entity = {
    "@id": "https://ror.org/0abcdef00",
    "@type": "Organization",
    "name": "Example University",
    "url": "https://www.example.org",
}


@pytest.fixture(scope="module", autouse=True)
def rc():
    """Creates template RO-Crate metadata."""
    return load_template_rc()


@pytest.fixture(scope="module", autouse=True)
def dc():
    """Creates template DataCite metadata."""
    return setup_dc()


def test_publisher_string(rc, dc):
    # Arrange
    rc, _ = set_field_in_template_rde("publisher", publisher_string, rc)
    rule_name = "publisher_mapping_direct"
    rule = get_single_mapping("publisher", rule_name)
    paths = get_mapping_paths(rc, {rule_name: rule})

    # Act
    dc, _ = apply_mapping(rule, paths, rc, dc, rule_name)

    # Assert
    assert dc["metadata"]["publisher"] == publisher_string


def test_publisher_entity(rc, dc):
    # Arrange
    rc = add_entity_to_template(publisher_entity, rc)
    rc, _ = set_field_in_template_rde("publisher", {"@id": publisher_entity["@id"]}, rc)
    rule_name = "publisher_mapping_name"
    rule = get_single_mapping("publisher", rule_name)
    paths = get_mapping_paths(rc, {rule_name: rule})

    # Act
    dc, _ = apply_mapping(rule, paths, rc, dc, rule_name)

    # Assert
    assert dc["metadata"]["publisher"] == publisher_entity["name"]
