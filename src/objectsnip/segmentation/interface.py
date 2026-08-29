from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Protocol

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class ImageData:
    width: int
    height: int
    bytes_per_line: int
    rgb_bytes: bytes

    def __post_init__(self) -> None:
        expected_size = self.bytes_per_line * self.height
        if self.width <= 0 or self.height <= 0:
            raise ValueError("image dimensions must be positive")
        if self.bytes_per_line < self.width * 3:
            raise ValueError("image stride is too small for RGB pixels")
        if len(self.rgb_bytes) != expected_size:
            raise ValueError("pixel data does not match image dimensions")

    def as_rgb_array(self) -> NDArray[np.uint8]:
        rows = np.frombuffer(self.rgb_bytes, dtype=np.uint8).reshape(
            self.height, self.bytes_per_line
        )
        pixels = rows[:, : self.width * 3].reshape(self.height, self.width, 3)
        return np.array(pixels, copy=True, order="C")


class PointLabel(IntEnum):
    EXCLUDE = 0
    INCLUDE = 1


@dataclass(frozen=True, slots=True)
class PointPrompt:
    x: float
    y: float
    label: PointLabel


@dataclass(frozen=True, slots=True)
class BoxPrompt:
    left: float
    top: float
    right: float
    bottom: float

    def __post_init__(self) -> None:
        if self.right <= self.left or self.bottom <= self.top:
            raise ValueError("prompt box must have positive area")


@dataclass(frozen=True, slots=True)
class ImageEncoding:
    image_width: int
    image_height: int
    embedding_shape: tuple[int, ...]
    device: str


@dataclass(frozen=True, slots=True)
class PredictionRequest:
    points: tuple[PointPrompt, ...] = ()
    box: BoxPrompt | None = None
    mask_input: NDArray[np.float32] | None = None
    multimask_output: bool = True

    def __post_init__(self) -> None:
        if not self.points and self.box is None and self.mask_input is None:
            raise ValueError("prediction requires at least one prompt")
        if self.mask_input is not None and self.mask_input.shape != (1, 256, 256):
            raise ValueError("mask input must have shape 1x256x256")


@dataclass(frozen=True, slots=True)
class SegmentationResult:
    masks: NDArray[np.bool_]
    scores: NDArray[np.float32]
    low_resolution_logits: NDArray[np.float32]

    def __post_init__(self) -> None:
        if self.masks.ndim != 3:
            raise ValueError("masks must have shape candidates x height x width")
        candidates = self.masks.shape[0]
        if self.scores.shape != (candidates,):
            raise ValueError("scores must contain one value per mask")
        if self.low_resolution_logits.shape != (candidates, 256, 256):
            raise ValueError(
                "low-resolution logits must have shape candidates x 256 x 256"
            )


class ImageSegmenter(Protocol):
    def load(self) -> None: ...

    def set_image(self, image: ImageData) -> ImageEncoding: ...

    def predict(self, request: PredictionRequest) -> SegmentationResult: ...
