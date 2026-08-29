from __future__ import annotations

from pathlib import Path

from objectsnip.segmentation.fake import FakeImageSegmenter
from objectsnip.segmentation.interface import ImageSegmenter
from objectsnip.segmentation.sam2 import Sam2ImageSegmenter

DEFAULT_SAM2_CHECKPOINT = Path(".models/sam2.1_hiera_tiny.pt")


def create_segmenter(
    backend: str,
    checkpoint: Path = DEFAULT_SAM2_CHECKPOINT,
    device: str = "auto",
) -> ImageSegmenter:
    if backend == "sam2":
        return Sam2ImageSegmenter(checkpoint=checkpoint, device=device)
    if backend == "fake":
        return FakeImageSegmenter()
    raise ValueError(f"unknown segmentation backend: {backend}")
