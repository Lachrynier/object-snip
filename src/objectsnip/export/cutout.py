from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from objectsnip.domain.geometry import Rect
from objectsnip.segmentation.interface import ImageData


@dataclass(frozen=True, slots=True)
class Cutout:
    rgba: NDArray[np.uint8]
    bounds: Rect


def build_cutout(image: ImageData, mask: NDArray[np.bool_]) -> Cutout:
    if mask.shape != (image.height, image.width):
        raise ValueError("mask dimensions must match the source image")

    selected_y, selected_x = np.nonzero(mask)
    if selected_x.size == 0:
        raise ValueError("cannot export an empty mask")

    left = int(selected_x.min())
    top = int(selected_y.min())
    right = int(selected_x.max()) + 1
    bottom = int(selected_y.max()) + 1
    bounds = Rect(left, top, right - left, bottom - top)

    rgb = image.as_rgb_array()[top:bottom, left:right]
    alpha = mask[top:bottom, left:right].astype(np.uint8) * 255
    rgba = np.empty((*alpha.shape, 4), dtype=np.uint8)
    rgba[..., :3] = rgb
    rgba[..., 3] = alpha
    return Cutout(np.ascontiguousarray(rgba), bounds)
