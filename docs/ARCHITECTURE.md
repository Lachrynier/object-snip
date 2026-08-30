# Architecture

**Status:** Implemented, with platform validation gaps

This document owns system boundaries, dependency direction, cross-cutting
technical rules, and architecture-level quality requirements. User-visible
behavior belongs to feature specifications.

## System shape

```text
ObjectSnipApplication
    ├── tray and global-shortcut portal
    ├── screenshot portal or direct screen capture
    │       └── CaptureOverlay
    │               └── committed context crop
    └── ObjectSelectionWindow
            ├── ImageEncodingService
            │       └── SAM 2.1 or fake segmenter
            └── cutout builder
                    ├── system clipboard
                    └── PNG file writer
```

`ObjectSnipApplication` currently coordinates the interaction and asynchronous
request lifecycle. Capture geometry is model-independent, and segmentation is
hidden behind an application-owned protocol. Export applies the active mask in
backend-neutral code, tightly crops the RGBA result, and sends the resulting
image to either the Qt clipboard or PNG writer.

## Dependency direction

```text
capture UI ───────► geometry
application ──────► capture, shortcuts, selection UI, segmentation service
segmentation service ──────► application-owned segmentation protocol
SAM and fake backends ─────► application-owned segmentation protocol
```

The current design follows these rules:

- Domain types do not depend on Qt, PyTorch, a model package, or OS services.
- Qt-specific types remain in UI and platform adapters.
- Backend-specific tensors remain inside a segmentation backend.
- Screenshot/model/UI coordinates cross boundaries through explicit value
  types and transformations.
- `app.py` owns composition and coordination, including candidate ranking and
  refinement state. If that behavior grows, it should move into a testable
  session component rather than continuing to expand application wiring.

## Current module structure

The source tree is organized by integration boundary:

```text
src/objectsnip/
├── __main__.py
├── app.py
├── debug_capture.py
├── domain/
│   └── geometry.py
├── export/
│   ├── cutout.py
│   └── file.py
├── capture/
│   ├── crop.py
│   ├── portal.py
│   └── screen.py
├── segmentation/
│   ├── interface.py
│   ├── fake.py
│   ├── models.py
│   ├── sam2.py
│   └── service.py
├── shortcuts/
│   └── portal.py
├── ui/
│   ├── overlay.py
│   └── selection_window.py
```

`app.py` composes these pieces and currently owns the active capture and
selection lifecycle. The selection widget owns prompt and viewport state while
the application owns asynchronous request generations and candidate refinement
state. A separate session layer should be introduced only when those state
transitions need to be shared or tested independently.

## Core domain concepts

The intended session model needs to represent:

- the frozen screenshot and its display context;
- the draft context rectangle and whether it is locked;
- prompt collection and selection;
- active interaction tool;
- current segmentation candidates;
- active candidate;
- undo/redo state;
- monotonically increasing prediction revision.

Prompts should use stable identities and immutable value semantics where
practical. Candidate masks returned by backends use image coordinates and a
backend-neutral representation.

This model is not yet a separate domain object. Today, state is split between
`ObjectSnipApplication`, `CaptureOverlay`, and `ObjectSelectionWindow`.

## Capture-to-segmentation boundary

Capture produces a frozen screenshot plus display metadata. While the context
rectangle is a draft, moving or resizing it changes only session state and UI;
it must not invoke or repeatedly encode with the segmentation backend.

Locking the rectangle commits an immutable context crop. The crop contains only
the selected screenshot pixels and establishes crop-local coordinates. That
committed crop—not the full frozen screenshot—is passed to
`ImageSegmenter.set_image()`.

```text
frozen screenshot + draft rectangle
                 │
          user locks region
                 ▼
       committed context crop
                 │
       background image encoder
```

Unlocking or revising an already encoded crop is not part of the first
milestone. If later supported, it creates a new committed crop and invalidates
all prompts and segmentation results tied to the previous crop.

## Linux display compatibility

Native Wayland does not expose the compositor's completed desktop pixels
through Qt's direct `QScreen.grabWindow()` path. ObjectSnip therefore requests a
screenshot asynchronously through `org.freedesktop.portal.Screenshot` on the
user's D-Bus session. A successful portal response contains a local image URI,
which is loaded into the same backend-neutral `QImage` boundary used by the UI.

Cancellation is a normal portal outcome and does not produce an application
error. Missing services, malformed responses, and unreadable returned images
are errors. Other Qt platforms currently use direct `QScreen` capture, with a
uniform-image guard to reject unusable buffers such as a black XWayland root.

The end-to-end application has so far been manually tested only on Fedora under
Wayland. Other distributions, desktop environments, X11, and non-Linux Qt
platforms should be treated as implemented code paths without validation, not
as supported configurations.

## Export boundary

The export transformation consumes backend-neutral RGB image data and a boolean
mask. It rejects empty or dimensionally incompatible masks, applies binary
alpha, and returns the smallest RGBA rectangle containing the selected pixels.
This transformation is independent of Qt and the segmentation backend. The
application converts the result to a `QImage`, then either places it on the
clipboard or passes it to the PNG writer. Export failures leave the selection
window open so the user can retry.

## Segmentation boundary

The implemented interface is:

```python
class ImageSegmenter(Protocol):
    def load(self) -> None: ...
    def set_image(self, image: ImageData) -> ImageEncoding: ...
    def predict(self, request: PredictionRequest) -> SegmentationResult: ...
```

The first implemented boundary converts Qt images into immutable RGB image
data, preloads an encoder on a persistent single-worker executor, and encodes
each committed crop away from the GUI event loop. Request generations prevent
results for closed or replaced workspaces from becoming active. The official
SAM 2.1 Hiera Small adapter is the default backend. A deterministic fake mirrors
its request/result contract so most lifecycle and session tests need neither
weights nor an accelerator. [`SAM2.md`](SAM2.md) owns the concrete contract.

The interface must support cached image encoding when a backend offers it.
Optional backend capabilities may advertise support for negative points,
boxes, multiple candidates, or future prompt types.

A deterministic fake backend is a first-class development adapter. UI and
session work should not require model weights, a GPU, or network access.

## Coordinates

Capture geometry is centralized in `domain/geometry.py`; crop conversion lives
in `capture/crop.py`; selection view/image transforms live alongside the custom
selection widget. These conversions are covered by deterministic unit tests.

The coordinate chain is explicit:

```text
global desktop → screen-local → frozen-image → context-crop → model
```

Potential spaces also include Qt logical and model-output coordinates.
Transformations must eventually cover high-DPI scaling, negative display
offsets, crop-origin translation, clamping, and round trips. Multi-monitor and
mixed-DPI behavior remain known gaps.

## Asynchronous prediction

Long inference never blocks the Qt event loop. Each prediction request carries
the session revision from which it was created. A returned result is applied
only if that revision remains current; stale results are discarded.

Prompt dragging renders immediately and may debounce or rate-limit prediction.
A final prediction occurs after the edit completes. Exact timing is an
implementation/performance decision informed by measurement.

## Testing boundaries

- **Unit:** rectangle creation, movement, resize hit-testing, bounds clamping,
  coordinate conversion, prompts, session transitions, history, stale-result
  rejection, mask application, crop bounds, and error cases.
- **Integration:** fake backend with real session logic, out-of-order async
  results, selected UI interactions, and platform adapters where practical.
- **Model evaluation:** a separate curated image set and benchmark output; never
  part of ordinary deterministic unit tests.

Tests should be organized by test kind when the suite exists:

```text
tests/
├── unit/
├── integration/
└── fixtures/
```

Experimental model comparisons belong in `benchmarks/` or `prototypes/` until
their boundary is understood.

## Architectural invariants

The following are **Accepted candidates** pending owner review:

1. Qt types do not enter segmentation or domain logic.
2. Model tensor types do not enter UI or domain logic.
3. Coordinate conversion is centralized and tested.
4. Session state is authoritative during an interaction.
5. Only a locked context crop crosses from capture into segmentation.
6. Draft region edits never trigger image encoding.
7. Segmentation backends implement a common application-owned interface.
8. Image encoding is reused across refinements when supported.
9. Long inference does not block the GUI event loop.
10. Stale predictions never overwrite newer session state.
11. Export transformation does not live in rendering widgets.
12. Later feature scope is not introduced through infrastructure work.

Once reviewed, change the heading above to **Accepted**. A future change to one
of these invariants should include a decision record.

## Known architecture risks

- interactive mask quality and latency on consumer hardware;
- X11 versus Wayland capture and shortcut integration;
- high-DPI and multi-monitor coordinate correctness;
- clipboard interoperability outside the tested Fedora Wayland environment;
- packaging model code and weights without excessive complexity.

The roadmap separates these risks so they are not debugged simultaneously.
