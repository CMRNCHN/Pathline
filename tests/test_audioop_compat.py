from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest

from runtime.media import audio_pipeline


def test_load_audioop_prefers_stdlib_on_python_312(monkeypatch: pytest.MonkeyPatch) -> None:
    stdlib_audioop = SimpleNamespace(name="audioop")
    monkeypatch.setattr(audio_pipeline.sys, "version_info", (3, 12, 0))

    def fake_import_module(name: str):
        if name == "audioop":
            return stdlib_audioop
        raise AssertionError(f"unexpected import: {name}")

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    loaded = audio_pipeline._load_audioop()

    assert loaded is stdlib_audioop


def test_load_audioop_uses_audioop_module_on_python_313(monkeypatch: pytest.MonkeyPatch) -> None:
    compat_audioop = SimpleNamespace(name="audioop")
    monkeypatch.setattr(audio_pipeline.sys, "version_info", (3, 13, 0))

    def fake_import_module(name: str):
        if name == "audioop":
            return compat_audioop
        raise AssertionError(f"unexpected import: {name}")

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    loaded = audio_pipeline._load_audioop()

    assert loaded is compat_audioop


def test_load_audioop_raises_clear_error_when_unavailable_on_python_313(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(audio_pipeline.sys, "version_info", (3, 13, 0))

    def fake_import_module(name: str):
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    with pytest.raises(ModuleNotFoundError, match="audioop-lts"):
        audio_pipeline._load_audioop()


def test_load_audioop_raises_clear_error_when_unavailable_on_python_312(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(audio_pipeline.sys, "version_info", (3, 12, 0))

    def fake_import_module(name: str):
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    with pytest.raises(ModuleNotFoundError, match="audioop-lts"):
        audio_pipeline._load_audioop()
