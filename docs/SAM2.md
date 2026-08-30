# SAM 2 integration

**Status:** Implemented  
**Backend:** Official SAM 2.1 Hiera models

This document owns the concrete SAM 2 integration contract, model setup,
runtime behavior, and the parity required from the deterministic fake backend.
Selection interaction remains owned by
[`features/selection.md`](features/selection.md).

## Upstream and model

ObjectSnip uses Meta's official
[`facebookresearch/sam2`](https://github.com/facebookresearch/sam2) package,
pinned to an exact Git commit in `pyproject.toml`. The integration uses the
static-image `SAM2ImagePredictor` with the improved SAM 2.1 Hiera checkpoints.
Small is the default; all official sizes are available:

| `--model` value | Parameters | Default checkpoint |
| --- | ---: | --- |
| `tiny` | 38.9M | `.models/sam2.1_hiera_tiny.pt` |
| `small` | 46M | `.models/sam2.1_hiera_small.pt` |
| `base-plus` | 80.8M | `.models/sam2.1_hiera_base_plus.pt` |
| `large` | 224.4M | `.models/sam2.1_hiera_large.pt` |

The default model uses:

- config: `configs/sam2.1/sam2.1_hiera_s.yaml`;
- checkpoint: `sam2.1_hiera_small.pt`;
- official checkpoint URL:
  `https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_small.pt`;
- expected SHA-256:
  `6d1aa6f30de5c92224f8172114de081d104bbd23dd9dc5c58996f0cad5dc4d38`;
- expected file size: 184,416,285 bytes.

The package and model are Apache-2.0 licensed by Meta. Model weights are not
committed to this repository.

## Setup

Install the locked Python dependencies and verified checkpoint:

```bash
just setup
just model
```

Download another size by passing its name to the recipe:

```bash
just model tiny
just model base-plus
just model large
```

Select the matching installed model at runtime with `--model`:

```bash
uv run objectsnip --model small
```

The checkpoint path is inferred from the selected model. A custom path or
device can still be selected explicitly:

```bash
uv run objectsnip --model large --sam2-checkpoint /path/to/model.pt --sam2-device cpu
```

`--sam2-device auto` is the default. It chooses CUDA, then Apple MPS, then CPU.
Explicitly requesting an unavailable accelerator produces a visible preparation
error instead of silently changing devices. `--segmenter fake` runs the same
application lifecycle without loading SAM or its checkpoint.

## Shared backend contract

Both `Sam2ImageSegmenter` and `FakeImageSegmenter` implement the same
`ImageSegmenter` protocol:

```python
class ImageSegmenter(Protocol):
    def load(self) -> None: ...
    def set_image(self, image: ImageData) -> ImageEncoding: ...
    def predict(self, request: PredictionRequest) -> SegmentationResult: ...
```

The fake is a deterministic behavioral test double. It matches method names,
accepted request types, result types, dtypes, dimensions, candidate counts, and
error ordering. It does not attempt to reproduce SAM's learned mask quality or
scores.

## Image encoding

Capture passes an immutable `ImageData` containing width, height, row stride,
and RGB888 bytes. Padding is removed and the backend creates a writable,
contiguous NumPy array with shape `height × width × 3`, dtype `uint8`, and values
in `[0, 255]`, as required by `SAM2ImagePredictor.set_image()`.

`set_image()` runs SAM's image encoder and caches predictor features for all
later prompts on that crop. It returns only backend-neutral metadata:

```text
ImageEncoding(
    image_width,
    image_height,
    embedding_shape,  # Hiera models currently return 1 × 256 × 64 × 64
    device,           # cuda, mps, cpu, or fake
)
```

The actual PyTorch feature tensors remain private to the SAM adapter. A new
locked crop replaces those features and invalidates all earlier predictions.

Model loading begins on ObjectSnip startup. Image encoding begins only after
**Lock region**. Both operations use the same persistent single-worker executor
and never run on Qt's GUI thread. The workspace displays `Preparing image…`
until encoding finishes. Closing, replacing, or retrying a session advances its
generation so stale completions are ignored.

## Prediction input

`PredictionRequest` mirrors the official image predictor inputs:

- `points`: zero or more crop-local `(x, y)` pixel coordinates;
- point label `1` / `INCLUDE`: foreground;
- point label `0` / `EXCLUDE`: background;
- `box`: optional crop-local `(left, top, right, bottom)` / XYXY box;
- `mask_input`: optional `float32` array shaped `1 × 256 × 256`, normally the
  logits selected from a previous result;
- `multimask_output`: requests three candidates when true and one when false.

At least one point, box, or mask input is required by ObjectSnip's contract.
Coordinates are expressed against the original locked crop. The adapter lets
SAM normalize them internally.

## Prediction output

`SegmentationResult` preserves the three values returned by the official
predictor while removing PyTorch tensors from the boundary:

- `masks`: boolean array shaped `candidates × image height × image width`;
- `scores`: `float32` array shaped `candidates`, containing SAM's predicted mask
  quality for each candidate;
- `low_resolution_logits`: `float32` array shaped
  `candidates × 256 × 256`.

For an ambiguous single click, multimask mode normally returns three candidates.
ObjectSnip score-ranks them, initially displays the highest-scoring candidate,
and lets the user choose among them in the toolbar. On the next prompt edit, the
active candidate's logits are passed back as `mask_input`, preserving the user's
chosen mask during refinement. The logits are not probabilities and are not
displayed directly. **Reset prompts** removes all points and clears both the
visible mask and refinement state.

## Device and numerical behavior

CUDA inference uses `torch.inference_mode()` and bfloat16 autocasting. CPU and
MPS use inference mode without autocast. The official project notes that MPS
support can produce different or degraded results compared with CUDA.

The optional SAM 2 CUDA extension is not required for the image predictor's
normal output. A working PyTorch CUDA runtime and NVIDIA driver are still needed
for GPU inference. When CUDA is unavailable, automatic selection uses CPU.

## Current scope

The real backend loads and encodes locked crops, and its prediction contract is
integration-tested with point prompts. The selection window collects positive
and negative point prompts, displays ranked masks, lets the user select a
candidate, and reuses that candidate's logits for refinement.

Run the opt-in real-model contract test with:

```bash
OBJECTSNIP_RUN_SAM2_TESTS=1 uv run pytest tests/integration/test_sam2_backend.py
```

Normal unit tests exercise the same contract through `FakeImageSegmenter` and
do not require weights, PyTorch device initialization, or network access.
General development setup and project commands live in
[`DEVELOPMENT.md`](DEVELOPMENT.md).
