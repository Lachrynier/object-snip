from pathlib import Path

from objectsnip.__main__ import DEFAULT_DEBUG_CAPTURE_DIRECTORY, parse_arguments


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
