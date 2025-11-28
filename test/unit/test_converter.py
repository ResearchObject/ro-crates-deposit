import json
import re

import pytest

import rocrate_inveniordm.mapping.converter as converter


def test_check_condition__true():
    rule = "?string"
    value = "This is a string"

    result = converter.check_condition(rule, value)

    assert result


def test_check_condition__false():
    rule = "?string"
    value = 3

    result = converter.check_condition(rule, value)

    assert not result


def test_check_condition__incorrect_format():
    rule = "string"
    value = "This is a string"

    with pytest.raises(
        ValueError, match=re.escape(f"Condition rule {rule} must start with ?")
    ):
        converter.check_condition(rule, value)


def test_check_condition__nonexistent():
    rule = "?random"
    value = "This is a string"

    with pytest.raises(
        NotImplementedError, match=re.escape(f"Function {rule} not implemented.")
    ):
        converter.check_condition(rule, value)


def test_process__valid():
    rule = "$dateProcessing"
    value = "18 June 2024"

    result = converter.process(rule, value)

    assert result == "2024-06-18"


def test_process__empty():
    rule = "$dateProcessing"
    value = ""

    result = converter.process(rule, value)

    assert result is None


def test_process__incorrect_format():
    rule = "dateProcessing"
    value = "18 June 2024"

    with pytest.raises(
        ValueError, match=re.escape(f"Processing rule {rule} must start with $")
    ):
        converter.process(rule, value)


def test_process__nonexistent():
    rule = "$date"
    value = "18 June 2024"

    with pytest.raises(
        NotImplementedError, match=re.escape(f"Function {rule} not implemented.")
    ):
        converter.process(rule, value)


def test_adds_string_creator():
    rc = {"@graph": [{"author": ["Alice"], "creator": ["Bob"]}]}
    result = converter.merge_authors_and_creators(rc)
    assert "Bob" in result["@graph"][0]["author"]
    assert len(result["@graph"][0]["author"]) == 2


def test_skips_existing_string_creator():
    rc = {"@graph": [{"author": ["Bob"], "creator": ["Bob"]}]}
    result = converter.merge_authors_and_creators(rc)
    # Should not duplicate
    assert result["@graph"][0]["author"].count("Bob") == 1
    assert len(result["@graph"][0]["author"]) == 1


def test_adds_dict_creator_with_id():
    rc = {
        "@graph": [
            {
                "author": [
                    {"@id": "https://orcid.org/0000-0000-0000-0001", "name": "Alice"}
                ],
                "creator": [
                    {"@id": "https://orcid.org/0000-0000-0000-0002", "name": "Bob"}
                ],
            }
        ]
    }
    result = converter.merge_authors_and_creators(rc)
    ids = [a["@id"] for a in result["@graph"][0]["author"] if isinstance(a, dict)]
    assert "https://orcid.org/0000-0000-0000-0002" in ids
    assert len(ids) == 2


def test_skips_existing_dict_creator_by_id():
    rc = {
        "@graph": [
            {
                "author": [
                    {"@id": "https://orcid.org/0000-0000-0000-0002", "name": "Bob"}
                ],
                "creator": [
                    {"@id": "https://orcid.org/0000-0000-0000-0002", "name": "Bob"}
                ],
            }
        ]
    }
    result = converter.merge_authors_and_creators(rc)
    ids = [a["@id"] for a in result["@graph"][0]["author"] if isinstance(a, dict)]
    # Should not duplicate
    assert ids.count("https://orcid.org/0000-0000-0000-0002") == 1
    assert len(result["@graph"][0]["author"]) == 1


def test_mixed_string_and_dict_creators():
    rc = {
        "@graph": [
            {
                "author": [
                    "Alice",
                    {"@id": "https://orcid.org/0000-0000-0000-0001", "name": "A"},
                ],
                "creator": [
                    "Charlie",
                    {"@id": "https://orcid.org/0000-0000-0000-0002", "name": "C"},
                ],
            }
        ]
    }
    result = converter.merge_authors_and_creators(rc)
    # String and dict added
    assert "Alice" in result["@graph"][0]["author"]
    assert "Charlie" in result["@graph"][0]["author"]
    ids = [a["@id"] for a in result["@graph"][0]["author"] if isinstance(a, dict)]
    assert "https://orcid.org/0000-0000-0000-0001" in ids
    assert "https://orcid.org/0000-0000-0000-0002" in ids
    assert len(result["@graph"][0]["author"]) == 4
