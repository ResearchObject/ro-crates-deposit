from datetime import datetime, timedelta

import pytest
import pytz

import rocrate_inveniordm.mapping.condition_functions as cf


def test_is_uri__true():
    input = "https://example.org"

    assert cf.is_uri(input)


def test_is_uri__false():
    input = "example.org"

    assert not cf.is_uri(input)


def test_is_uri__empty():
    input = ""

    assert not cf.is_uri(input)


def test_is_uri__none():
    input = None

    assert not cf.is_uri(input)


def test_is_not_uri__true():
    input = "example.org"

    assert cf.is_not_uri(input)


def test_is_not_uri__false():
    input = "http://example.org"

    assert not cf.is_not_uri(input)


def test_is_not_uri__empty():
    input = ""

    assert not cf.is_not_uri(input)


def test_is_not_uri__none():
    input = None

    assert not cf.is_not_uri(input)


@pytest.mark.skip(reason="condition not implemented")
def test_geonames():
    input = ""

    assert cf.geonames(input)


@pytest.mark.parametrize(
    "input",
    [
        "https://doi.org/xxxxx",
        "http://doi.org/xxxxx",
        "https://dx.doi.org/xxxxx",
        "http://dx.doi.org/xxxxx",
    ],
)
def test_doi__true(input):
    assert cf.doi(input)


def test_doi__false():
    input = "abcde"
    assert not cf.doi(input)


def test_doi__empty():
    input = ""
    assert not cf.doi(input)


def test_doi__none():
    input = None
    assert not cf.doi(input)


def test_orcid__true():
    input = "https://orcid.org/0000-0000-0000-0000"
    assert cf.orcid(input)


def test_orcid__false():
    input = "0000-0000-0000-0000"
    assert not cf.orcid(input)


def test_orcid__empty():
    input = ""
    assert not cf.orcid(input)


def test_orcid__none():
    input = None
    assert not cf.orcid(input)


def test_embargoed__true():
    future_date = datetime.now() + timedelta(weeks=1)
    input = future_date.strftime("%Y-%m-%d")

    assert cf.embargoed(input)


def test_embargoed__false():
    past_date = datetime.now() - timedelta(weeks=1)
    input = past_date.strftime("%Y-%m-%d")

    assert not cf.embargoed(input)


def test_embargoed__today():
    today = datetime.now(tz=pytz.utc)
    input = today.strftime("%Y-%m-%d")

    assert not cf.embargoed(input)


def test_embargoed__today_timestamped():
    today = datetime.now(tz=pytz.utc)
    input = today.strftime("%Y-%m-%dT%H:%M:%S%z")

    assert not cf.embargoed(input)


def test_embargoed__empty():
    input = ""

    assert not cf.embargoed(input)


def test_embargoed__none():
    input = None

    assert not cf.embargoed(input)


def test_string__true():
    input = "this is a string"

    assert cf.string(input)


@pytest.mark.parametrize("input", [3, ["test"], {"test": "test"}])
def test_string__false(input):
    assert not cf.string(input)


def test_string__empty():
    input = ""

    assert not cf.string(input)


def test_string__none():
    input = None

    assert not cf.string(input)


def test_ror__true():
    input = "https://ror.org/05sd8tv96"
    assert cf.ror(input)


def test_ror__false():
    input = "05sd8tv96"
    assert not cf.ror(input)


def test_ror__empty():
    input = ""
    assert not cf.ror(input)


def test_ror__none():
    input = None
    assert not cf.ror(input)
