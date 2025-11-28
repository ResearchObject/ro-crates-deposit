import rocrate_inveniordm.mapping.processing_functions as pf


def test_dateProcessing__date_only():
    out = pf.dateProcessing("5 June 2012")

    assert out == "2012-06-05"


def test_dateProcessing__timestamp():
    out = pf.dateProcessing("5 June 2012 09:30:44")

    assert out == "2012-06-05"


def test_dateProcessing__year_only():
    out = pf.dateProcessing("2012")

    assert out == "2012"


def test_dateProcessing__empty():
    out = pf.dateProcessing("")

    assert out is None


def test_dateProcessing__none():
    out = pf.dateProcessing(None)

    assert out is None


def test_typeProcessing_single():
    out = pf.typeProcessing("Dataset")

    assert out == "dataset"


def test_typeProcessing_wf():
    out = pf.typeProcessing(["File", "SoftwareSourceCode", "ComputationalWorkflow"])

    assert out == "workflow"


def test_typeProcessing_not_wf():
    out = pf.typeProcessing(["File", "ImageObject", "WorkflowSketch"])

    assert out == "dataset"


def test_nameProcessing():
    out = pf.nameProcessing("John Michael Smith")

    assert out["family_name"] == "Smith"
    assert out["given_name"] == "John Michael"
    assert out["name"] == "John Michael Smith"


def test_rightsProcessing_spdx():
    out = pf.rightsProcessing("https://spdx.org/licenses/CC-BY-NC-ND-4.0.html")

    assert "title" not in out
    assert out["id"] == "cc-by-nc-nd-4.0"
    assert out["scheme"] == "spdx"
    assert out["link"] == "https://spdx.org/licenses/CC-BY-NC-ND-4.0.html"


def test_rightsProcessing_non_spdx():
    out = pf.rightsProcessing("https://licensewebsite.org/licenses/1.0/")

    assert not "id" in out
    assert out["title"] == {"en": "https://licensewebsite.org/licenses/1.0/"}
    assert out["link"] == "https://licensewebsite.org/licenses/1.0/"
