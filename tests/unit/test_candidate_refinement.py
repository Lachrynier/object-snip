import numpy as np

from objectsnip.app import rank_segmentation_result, refinement_mask_input
from objectsnip.segmentation.interface import SegmentationResult


def segmentation_result() -> SegmentationResult:
    masks = np.stack([np.full((2, 2), index, dtype=np.bool_) for index in (0, 1, 1)])
    scores = np.asarray([0.4, 0.9, 0.7], dtype=np.float32)
    logits = np.stack(
        [np.full((256, 256), index, dtype=np.float32) for index in range(3)]
    )
    return SegmentationResult(masks, scores, logits)


def test_candidates_are_ranked_by_descending_score() -> None:
    ranked = rank_segmentation_result(segmentation_result())

    np.testing.assert_allclose(ranked.scores, [0.9, 0.7, 0.4])
    assert float(ranked.low_resolution_logits[0, 0, 0]) == 1
    assert float(ranked.low_resolution_logits[1, 0, 0]) == 2
    assert float(ranked.low_resolution_logits[2, 0, 0]) == 0


def test_active_candidate_logits_become_next_mask_input() -> None:
    ranked = rank_segmentation_result(segmentation_result())

    mask_input = refinement_mask_input(ranked, 1)

    assert mask_input is not None
    assert mask_input.shape == (1, 256, 256)
    assert mask_input.dtype == np.float32
    assert np.all(mask_input == 2)


def test_first_prediction_has_no_refinement_mask() -> None:
    assert refinement_mask_input(None, 0) is None
