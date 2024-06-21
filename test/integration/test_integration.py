import json
import os
import pytest
import pathlib
import re
import requests
import shutil
import subprocess

from test.unit.utils import get_request_headers, fetch_inveniordm_record

CRATES = ["minimal-ro-crate", "test-ro-crate", "real-world-example"]
TEST_DATA_FOLDER = "test/data"
TEST_OUTPUT_FOLDER = "test/output"


@pytest.mark.parametrize("crate_name", [*CRATES])
def test_created_datacite_files(crate_name):
    # Arrange
    crate_path = os.path.join(TEST_DATA_FOLDER, crate_name)
    compare_path = os.path.join(TEST_DATA_FOLDER, f"datacite-out-{crate_name}.json")
    with open(compare_path) as expected:
        expected_json = json.load(expected)
    output_file = "datacite-out.json"

    # Act
    # note - check_output raises CalledProcessError if exit code is non-zero
    # --no-upload prevents upload and generates DataCite files only
    log = subprocess.check_output(
        f"python deposit.py {crate_path} --no-upload", shell=True, text=True
    )
    # preserve data files and log in TEST_OUTPUT_FOLDER
    shutil.copyfile(
        output_file, os.path.join(TEST_OUTPUT_FOLDER, f"datacite-out-{crate_name}.json")
    )
    with open(
        os.path.join(TEST_OUTPUT_FOLDER, f"log-datacite-{crate_name}.txt"),
        "w",
    ) as log_file:
        log_file.write(log)

    # Assert
    assert "Created datacite-out.json, skipping upload" in log
    assert os.path.exists(output_file)
    with open(output_file) as output:
        output_json = json.load(output)
        assert output_json == expected_json


@pytest.mark.parametrize("crate_name", [*CRATES])
def test_created_invenio_records(crate_name):
    # Arrange
    crate_path = os.path.join(TEST_DATA_FOLDER, crate_name)
    compare_path = os.path.join(TEST_DATA_FOLDER, f"datacite-out-{crate_name}.json")
    with open(compare_path) as expected:
        expected_json = json.load(expected)
        expected_metadata = expected_json["metadata"]
    expected_log_pattern = r"^Successfully created record (?P<id>[0-9]*)$"

    # Act
    # note - check_output raises CalledProcessError if exit code is non-zero
    log = subprocess.check_output(
        f"python deposit.py {crate_path}", shell=True, text=True
    )
    with open(
        os.path.join(TEST_OUTPUT_FOLDER, f"log-upload-{crate_name}.txt"),
        "w",
    ) as log_file:
        log_file.write(log)
    match = re.search(expected_log_pattern, log, flags=re.MULTILINE)
    record_id = match.group("id")

    headers = get_request_headers()
    record = fetch_inveniordm_record(record_id)
    metadata = record["metadata"]

    # Assert
    assert metadata["title"] == expected_metadata["title"]
    assert metadata["upload_type"] == expected_metadata["resource_type"]["id"]
    assert metadata["access_right"] == "open"
    assert len(metadata["creators"]) == len(expected_metadata["creators"])
    if "contributors" in expected_metadata:
        assert len(metadata["contributors"]) == len(expected_metadata["contributors"])
    else:
        assert "contributors" not in metadata

    if expected_json["files"]["enabled"]:
        assert len(record["files"]) != 0
        for file in record["files"]:
            filename = file["filename"]
            local_path = next(
                pathlib.Path(os.path.join(TEST_DATA_FOLDER, crate_name)).glob(
                    f"**/{filename}"
                )
            )
            with open(local_path) as local_file:
                remote_file_data = requests.get(
                    file["links"]["download"], headers=headers
                ).content
                assert local_file.read() == remote_file_data.decode()
    else:
        assert len(record["files"]) == 0
    assert record["state"] == "unsubmitted"
    assert record["submitted"] is False


def test_created_invenio_record_from_datacite():
    """Test creating a record from a pre-existing DataCite file."""
    # Arrange
    crate_name = "test-ro-crate"
    crate_path = os.path.join(TEST_DATA_FOLDER, crate_name)
    compare_path = os.path.join(TEST_DATA_FOLDER, f"datacite-out-{crate_name}.json")
    with open(compare_path) as expected:
        expected_json = json.load(expected)
        expected_metadata = expected_json["metadata"]
    expected_log_pattern_1 = "Skipping metadata conversion, loading DataCite file"
    expected_log_pattern_2 = r"^Successfully created record (?P<id>[0-9]*)$"

    # Act
    # note - check_output raises CalledProcessError if exit code is non-zero
    log = subprocess.check_output(
        f"python deposit.py {crate_path} -d {compare_path}", shell=True, text=True
    )
    match = re.search(expected_log_pattern_2, log, flags=re.MULTILINE)
    record_id = match.group("id")

    record = fetch_inveniordm_record(record_id)
    metadata = record["metadata"]

    # Assert
    assert expected_log_pattern_1 in log
    # check one piece of metadata to confirm it was uploaded
    assert metadata["title"] == expected_metadata["title"]
    # check submission state
    assert record["state"] == "unsubmitted"
    assert record["submitted"] is False
