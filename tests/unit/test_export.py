import numpy as np
import pytest

from objectsnip.domain.geometry import Rect
from objectsnip.export.cutout import build_cutout
from objectsnip.segmentation.interface import ImageData


def image_data(pixels: np.ndarray) -> ImageData:
    height, width, _channels = pixels.shape
    return ImageData(width, height, width * 3, pixels.tobytes())


def test_cutout_is_tightly_bounded_and_uses_mask_for_alpha() -> None:
    pixels = np.arange(4 * 5 * 3, dtype=np.uint8).reshape(4, 5, 3)
    mask = np.zeros((4, 5), dtype=np.bool_)
    mask[1, 2] = True
    mask[2, 1:4] = True

    cutout = build_cutout(image_data(pixels), mask)

    assert cutout.bounds == Rect(1, 1, 3, 2)
    np.testing.assert_array_equal(cutout.rgba[..., :3], pixels[1:3, 1:4])
    np.testing.assert_array_equal(
        cutout.rgba[..., 3],
        np.array([[0, 255, 0], [255, 255, 255]], dtype=np.uint8),
    )


def test_cutout_handles_a_single_edge_pixel() -> None:
    pixels = np.zeros((2, 3, 3), dtype=np.uint8)
    mask = np.zeros((2, 3), dtype=np.bool_)
    mask[1, 2] = True

    cutout = build_cutout(image_data(pixels), mask)

    assert cutout.bounds == Rect(2, 1, 1, 1)
    assert cutout.rgba.shape == (1, 1, 4)
    assert cutout.rgba[0, 0, 3] == 255


def test_cutout_rejects_an_empty_mask() -> None:
    pixels = np.zeros((2, 3, 3), dtype=np.uint8)

    with pytest.raises(ValueError, match="empty mask"):
        build_cutout(image_data(pixels), np.zeros((2, 3), dtype=np.bool_))


def test_cutout_rejects_mismatched_dimensions() -> None:
    pixels = np.zeros((2, 3, 3), dtype=np.uint8)

    with pytest.raises(ValueError, match="dimensions"):
        build_cutout(image_data(pixels), np.zeros((1, 3), dtype=np.bool_))
