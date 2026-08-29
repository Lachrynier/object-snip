from pathlib import Path

from objectsnip.__main__ import (
    DEFAULT_DEBUG_CAPTURE_DIRECTORY,
    DEFAULT_SAM2_CHECKPOINT,
    parse_arguments,
)


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
    assert arguments.model == "tiny"
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
