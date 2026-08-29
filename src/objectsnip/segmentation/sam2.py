from __future__ import annotations

from contextlib import AbstractContextManager, nullcontext
from pathlib import Path
from typing import Any

import numpy as np

from objectsnip.segmentation.interface import (
    ImageData,
    ImageEncoding,
    PredictionRequest,
    SegmentationResult,
)

SAM2_TINY_CONFIG = "configs/sam2.1/sam2.1_hiera_t.yaml"


def select_device(torch_module: Any, requested: str = "auto") -> str:
    if requested not in {"auto", "cpu", "cuda", "mps"}:
        raise ValueError(f"unsupported SAM 2 device: {requested}")
    if requested == "cuda":
        if not torch_module.cuda.is_available():
            raise RuntimeError("CUDA was requested but is not available to PyTorch")
        return "cuda"
    if requested == "mps":
        if not torch_module.backends.mps.is_available():
            raise RuntimeError("MPS was requested but is not available to PyTorch")
        return "mps"
    if requested == "cpu":
        return "cpu"
    if torch_module.cuda.is_available():
        return "cuda"
    if torch_module.backends.mps.is_available():
        return "mps"
    return "cpu"


class Sam2ImageSegmenter:
    def __init__(
        self,
        checkpoint: Path,
        device: str = "auto",
        model_config: str = SAM2_TINY_CONFIG,
    ) -> None:
        self._checkpoint = checkpoint
        self._requested_device = device
        self._model_config = model_config
        self._device: str | None = None
        self._torch: Any = None
        self._predictor: Any = None

    def load(self) -> None:
        if not self._checkpoint.is_file():
            raise RuntimeError(
                f"SAM 2 checkpoint not found: {self._checkpoint}. "
                "Run `just model` or pass --sam2-checkpoint."
            )
        try:
            import torch
            from sam2.build_sam import build_sam2
            from sam2.sam2_image_predictor import SAM2ImagePredictor
        except ImportError as exc:
            raise RuntimeError(
                "SAM 2 dependencies are unavailable; run `uv sync`"
            ) from exc

        device = select_device(torch, self._requested_device)
        try:
            model = build_sam2(
                self._model_config,
                str(self._checkpoint),
                device=device,
                mode="eval",
                apply_postprocessing=True,
            )
        except Exception as exc:
            raise RuntimeError(f"could not load SAM 2 on {device}: {exc}") from exc
        self._torch = torch
        self._device = device
        self._predictor = SAM2ImagePredictor(model)

    def set_image(self, image: ImageData) -> ImageEncoding:
        predictor = self._require_predictor()
        with self._torch.inference_mode(), self._autocast():
            predictor.set_image(image.as_rgb_array())
            embedding = predictor.get_image_embedding()
        return ImageEncoding(
            image_width=image.width,
            image_height=image.height,
            embedding_shape=tuple(int(value) for value in embedding.shape),
            device=self._device or "unknown",
        )

    def predict(self, request: PredictionRequest) -> SegmentationResult:
        predictor = self._require_predictor()
        point_coords = (
            np.asarray([(point.x, point.y) for point in request.points], np.float32)
            if request.points
            else None
        )
        point_labels = (
            np.asarray([int(point.label) for point in request.points], np.int32)
            if request.points
            else None
        )
        box = (
            np.asarray(
                [
                    request.box.left,
                    request.box.top,
                    request.box.right,
                    request.box.bottom,
                ],
                dtype=np.float32,
            )
            if request.box is not None
            else None
        )
        with self._torch.inference_mode(), self._autocast():
            masks, scores, logits = predictor.predict(
                point_coords=point_coords,
                point_labels=point_labels,
                box=box,
                mask_input=request.mask_input,
                multimask_output=request.multimask_output,
                return_logits=False,
                normalize_coords=True,
            )
        return SegmentationResult(
            masks=np.ascontiguousarray(masks, dtype=np.bool_),
            scores=np.ascontiguousarray(scores, dtype=np.float32),
            low_resolution_logits=np.ascontiguousarray(logits, dtype=np.float32),
        )

    def _require_predictor(self) -> Any:
        if self._predictor is None:
            raise RuntimeError("SAM 2 must be loaded before use")
        return self._predictor

    def _autocast(self) -> AbstractContextManager[Any]:
        if self._device == "cuda":
            return self._torch.autocast("cuda", dtype=self._torch.bfloat16)
        return nullcontext()
