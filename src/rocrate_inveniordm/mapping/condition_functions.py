import re


def is_uri(value):
    """Checks if a string is a URI."""
    return value and value.startswith("http")


def is_not_uri(value):
    """Checks if a string is not empty and not a URI."""
    return value and not is_uri(value)


def geonames(value):
    return True


def doi(value):
    """
    Checks if the value is a doi url
    """
    doi_start_pattern = r"https?:\/\/(dx.)?doi.org"
    if not value:
        return False
    return re.match(doi_start_pattern, value) is not None


def orcid(value):
    return value and value.startswith("https://orcid.org/")


def embargoed(value):
    """
    Checks if the value is a date in the future.
    """
    from datetime import datetime

    from dateutil.parser import parse

    if not value:
        return False

    fuzzy_date = parse(value, fuzzy=True)
    now = datetime.now()
    if now.timestamp() < fuzzy_date.timestamp():
        return True
    return False


def string(value):
    return value and isinstance(value, str)


def ror(value):
    return value and value.startswith("https://ror.org/")
