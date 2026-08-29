from __future__ import annotations

from pathlib import Path

from objectsnip.segmentation.fake import FakeImageSegmenter
from objectsnip.segmentation.interface import ImageSegmenter
from objectsnip.segmentation.models import DEFAULT_SAM2_MODEL, SAM2_MODELS
from objectsnip.segmentation.sam2 import Sam2ImageSegmenter

DEFAULT_SAM2_CHECKPOINT = SAM2_MODELS[DEFAULT_SAM2_MODEL].checkpoint


def create_segmenter(
    backend: str,
    model: str = DEFAULT_SAM2_MODEL,
    checkpoint: Path = DEFAULT_SAM2_CHECKPOINT,
    device: str = "auto",
) -> ImageSegmenter:
    if backend == "sam2":
        model_definition = SAM2_MODELS.get(model)
        if model_definition is None:
            raise ValueError(f"unknown SAM 2 model: {model}")
        return Sam2ImageSegmenter(
            checkpoint=checkpoint,
            device=device,
            model_config=model_definition.config,
        )
    if backend == "fake":
        return FakeImageSegmenter()
    raise ValueError(f"unknown segmentation backend: {backend}")
