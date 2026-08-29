from __future__ import annotations

import argparse
from pathlib import Path

from objectsnip.segmentation.models import (
    DEFAULT_SAM2_MODEL,
    SAM2_MODEL_NAMES,
    SAM2_MODELS,
)

DEFAULT_DEBUG_CAPTURE_DIRECTORY = Path(".artifacts/captures")
DEFAULT_SAM2_CHECKPOINT = SAM2_MODELS[DEFAULT_SAM2_MODEL].checkpoint


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
        "--model",
        choices=SAM2_MODEL_NAMES,
        default=DEFAULT_SAM2_MODEL,
        help=f"SAM 2.1 model size; defaults to {DEFAULT_SAM2_MODEL}",
    )
    parser.add_argument(
        "--sam2-checkpoint",
        type=Path,
        default=None,
        metavar="PATH",
        help="custom checkpoint path; overrides the --model default",
    )
    parser.add_argument(
        "--sam2-device",
        choices=("auto", "cpu", "cuda", "mps"),
        default="auto",
        help="SAM 2 inference device; defaults to auto",
    )
    parsed = parser.parse_args(arguments)
    if parsed.sam2_checkpoint is None:
        parsed.sam2_checkpoint = SAM2_MODELS[parsed.model].checkpoint
    return parsed


def main() -> None:
    arguments = parse_arguments()
    from objectsnip.app import run
    from objectsnip.segmentation.config import create_segmenter

    segmenter = create_segmenter(
        arguments.segmenter,
        model=arguments.model,
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
