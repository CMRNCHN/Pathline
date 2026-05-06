import pytest

from ivr_assessor.live_map_gui import _normalize_suite_filename


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("billing_suite", "billing_suite.json"),
        ("billing-suite.json", "billing-suite.json"),
        ("suite.v1", "suite.v1.json"),
        ("suite_01.JSON", "suite_01.JSON.json"),
        ("  nightly_suite  ", "nightly_suite.json"),
    ],
)
def test_normalize_suite_filename_accepts_safe_names(raw: str, expected: str) -> None:
    assert _normalize_suite_filename(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "   ",
        "../escape",
        "..\\escape",
        "nested/path",
        "nested\\path",
        ".json",
        "suite name",
        "suite$",
    ],
)
def test_normalize_suite_filename_rejects_unsafe_names(raw: object) -> None:
    with pytest.raises(ValueError):
        _normalize_suite_filename(raw)
