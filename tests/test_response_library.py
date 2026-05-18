from pathlib import Path

import pytest

from runtime.state.response_library import ResponseClip, ResponseLibrary


def test_selects_clip_by_label_and_style():
    clips = [
        ResponseClip(
            id="billing-calm",
            label="billing",
            file_path=Path("audio/billing-calm.wav"),
            style="calm",
            duration_ms=1200,
            tags=("billing", "prebuilt"),
        ),
        ResponseClip(
            id="billing-friendly",
            label="billing",
            file_path=Path("audio/billing-friendly.wav"),
            style="friendly",
            duration_ms=1100,
            tags=("billing", "prebuilt"),
        ),
    ]

    library = ResponseLibrary(clips=clips)

    selected = library.pick("billing", style="friendly")

    assert selected is clips[1]


def test_selects_lowest_id_when_multiple_clips_match():
    clips = [
        ResponseClip(
            id="billing-z",
            label="billing",
            file_path=Path("audio/billing-z.wav"),
            style="friendly",
            duration_ms=1100,
            tags=("billing", "prebuilt"),
        ),
        ResponseClip(
            id="billing-a",
            label="billing",
            file_path=Path("audio/billing-a.wav"),
            style="friendly",
            duration_ms=1050,
            tags=("billing", "prebuilt"),
        ),
    ]

    library = ResponseLibrary(clips=clips)

    selected = library.pick("billing", style="friendly")

    assert selected is clips[1]


def test_missing_label_raises_lookup_error():
    library = ResponseLibrary(
        clips=[
            ResponseClip(
                id="billing-friendly",
                label="billing",
                file_path=Path("audio/billing-friendly.wav"),
                style="friendly",
                duration_ms=1100,
                tags=("billing", "prebuilt"),
            )
        ]
    )

    with pytest.raises(LookupError):
        library.pick("support")


def test_style_mismatch_raises_lookup_error():
    library = ResponseLibrary(
        clips=[
            ResponseClip(
                id="billing-friendly",
                label="billing",
                file_path=Path("audio/billing-friendly.wav"),
                style="friendly",
                duration_ms=1100,
                tags=("billing", "prebuilt"),
            )
        ]
    )

    with pytest.raises(LookupError):
        library.pick("billing", style="calm")