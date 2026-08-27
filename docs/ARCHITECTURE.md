# Architecture

**Status:** Draft

This document owns system boundaries, dependency direction, cross-cutting
technical rules, and architecture-level quality requirements. User-visible
behavior belongs to feature specifications.

## System shape

```text
application lifecycle
        │
        ├── tray + shortcut adapter
        │
        ├── capture adapter ────── frozen screenshot + display context
        │                                      │
        └──────────────────────────────────────▼
                                  capture/session domain
                                    │          │
                          lock crop │          │ state
                                    ▼          ▼
                            segmentation      UI adapter
                               adapter
                                    │
                                    └──────────► export logic/adapters
```

The session/domain layer represents an active interaction. UI, model, capture,
and operating-system integrations are adapters around it.

## Dependency rules

```text
UI ───────────────► domain/session ◄──────── segmentation adapter
capture adapter ──► domain types
export adapter ───► export/domain logic
application ──────► all adapters for composition only
```

- Domain types do not depend on Qt, PyTorch, a model package, or OS services.
- Qt-specific types remain in UI and platform adapters.
- Backend-specific tensors remain inside a segmentation backend.
- Screenshot/model/UI coordinates cross boundaries through explicit value
  types and transformations.
- Application composition may know concrete adapters but must not absorb their
  behavior.

## Initial module strategy

Begin with cohesive files and split them only when responsibilities change
independently or navigation becomes difficult:

```text
src/objectsnip/
├── __main__.py
├── app.py
├── domain/
│   ├── models.py
│   └── session.py
├── segmentation/
│   ├── interface.py
│   ├── fake.py
│   └── <first_backend>.py
├── ui/
│   ├── window.py
│   └── canvas.py
├── capture/
│   └── service.py
└── export/
    └── cutout.py
```

This is a growth guide, not a requirement to create empty modules. Avoid one
file per tiny UI tool until each has independent behavior worth isolating.

## Core domain concepts

An active capture session is authoritative for:

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

Widgets render session state and send user intent; widget objects are not the
authoritative data store.

## Capture-to-segmentation boundary

Capture produces a frozen screenshot plus display metadata. While the context
rectangle is a draft, moving or resizing it changes only session state and UI;
it must not invoke or repeatedly encode with the segmentation backend.

Locking the rectangle commits an immutable context crop. The crop contains only
the selected screenshot pixels and establishes crop-local coordinates. That
committed crop—not the full frozen screenshot—is passed to `Segmenter.set_image`
when model integration is introduced.

```text
frozen screenshot + draft rectangle
                 │
          user locks region
                 ▼
       committed context crop
                 │
          future image encoder
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

## Segmentation boundary

The minimal conceptual interface is:

```python
class Segmenter(Protocol):
    def set_image(self, image: ImageArray) -> None: ...
    def predict(self, prompts: PromptSet) -> SegmentationResult: ...
```

The concrete types will be established by implementation, not copied verbatim
from this sketch. The interface must support cached image encoding when a
backend offers it. Optional backend capabilities may advertise support for
negative points, boxes, multiple candidates, or future prompt types.

A deterministic fake backend is a first-class development adapter. UI and
session work should not require model weights, a GPU, or network access.

## Coordinates

Coordinate conversion is a dedicated subsystem. Scaling arithmetic must not be
scattered through event handlers.

The coordinate chain is explicit:

```text
global desktop → screen-local → frozen-image → context-crop → model
```

Potential spaces also include Qt logical and model-output coordinates.
Transformations must cover high-DPI scaling, negative display offsets, crop
origin translation, clamping, and round trips. The first milestone stops at
context-crop coordinates, but its types must not conflate these spaces.

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
- transparent clipboard interoperability;
- packaging model code and weights without excessive complexity.

The roadmap separates these risks so they are not debugged simultaneously.
