import numpy as np
import pytest

from objectsnip.segmentation.fake import FakeImageSegmenter
from objectsnip.segmentation.interface import (
    BoxPrompt,
    ImageData,
    PointLabel,
    PointPrompt,
    PredictionRequest,
)


def image_data(
    width: int = 32,
    height: int = 24,
    pixels: bytes | None = None,
) -> ImageData:
    stride = width * 3
    return ImageData(
        width=width,
        height=height,
        bytes_per_line=stride,
        rgb_bytes=pixels or bytes(stride * height),
    )


def test_image_data_validates_dimensions_and_storage() -> None:
    with pytest.raises(ValueError):
        ImageData(width=0, height=1, bytes_per_line=0, rgb_bytes=b"")
    with pytest.raises(ValueError):
        ImageData(width=2, height=1, bytes_per_line=3, rgb_bytes=b"\0" * 3)
    with pytest.raises(ValueError):
        ImageData(width=1, height=1, bytes_per_line=3, rgb_bytes=b"\0" * 2)


def test_image_data_removes_row_padding_for_sam() -> None:
    image = ImageData(
        width=1,
        height=2,
        bytes_per_line=4,
        rgb_bytes=b"\x01\x02\x03\xff\x04\x05\x06\xff",
    )

    assert image.as_rgb_array().tolist() == [[[1, 2, 3]], [[4, 5, 6]]]


def test_prediction_requires_a_supported_prompt() -> None:
    with pytest.raises(ValueError):
        PredictionRequest()
    with pytest.raises(ValueError):
        PredictionRequest(mask_input=np.zeros((256, 256), dtype=np.float32))


def test_fake_segmenter_mirrors_sam_encoding_metadata() -> None:
    segmenter = FakeImageSegmenter()
    segmenter.load()

    encoding = segmenter.set_image(image_data())

    assert (encoding.image_width, encoding.image_height) == (32, 24)
    assert encoding.embedding_shape == (1, 256, 64, 64)
    assert encoding.device == "fake"


def test_fake_segmenter_returns_sam_shaped_candidates() -> None:
    segmenter = FakeImageSegmenter()
    segmenter.load()
    segmenter.set_image(image_data())
    request = PredictionRequest(
        points=(
            PointPrompt(16, 12, PointLabel.INCLUDE),
            PointPrompt(2, 2, PointLabel.EXCLUDE),
        ),
        box=BoxPrompt(4, 4, 28, 20),
    )

    result = segmenter.predict(request)

    assert result.masks.shape == (3, 24, 32)
    assert result.masks.dtype == np.bool_
    assert result.scores.shape == (3,)
    assert result.scores.dtype == np.float32
    assert result.low_resolution_logits.shape == (3, 256, 256)
    assert result.low_resolution_logits.dtype == np.float32


def test_fake_segmenter_supports_single_candidate_and_logit_refinement() -> None:
    segmenter = FakeImageSegmenter()
    segmenter.load()
    segmenter.set_image(image_data())
    previous_logits = np.zeros((1, 256, 256), dtype=np.float32)

    result = segmenter.predict(
        PredictionRequest(mask_input=previous_logits, multimask_output=False)
    )

    assert result.masks.shape == (1, 24, 32)
    assert result.scores.shape == (1,)
    assert result.low_resolution_logits.shape == (1, 256, 256)
