from __future__ import annotations

import numpy as np

from objectsnip.segmentation.interface import (
    ImageData,
    ImageEncoding,
    PointLabel,
    PredictionRequest,
    SegmentationResult,
)


class FakeImageSegmenter:
    """Deterministic test double with the same contract and shapes as SAM 2."""

    def __init__(self) -> None:
        self._image: ImageData | None = None

    def load(self) -> None:
        pass

    def set_image(self, image: ImageData) -> ImageEncoding:
        self._image = image
        return ImageEncoding(
            image_width=image.width,
            image_height=image.height,
            embedding_shape=(1, 256, 64, 64),
            device="fake",
        )

    def predict(self, request: PredictionRequest) -> SegmentationResult:
        if self._image is None:
            raise RuntimeError("an image must be set before prediction")
        candidates = 3 if request.multimask_output else 1
        masks = np.zeros(
            (candidates, self._image.height, self._image.width), dtype=np.bool_
        )
        yy, xx = np.ogrid[: self._image.height, : self._image.width]

        if request.box is not None:
            box = request.box
            left = max(0, round(box.left))
            top = max(0, round(box.top))
            right = min(self._image.width, round(box.right))
            bottom = min(self._image.height, round(box.bottom))
            masks[:, top:bottom, left:right] = True

        for point in request.points:
            for candidate in range(candidates):
                radius = 8 + candidate * 4
                disk = (xx - point.x) ** 2 + (yy - point.y) ** 2 <= radius**2
                if point.label is PointLabel.INCLUDE:
                    masks[candidate] |= disk
                else:
                    masks[candidate] &= ~disk

        sample_y = np.linspace(0, self._image.height - 1, 256).astype(np.intp)
        sample_x = np.linspace(0, self._image.width - 1, 256).astype(np.intp)
        sampled = masks[:, sample_y[:, None], sample_x]
        logits = np.where(sampled, 8.0, -8.0).astype(np.float32)
        scores = np.linspace(0.95, 0.75, candidates, dtype=np.float32)
        return SegmentationResult(
            masks=masks,
            scores=scores,
            low_resolution_logits=logits,
        )
