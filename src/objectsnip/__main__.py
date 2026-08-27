from __future__ import annotations

import argparse
from pathlib import Path

DEFAULT_DEBUG_CAPTURE_DIRECTORY = Path(".artifacts/captures")


def parse_arguments(arguments: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="objectsnip")
    parser.add_argument(
        "--debug-captures",
        nargs="?",
        const=DEFAULT_DEBUG_CAPTURE_DIRECTORY,
        type=Path,
        metavar="DIRECTORY",
        help=(
            "save source and locked-region PNGs; defaults to "
            f"{DEFAULT_DEBUG_CAPTURE_DIRECTORY}"
        ),
    )
    return parser.parse_args(arguments)


def main() -> None:
    arguments = parse_arguments()
    from objectsnip.app import run

    raise SystemExit(run(debug_capture_directory=arguments.debug_captures))


if __name__ == "__main__":
    main()
