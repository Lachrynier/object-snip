import os
from pathlib import Path

import numpy as np
import pytest

from objectsnip.segmentation.interface import (
    ImageData,
    PointLabel,
    PointPrompt,
    PredictionRequest,
)
from objectsnip.segmentation.sam2 import Sam2ImageSegmenter

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("OBJECTSNIP_RUN_SAM2_TESTS") != "1",
        reason="set OBJECTSNIP_RUN_SAM2_TESTS=1 to run model-backed tests",
    ),
]


def test_real_sam2_backend_matches_shared_contract() -> None:
    width = height = 64
    pixels = np.zeros((height, width, 3), dtype=np.uint8)
    pixels[16:48, 16:48] = 255
    image = ImageData(width, height, width * 3, pixels.tobytes())
    segmenter = Sam2ImageSegmenter(Path(".models/sam2.1_hiera_tiny.pt"), device="cpu")

    segmenter.load()
    encoding = segmenter.set_image(image)
    result = segmenter.predict(
        PredictionRequest(
            points=(PointPrompt(32, 32, PointLabel.INCLUDE),),
        )
    )

    assert encoding.embedding_shape == (1, 256, 64, 64)
    assert encoding.device == "cpu"
    assert result.masks.shape == (3, height, width)
    assert result.masks.dtype == np.bool_
    assert result.scores.shape == (3,)
    assert result.scores.dtype == np.float32
    assert result.low_resolution_logits.shape == (3, 256, 256)
    assert result.low_resolution_logits.dtype == np.float32
