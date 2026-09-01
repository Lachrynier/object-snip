from pathlib import Path

import pytest

from objectsnip.__main__ import (
    DEFAULT_DEBUG_CAPTURE_DIRECTORY,
    DEFAULT_SAM2_CHECKPOINT,
    ensure_selected_model,
    parse_arguments,
)
from objectsnip.segmentation.models import SAM2_MODELS


def test_debug_captures_is_disabled_by_default() -> None:
    assert parse_arguments([]).debug_captures is None


def test_debug_captures_uses_default_directory_without_value() -> None:
    assert (
        parse_arguments(["--debug-captures"]).debug_captures
        == DEFAULT_DEBUG_CAPTURE_DIRECTORY
    )


def test_debug_captures_accepts_directory() -> None:
    arguments = parse_arguments(["--debug-captures", "/tmp/captures"])
    assert arguments.debug_captures == Path("/tmp/captures")


def test_sam2_is_the_default_backend() -> None:
    arguments = parse_arguments([])

    assert arguments.segmenter == "sam2"
    assert arguments.model == "small"
    assert arguments.sam2_checkpoint == DEFAULT_SAM2_CHECKPOINT
    assert arguments.sam2_device == "auto"


def test_segmentation_backend_options_are_configurable() -> None:
    arguments = parse_arguments(
        [
            "--segmenter",
            "fake",
            "--model",
            "large",
            "--sam2-checkpoint",
            "/tmp/model.pt",
            "--sam2-device",
            "cpu",
        ]
    )

    assert arguments.segmenter == "fake"
    assert arguments.model == "large"
    assert arguments.sam2_checkpoint == Path("/tmp/model.pt")
    assert arguments.sam2_device == "cpu"


def test_model_selects_its_default_checkpoint() -> None:
    arguments = parse_arguments(["--model", "base-plus"])

    assert arguments.sam2_checkpoint == Path(".models/sam2.1_hiera_base_plus.pt")


def test_selected_builtin_model_is_ensured(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    ensured = []
    monkeypatch.setattr("objectsnip.model_setup.ensure_model", ensured.append)

    ensure_selected_model(parse_arguments(["--model", "tiny"]))

    assert ensured == [SAM2_MODELS["tiny"]]


def test_custom_checkpoint_is_not_automatically_downloaded(
    tmp_path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    checkpoint = tmp_path / "custom-model.pt"
    checkpoint.touch()
    ensured = []
    monkeypatch.setattr("objectsnip.model_setup.ensure_model", ensured.append)

    ensure_selected_model(parse_arguments(["--sam2-checkpoint", str(checkpoint)]))

    assert ensured == []


def test_missing_custom_checkpoint_is_rejected_at_startup(tmp_path) -> None:  # type: ignore[no-untyped-def]
    checkpoint = tmp_path / "missing.pt"

    with pytest.raises(RuntimeError, match="SAM 2 checkpoint not found"):
        ensure_selected_model(parse_arguments(["--sam2-checkpoint", str(checkpoint)]))


def test_fake_segmenter_does_not_download_a_model(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    ensured = []
    monkeypatch.setattr("objectsnip.model_setup.ensure_model", ensured.append)

    ensure_selected_model(parse_arguments(["--segmenter", "fake"]))

    assert ensured == []
