from __future__ import annotations

import argparse
from pathlib import Path

DEFAULT_DEBUG_CAPTURE_DIRECTORY = Path(".artifacts/captures")
DEFAULT_SAM2_CHECKPOINT = Path(".models/sam2.1_hiera_tiny.pt")


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
    parser.add_argument(
        "--segmenter",
        choices=("sam2", "fake"),
        default="sam2",
        help="segmentation backend; defaults to sam2",
    )
    parser.add_argument(
        "--sam2-checkpoint",
        type=Path,
        default=DEFAULT_SAM2_CHECKPOINT,
        metavar="PATH",
        help=f"SAM 2.1 checkpoint; defaults to {DEFAULT_SAM2_CHECKPOINT}",
    )
    parser.add_argument(
        "--sam2-device",
        choices=("auto", "cpu", "cuda", "mps"),
        default="auto",
        help="SAM 2 inference device; defaults to auto",
    )
    return parser.parse_args(arguments)


def main() -> None:
    arguments = parse_arguments()
    from objectsnip.app import run
    from objectsnip.segmentation.config import create_segmenter

    segmenter = create_segmenter(
        arguments.segmenter,
        checkpoint=arguments.sam2_checkpoint,
        device=arguments.sam2_device,
    )
    raise SystemExit(
        run(
            debug_capture_directory=arguments.debug_captures,
            segmenter=segmenter,
        )
    )


if __name__ == "__main__":
    main()
