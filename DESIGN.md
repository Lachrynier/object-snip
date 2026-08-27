# ObjectSnip — Design Document

> **Status:** Draft  
> **Working project name:** ObjectSnip  
> **Primary platform for initial development:** Linux desktop  
> **Initial UI framework:** PySide6 / Qt  
> **Primary language:** Python  
> **Core capability:** Local interactive object segmentation directly from a frozen screenshot in a snipping tool

---

## 1. Executive Summary

ObjectSnip is a local desktop screenshot utility that allows a user to extract arbitrary visual objects directly from their screen.

Traditional screenshot tools primarily select rectangular regions. ObjectSnip instead treats the visual object itself as the selection primitive.

The intended interaction is:

- Have ObjectSnip in the system tray.
1. Trigger ObjectSnip using a global shortcut.
2. The current screen is captured and displayed as a fullscreen frozen overlay like a snipping tool.
3. The user clicks an object.
4. A promptable segmentation model predicts one or more object masks.
5. If the first result is ambiguous, the user refines it using additional positive or negative points, box constraints, or candidate cycling.
6. The user presses Enter.
7. The selected object is copied to the clipboard as a transparent image.

The product should make the common case extremely fast:

> **See object → snip object → paste object.**

The application is local-first. Screenshots and model inputs remain on the user's machine.

---

## 2. Problem Statement

Existing screenshot utilities are optimized around rectangular crops.

This is effective when the user wants a rectangular area, but awkward when they want an isolated visual object such as:

- a person,
- a chair,
- an icon,
- a product,
- a diagram component,
- a piece of clothing,
- an object inside a webpage,
- an object inside a video frame,
- or another irregularly shaped subject.

A typical background-removal workflow requires several steps:

1. capture screenshot,
2. crop the relevant region,
3. save or copy it,
4. open another application or website,
5. upload or paste the image,
6. perform background removal,
7. correct segmentation mistakes if possible,
8. copy or download the final result.

ObjectSnip aims to collapse this into one direct interaction on the screen.

The harder part of this problem is ambiguity.

A click on a person's torso could mean:

- the shirt,
- the upper body,
- the full person,
- the foreground person excluding carried objects,
- or another nearby object.

The application must therefore treat model output as an editable proposal rather than a final answer.

---

## 3. Product Vision

ObjectSnip should feel like a normal screenshot utility whose selection mechanism has become semantic.

The user should not need to understand machine learning concepts.

They should see:

- include,
- exclude,
- box,
- lasso,
- undo,
- redo,
- copy,
- save.

They should not see:

- embeddings,
- mask decoder,
- logits,
- inference tensors,
- feature maps,
- transformer prompts.

The product should preserve the directness of tools such as KDE Spectacle, GNOME Screenshot, Windows Snipping Tool, or macOS Screenshot while adding interactive object selection.

---

## 4. Product Principles

### 4.1 Local-first

Screenshots must remain local by default.

No cloud API should be required for the core workflow.

Reasons:

- privacy,
- low latency,
- no API costs,
- offline operation,
- predictable behavior,
- simpler distribution,
- no account requirement.

### 4.2 Fast common path

The target interaction for an easy object is:

```text
global shortcut
→ click object
→ Enter
→ paste elsewhere
```

Refinement tools exist for difficult cases but should not burden simple cases.

### 4.3 Model output is editable

Segmentation is probabilistic.

The UI should expose fast ways to correct uncertainty.

### 4.4 The model is replaceable

The application should depend on an abstract promptable-segmentation interface rather than a specific SAM implementation.

The first model may not be the final model.

### 4.5 The project is not a general image editor

ObjectSnip should not become a lightweight Photoshop clone.

Every major feature should support the core task:

> select an object from the screen and do something useful with that selected object.

### 4.6 Graceful degradation

The application should still provide useful behavior when segmentation fails.

Potential manual fallbacks include:

- rectangular crop,
- manual lasso,
- hard mask editing in future versions.

### 4.7 UI and model code remain independent

Qt widgets should not contain model logic.

Model backends should not know about Qt.

### 4.8 Performance is part of UX

Interactive segmentation is only useful if refinement feels immediate.

The architecture should therefore distinguish between:

- initial image encoding,
- prompt-based mask decoding,
- mask rendering.

---

# 5. Target Users

The initial target is a desktop user who frequently copies visual material between applications.

Examples include:

- students preparing notes or slides,
- developers making documentation or bug reports,
- designers collecting references,
- people posting screenshots to chat or social platforms,
- researchers extracting figures or visual objects,
- educators preparing teaching material,
- users making quick compositions in presentation software.

The application is not initially optimized for professional photo editing.

---

# 6. Core Use Cases

## 6.1 Copy an object from the screen

A user sees an object on screen and wants it without its background.

Example:

```text
presentation on screen
→ trigger ObjectSnip
→ click diagram object
→ mask appears
→ Enter
→ paste transparent object into notes
```

## 6.2 Refine an ambiguous segmentation

A user clicks a person, but the model selects only the jacket.

The user:

1. adds another positive point on the person's trousers,
2. optionally adds a negative point on the background,
3. mask updates,
4. presses Enter.

## 6.3 Switch among plausible interpretations

A single click may produce several valid masks.

Example:

- glasses,
- face,
- whole person.

The user can cycle candidates without adding more prompts.

## 6.4 Constrain the target region

The user can drag a box around an object to indicate that the relevant target lies inside a rough region.

## 6.5 Save rather than copy

Instead of copying to clipboard, the user can save the transparent result as PNG.

---

# 7. Interaction Design

## 7.1 Capture workflow

The high-level flow is:

```text
Idle
  │
  │ global shortcut
  ▼
Capture screen
  │
  ▼
Fullscreen frozen overlay
  │
  ▼
User provides prompt
  │
  ▼
Segmentation result
  │
  ├── refine
  ├── switch candidate
  ├── undo/redo
  └── export
```

The user should perceive the desktop as frozen.

Implementation-wise, ObjectSnip captures the screen and then displays that screenshot in a fullscreen frameless Qt window.

The user is interacting with ObjectSnip, not the applications beneath it.

---

## 7.2 Default tool

The default tool is:

> **Include point**

A left click indicates:

> This location belongs to the object I want.

For many objects this should be sufficient.

---

## 7.3 Positive point

Visual representation:

- small visible marker,
- distinct include styling,
- draggable after placement.

Behavior:

```text
left click
→ add positive point
→ run prediction
→ update mask
```

---

## 7.4 Negative point

A negative point means:

> This location does not belong to the object I want.

This is useful when:

- nearby objects are accidentally included,
- the background is included,
- adjacent objects touch,
- the model selects a larger semantic unit than intended.

The user switches to the negative-point tool before placing the point.

A future shortcut may allow modifier-based placement.

---

## 7.5 Box prompt

The user drags a rectangle around the target.

Meaning:

> The desired object is contained approximately within this region.

The box is a model prompt, not necessarily the final crop.

The predicted mask may occupy any irregular subset of the box.

---

## 7.6 Candidate cycling

Promptable segmentation models may produce multiple masks for ambiguous prompts.

ObjectSnip should preserve these candidate masks when supported by the backend.

Suggested controls:

```text
Tab        → next candidate
Shift+Tab  → previous candidate
```

The currently active mask updates immediately.

This is preferable to forcing the model's top-ranked candidate when multiple interpretations are reasonable.

---

## 7.7 Prompt editing

Prompts are persistent UI objects.

A prompt should be:

- selectable,
- movable,
- deletable.

Suggested behavior:

```text
click marker       → select
drag marker        → move
Delete / Backspace → delete selected prompt
Ctrl+Z             → undo
Ctrl+Shift+Z       → redo
```

Moving a prompt triggers a new segmentation prediction.

A small contextual `×` may also be displayed near a selected prompt.

---

## 7.8 Undo / redo

All meaningful session mutations should be undoable.

Examples:

- adding prompt,
- removing prompt,
- moving prompt,
- adding box,
- removing box,
- changing candidate selection,
- adding future lasso prompt.

Undo/redo should operate on session state rather than manually reversing widget actions.

---

## 7.9 Mask visualization

The selected mask should remain visually obvious without hiding the original content.

Potential rendering:

- translucent filled overlay,
- crisp mask boundary,
- slight dimming outside selection.

A useful default might be:

```text
selected object   → normal brightness + translucent mask tint
everything else   → slightly dimmed
boundary          → visible outline
```

The mask overlay should update without rebuilding the entire UI scene.

---

## 7.10 Export

Primary export operation:

```text
Enter
→ create RGBA cutout
→ place image on clipboard
→ close capture overlay
```

Secondary export:

```text
Ctrl+S
→ save transparent PNG
```

The alpha channel is derived from the segmentation mask.

Later versions may support:

- mask-only export,
- original crop + mask,
- feathered alpha,
- trim transparent borders.

---

# 8. Minimal Toolbar

The overlay should contain a compact floating toolbar.

Conceptual layout:

```text
╭──────────────────────────────────────────────╮
│ + Include  − Exclude  □ Box  ◯ Lasso        │
│                                              │
│ Undo  Redo               Copy  Save  Cancel  │
╰──────────────────────────────────────────────╯
```

The toolbar should be draggable.

For MVP, it can contain only:

```text
Include
Exclude
Box
Undo
Redo
Copy
Save
Cancel
```

Lasso is a later milestone.

---

# 9. Keyboard Interaction

Initial candidate shortcuts:

```text
1                Include point
2                Exclude point
3                Box

Tab              Next mask candidate
Shift+Tab        Previous mask candidate

Ctrl+Z           Undo
Ctrl+Shift+Z     Redo

Enter            Copy object to clipboard
Ctrl+S           Save PNG
Esc              Cancel / exit capture
Delete           Delete selected prompt
```

Shortcuts are provisional and should be evaluated in use.

The most important shortcut is the global capture shortcut.

---

# 10. Future Interaction Modes

## 10.1 Loose lasso

The user quickly circles an object.

Meaning:

> The target object is somewhere inside this approximate region.

The lasso should not initially be interpreted as a pixel-perfect manual mask.

Possible implementations include:

### Strategy A: derive prompt points

Convert the lasso to:

- bounding box,
- sampled positive points inside,
- sampled negative points immediately outside.

### Strategy B: spatial constraint

Run the normal segmentation prediction and suppress masks substantially outside the lasso region.

### Strategy C: model-native dense prompt

If a future segmentation backend accepts masks or dense prompts, rasterize the lasso into that representation.

This should remain backend-independent at the session/UI layer.

---

## 10.2 Hard lasso

A future manual mode may allow the user to say:

> Use exactly this enclosed area.

This provides a model-independent fallback.

---

## 10.3 Text prompt

Example:

```text
"glasses"
"pants"
"red backpack"
```

This is not a core segmentation feature.

It likely requires an open-vocabulary grounding or detection model:

```text
text
 ↓
open-vocabulary detector / grounding model
 ↓
bounding boxes
 ↓
promptable segmentation model
 ↓
mask candidates
```

Text prompting is explicitly outside the initial MVP.

---

## 10.4 Semantic actions

Possible future actions after object selection:

- blur selected object,
- blur everything except selected object,
- remove selected object,
- inpaint selected region,
- copy mask,
- copy object,
- redact similar objects,
- select all similar objects.

These should not be implemented until the core snipping workflow is mature.

---

# 11. State Model

The active capture should be represented explicitly.

Conceptual model:

```text
CaptureSession
├── screenshot
├── display_context
├── prompts
│   ├── positive_points[]
│   ├── negative_points[]
│   ├── box_prompt?
│   └── future_lasso?
├── segmentation_result
│   ├── candidate_masks[]
│   └── candidate_scores[]
├── active_candidate_index
├── active_tool
├── selected_prompt_id
└── history
```

The session is the authoritative state of an active capture.

Widgets render session state.

Widgets should not become the authoritative storage for prompts.

---

# 12. Prompt Data Model

A prompt should be represented independently from Qt.

Example conceptual structures:

```python
@dataclass(frozen=True)
class PointPrompt:
    id: UUID
    position: ImagePoint
    kind: Literal["positive", "negative"]
```

```python
@dataclass(frozen=True)
class BoxPrompt:
    id: UUID
    top_left: ImagePoint
    bottom_right: ImagePoint
```

A container can expose:

```python
@dataclass(frozen=True)
class PromptSet:
    points: tuple[PointPrompt, ...]
    boxes: tuple[BoxPrompt, ...]
```

Immutability is attractive for history management because state snapshots become easy to reason about.

Exact implementation may change.

---

# 13. Coordinate Systems

Coordinate handling must be treated as a first-class architectural concern.

At minimum, the application may encounter:

1. global desktop coordinates,
2. Qt logical coordinates,
3. screen-local coordinates,
4. screenshot pixel coordinates,
5. model-input coordinates,
6. model-output mask coordinates.

High-DPI displays can cause:

```text
1 Qt logical pixel != 1 screenshot pixel
```

Multi-monitor configurations can introduce:

- negative global coordinates,
- different monitor scales,
- different resolutions,
- different device pixel ratios.

All coordinate transformations must pass through a dedicated coordinate abstraction.

Do not scatter scaling arithmetic throughout UI event handlers.

Example conceptual API:

```python
screen_to_image(point)
image_to_screen(point)

image_to_model(point)
model_to_image(mask)

global_to_screen(point)
screen_to_global(point)
```

Coordinate conversion should have dedicated tests from the beginning.

---

# 14. High-Level Architecture

```text
                 ┌──────────────────────┐
                 │     Application      │
                 │ lifecycle / shortcut │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │       Capture        │
                 │ screen acquisition   │
                 │ display geometry     │
                 └──────────┬───────────┘
                            │
                       Screenshot
                            │
                            ▼
                 ┌──────────────────────┐
                 │   Capture Session    │
                 │ prompts / state      │
                 │ history / candidates │
                 └───────┬──────┬───────┘
                         │      │
              prompts    │      │ state
                         ▼      ▼
              ┌────────────┐  ┌──────────────┐
              │Segmentation│  │      UI      │
              │  backend   │  │ overlay/tools│
              └────────────┘  └──────────────┘
                         │
                         ▼
                 ┌──────────────────────┐
                 │        Export        │
                 │ clipboard / PNG      │
                 └──────────────────────┘
```

---

# 15. Architectural Boundaries

## 15.1 Application layer

Responsibilities:

- startup,
- shutdown,
- configuration,
- model initialization,
- global shortcut lifecycle,
- entering capture mode,
- leaving capture mode.

Should not:

- implement segmentation algorithms,
- draw masks,
- perform coordinate math directly.

---

## 15.2 Capture layer

Responsibilities:

- enumerate displays,
- capture screenshot pixels,
- represent display geometry,
- handle DPI metadata,
- map screen coordinates to screenshot coordinates.

Should not:

- know about segmentation models,
- know about prompt semantics,
- manage clipboard export.

---

## 15.3 Session layer

Responsibilities:

- active prompts,
- current tool,
- active mask candidate,
- undo/redo,
- authoritative capture state.

The session coordinates changes between UI and segmentation.

It should not depend directly on Qt widgets.

---

## 15.4 Segmentation layer

Responsibilities:

- load model,
- set screenshot/image,
- cache image representation where supported,
- convert prompts to model format,
- predict masks,
- return candidate masks and confidence scores.

Should not:

- know about Qt,
- manage screen capture,
- draw overlays,
- write to clipboard.

---

## 15.5 UI layer

Responsibilities:

- fullscreen overlay,
- screenshot rendering,
- toolbar,
- mask rendering,
- prompt rendering,
- pointer interaction,
- keyboard shortcuts,
- drag behavior.

The UI communicates intent to the session.

The UI should not contain model-specific tensor transformations.

---

## 15.6 Export layer

Responsibilities:

- apply mask to screenshot,
- construct RGBA image,
- trim or preserve bounds,
- write PNG,
- populate system clipboard.

Should not:

- invoke segmentation,
- manage application state.

---

# 16. Proposed Repository Layout

```text
objectsnip/
│
├── README.md
├── DESIGN.md
├── pyproject.toml
├── LICENSE
├── .gitignore
│
├── src/
│   └── objectsnip/
│       │
│       ├── __init__.py
│       ├── __main__.py
│       ├── app.py
│       ├── config.py
│       ├── shortcuts.py
│       │
│       ├── capture/
│       │   ├── __init__.py
│       │   ├── screen_capture.py
│       │   ├── displays.py
│       │   └── coordinates.py
│       │
│       ├── session/
│       │   ├── __init__.py
│       │   ├── capture_session.py
│       │   ├── prompts.py
│       │   ├── state.py
│       │   └── history.py
│       │
│       ├── segmentation/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── result.py
│       │   └── models/
│       │       ├── __init__.py
│       │       ├── mobile_sam.py
│       │       └── sam2.py
│       │
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── overlay.py
│       │   ├── canvas.py
│       │   ├── toolbar.py
│       │   ├── mask_item.py
│       │   ├── prompt_items.py
│       │   └── tools/
│       │       ├── __init__.py
│       │       ├── include_tool.py
│       │       ├── exclude_tool.py
│       │       └── box_tool.py
│       │
│       └── export/
│           ├── __init__.py
│           ├── clipboard.py
│           └── image_export.py
│
├── tests/
│   ├── test_coordinates.py
│   ├── test_prompts.py
│   ├── test_history.py
│   ├── test_session.py
│   └── test_export.py
│
├── benchmarks/
│   ├── README.md
│   └── segmentation_models.py
│
├── scripts/
│   └── download_models.py
│
└── assets/
    └── icons/
```

This structure is a starting point, not a rigid requirement.

Files should be added only when they represent a clear responsibility.

Avoid splitting trivial code into excessive modules purely to match this tree.

---

# 17. Segmentation Abstraction

The rest of the application should not depend on SAM-specific APIs.

A minimal conceptual protocol:

```python
class Segmenter(Protocol):
    def load(self) -> None:
        ...

    def set_image(self, image: np.ndarray) -> None:
        ...

    def predict(self, prompts: PromptSet) -> SegmentationResult:
        ...
```

Potential extension:

```python
class Segmenter(Protocol):
    @property
    def capabilities(self) -> SegmenterCapabilities:
        ...
```

Capabilities may include:

```text
positive_points
negative_points
boxes
multiple_candidates
dense_masks
text_prompts
```

This allows the UI to adapt to different backends in the future.

---

# 18. Segmentation Result

Conceptual structure:

```python
@dataclass
class SegmentationResult:
    masks: list[np.ndarray]
    scores: list[float]
```

Constraints:

- masks should be returned in screenshot/image coordinates,
- backend-specific tensor types should not escape the segmentation layer,
- the mask representation should be consistent across backends,
- candidate ordering should correspond to score ordering when meaningful.

Potential future metadata:

```text
inference_time_ms
backend_name
raw_score
stability_score
```

---

# 19. Model Strategy

ObjectSnip requires a model optimized for:

- static images,
- positive point prompts,
- negative point prompts,
- box prompts,
- fast prompt refinement,
- local inference,
- consumer hardware,
- good object boundaries.

Video support is not initially relevant.

Candidate model families include:

- MobileSAM,
- SAM 2 Tiny,
- other lightweight promptable segmentation models.

The architecture must not assume the first tested model is the final model.

---

# 20. Model Benchmarking

Model selection should be empirical.

The project should contain a small benchmark suite using representative screenshot targets.

Example target categories:

- person,
- face,
- clothing,
- glasses,
- chair,
- cup,
- icon,
- UI panel,
- product image,
- diagram component,
- small object,
- partially occluded object,
- low-contrast object.

Measure:

```text
model load time
image encoding time
first prediction latency
refinement latency
peak memory
CPU latency
CUDA latency
mask quality
failure cases
```

The distinction between first prediction and refinement is critical.

For models that cache image features:

```text
T_first =
    T_image_encoding
    +
    T_prompt_decode
```

while:

```text
T_refinement ≈
    T_prompt_decode
```

For this product, refinement latency strongly affects perceived quality.

---

# 21. Performance Targets

Initial targets are aspirational and should be revised after benchmarking.

### Prompt refinement

Preferred:

```text
< 100 ms
```

Acceptable early prototype:

```text
< 300 ms
```

Above approximately 500 ms may begin to feel disruptive during repeated refinement.

### Initial screenshot encoding

Preferred:

```text
< 1 second
```

A slightly slower first result may be acceptable if all subsequent interactions are fast.

### Overlay rendering

The GUI should remain responsive while inference occurs.

Long-running model operations must not block the main Qt event loop.

---

# 22. Concurrency

Inference should not freeze UI rendering.

Likely approach:

```text
Qt main thread
    │
    ├── input
    ├── rendering
    └── session events

worker thread / executor
    │
    └── segmentation inference
```

Important issue:

A user may move prompts faster than predictions complete.

Therefore prediction requests should carry a session revision number.

Example:

```text
revision 14 → prediction starts
revision 15 → user moves point
revision 15 → prediction starts
revision 14 → result returns late
```

Revision 14 must be discarded.

Only the result corresponding to the newest applicable session state should be displayed.

This prevents stale masks from appearing after fast interaction.

---

# 23. Prediction Debouncing

Dragging a point may generate many mouse-move events.

The application should avoid queueing one inference request for every pixel of movement.

Possible strategy:

- update marker visually every frame,
- debounce segmentation prediction,
- run prediction after a short delay,
- or run at a capped interactive frequency.

Example:

```text
drag marker
→ render marker immediately
→ predict at maximum ~10–20 Hz
→ final prediction on release
```

Exact behavior depends on model speed.

---

# 24. Model Loading

Model loading should not occur every time capture mode opens.

Preferred lifecycle:

```text
application starts
→ initialize or lazily load backend once
→ reuse backend for all captures
```

Potential compromise:

- application starts lightweight,
- model loads on first invocation,
- model remains resident afterward.

This should be benchmarked because startup latency and memory consumption may conflict.

---

# 25. Screen Capture Strategy

For the initial prototype, use Qt screen APIs where possible.

General approach:

```text
global shortcut
→ capture target screen
→ instantiate fullscreen frameless overlay
→ display captured pixels
```

The screen is not literally frozen.

The application creates a fullscreen window containing a screenshot of the previous desktop state.

This is sufficient to create the expected screenshot-tool interaction model.

---

# 26. Multi-Monitor Support

Multi-monitor support is important but not required for the earliest model/UI prototype.

Potential future strategies:

### Strategy A: capture active monitor only

Simplest behavior.

### Strategy B: one overlay per display

Each screen receives its own fullscreen screenshot window.

### Strategy C: virtual desktop canvas

Compose all monitors into one logical image and map global coordinates.

Strategy B may be easier to reason about while preserving per-monitor DPI.

This decision should be postponed until the single-screen workflow works.

---

# 27. Global Shortcut

A native-feeling screenshot tool requires a global shortcut.

This is one of the areas most likely to require platform-specific handling.

Initial Linux development can choose the simplest workable approach.

The architecture should isolate shortcut registration behind a small interface so platform-specific implementations can be added later.

Example conceptual API:

```python
class GlobalShortcutService:
    def register_capture_shortcut(self, callback) -> None:
        ...

    def unregister_all(self) -> None:
        ...
```

The rest of the application should not care how the shortcut is implemented.

---

# 28. Platform Strategy

## Phase 1

Primary development:

```text
Linux
```

Goal:

- prove interaction,
- prove segmentation,
- prove screen capture,
- prove clipboard export.

## Phase 2

Improve Linux desktop compatibility.

Potential issues:

- X11 vs Wayland,
- global shortcuts,
- screenshot permissions,
- desktop portal behavior,
- multiple monitors,
- fractional scaling.

## Phase 3

Evaluate:

- Windows,
- macOS.

Cross-platform support is desirable but should not delay proving the product.

---

# 29. Wayland Considerations

Linux desktop screenshot and global-input behavior may differ significantly between X11 and Wayland.

This is one of the main expected platform-specific risks.

The project should avoid allowing Linux integration complexity to block early progress.

A practical development strategy is:

1. build the segmentation UI first using ordinary image files,
2. add fullscreen frozen-image interaction,
3. integrate real screen capture,
4. then solve Wayland-specific capture/shortcut issues.

This ensures that OS integration is not mixed with model debugging.

---

# 30. Export Pipeline

Given:

```text
RGB screenshot I
binary/soft mask M
```

construct:

```text
RGBA = [I, alpha(M)]
```

Potential alpha strategies:

### Binary mask

```text
alpha ∈ {0, 255}
```

Simple but potentially harsh edges.

### Soft mask

If model output exposes suitable probabilities:

```text
alpha ∈ [0, 255]
```

May preserve anti-aliased boundaries.

### Feathered mask

Apply a small boundary operation to produce visually smoother cutouts.

This should be optional and tested carefully to avoid halos.

---

# 31. Transparent Bounds

The exported image may either:

### Preserve full screenshot dimensions

Useful in niche workflows, but wastes space.

### Crop to mask bounds

Preferred default.

Compute the smallest bounding rectangle containing non-transparent pixels and export only that region.

Optional padding may be added.

---

# 32. Clipboard

The clipboard is a core feature, not an afterthought.

The goal is:

```text
ObjectSnip
→ Enter
→ switch to another application
→ Ctrl+V
```

The clipboard implementation should preserve alpha transparency where supported.

Clipboard behavior should be tested with:

- LibreOffice Impress,
- PowerPoint where available,
- browsers,
- image editors,
- chat applications,
- file managers.

---

# 33. Error Handling

Expected user-facing error cases:

- model failed to load,
- screenshot capture failed,
- GPU unavailable,
- out of memory,
- no valid mask,
- clipboard operation failed,
- save operation failed.

Error UI should remain concise.

Avoid exposing raw stack traces in the overlay.

Developer logs may contain detailed diagnostics.

---

# 34. Configuration

Initial configuration should be minimal.

Potential settings:

```text
global shortcut
preferred model
compute device
default export behavior
mask overlay opacity
copy vs save default
```

Avoid building a settings system before the core workflow is functional.

---

# 35. Logging

Use structured Python logging.

Potential logging categories:

```text
application lifecycle
capture
segmentation backend
inference latency
coordinate mapping
export
errors
```

Do not log screenshot pixel data or sensitive image contents.

---

# 36. Testing Strategy

The project contains both deterministic application logic and difficult-to-test GUI/model behavior.

Testing should focus heavily on deterministic boundaries.

---

## 36.1 Unit tests

High-value unit tests:

### Coordinates

- logical → image mapping,
- image → logical mapping,
- device pixel ratios,
- monitor offsets,
- round-trip transforms.

### Prompts

- add,
- delete,
- move,
- positive/negative typing,
- serialization if introduced.

### History

- undo,
- redo,
- branching after undo,
- prompt movement,
- candidate changes.

### Export

- mask application,
- alpha channel,
- cropping,
- empty mask handling,
- edge pixels.

### Session

- revision numbers,
- stale result rejection,
- tool switching,
- candidate cycling.

---

## 36.2 Integration tests

Potential integration tests:

- fake segmenter + real session,
- screenshot image + fake UI events,
- clipboard export using controlled image,
- asynchronous predictions returning out of order.

A fake segmenter should be available for UI development.

Example:

```python
class FakeSegmenter:
    def predict(self, prompts):
        return deterministic_test_mask(...)
```

This allows GUI work without loading a neural network.

---

## 36.3 Model evaluation tests

Model quality should not be mixed with normal unit tests.

Maintain a small manually curated evaluation set.

Evaluate:

- first-click mask,
- one-refinement mask,
- difficult edge cases,
- ambiguous targets.

The benchmark should produce both numerical and visual output.

---

# 37. Development Sequence

The project should deliberately separate product risks.

There are three major risks:

1. interactive segmentation quality,
2. interactive GUI quality,
3. OS-level screenshot integration.

Do not solve all three simultaneously.

---

# 38. Milestones

## 0.1 — Interactive segmentation sandbox

Run in a normal application window.

Features:

- open a local image,
- positive points,
- negative points,
- move prompts,
- delete prompts,
- candidate masks,
- mask overlay,
- model abstraction.

Purpose:

> prove the segmentation interaction without screenshot integration.

---

## 0.2 — Frozen screen mode

Features:

- capture one monitor,
- show screenshot fullscreen,
- interact with screenshot,
- exit with Escape.

Purpose:

> prove that the application can feel like a screenshot utility.

---

## 0.3 — Useful daily utility

Features:

- global shortcut,
- positive points,
- negative points,
- box prompt,
- candidate cycling,
- copy transparent cutout,
- save PNG,
- draggable toolbar,
- undo/redo.

At this milestone, the project should be useful enough for the developer to leave installed.

---

## 0.4 — Selection quality

Features considered:

- loose lasso,
- edge refinement,
- mask feathering,
- better candidate navigation,
- better object-bound trimming,
- model benchmark results.

---

## 0.5 — Platform robustness

Features:

- multi-monitor support,
- DPI correctness,
- device selection,
- CPU fallback,
- GPU acceleration,
- packaging,
- settings,
- error recovery.

---

## 1.0 — Stable core utility

Requirements:

- reliably usable on the primary supported platform,
- installable,
- documented,
- sensible model download/setup,
- robust clipboard behavior,
- no major coordinate bugs,
- acceptable inference latency,
- tested core workflow.

---

# 39. MVP Definition

The MVP is intentionally narrow.

A valid MVP must allow:

1. launch application,
2. trigger screen capture,
3. capture one monitor,
4. display a fullscreen frozen screenshot,
5. add positive points,
6. add negative points,
7. produce a segmentation mask,
8. move existing points,
9. delete existing points,
10. update the mask after edits,
11. copy transparent object with Enter,
12. cancel with Escape.

Optional in MVP:

- box prompt,
- candidate cycling.

Everything else is non-MVP.

---

# 40. Explicit Non-Goals for MVP

Do not implement these unless the project scope is deliberately revised:

- OCR,
- image annotations,
- arrows,
- text boxes,
- screen recording,
- cloud inference,
- accounts,
- collaboration,
- browser extension,
- inpainting,
- object removal,
- background generation,
- text prompts,
- object detection,
- semantic search,
- image history,
- upload service,
- social sharing,
- multi-object composition,
- automatic software updates,
- polished cross-platform installers,
- full macOS support,
- full Windows support.

The existence of a possible feature does not justify adding it.

---

# 41. Dependencies

Initial likely dependencies:

```text
Python
PySide6
NumPy
Pillow and/or OpenCV
PyTorch
chosen segmentation model package/code
```

Potential optional dependencies:

```text
onnxruntime
opencv-python
safetensors
huggingface_hub
```

Dependencies should be added only when required.

Avoid adding a large framework for a small utility function.

---

# 42. PyTorch vs ONNX

Initial development should prioritize correctness and iteration speed.

PyTorch is likely the simplest first backend.

Later, ONNX may be evaluated for:

- easier CPU inference,
- reduced deployment complexity,
- cross-platform performance,
- smaller runtime footprint.

The segmentation abstraction should make this migration possible without changing UI or session logic.

---

# 43. Packaging

Packaging is not an early milestone.

Potential later options include:

- PyInstaller,
- Nuitka,
- platform-native packaging,
- Flatpak for Linux.

Model weights may be:

- bundled,
- downloaded on first run,
- installed separately.

Bundling very large model files may make application distribution impractical.

The model-management strategy should be decided after benchmarking model sizes.

---

# 44. Security and Privacy

Core privacy rule:

> screenshots remain local unless the user explicitly chooses otherwise in a future feature.

The application should not include telemetry by default.

If crash reporting is ever added, image data must never be attached automatically.

Clipboard contents should only be written as a result of explicit user action.

---

# 45. Accessibility

Potential considerations:

- keyboard-only prompt management,
- configurable shortcuts,
- mask colors that remain distinguishable under color-vision deficiencies,
- scalable toolbar,
- high-DPI rendering,
- visible focus state.

These are not necessarily MVP blockers but should influence UI design.

---

# 46. Open Design Questions

These decisions should be revisited after prototypes.

## 46.1 Working name

Current working name:

```text
ObjectSnip
```

Repository:

```text
objectsnip
```

The final name should be checked for:

- GitHub collisions,
- PyPI collisions,
- discoverability,
- trademark concerns,
- general searchability.

---

## 46.2 Initial segmentation backend

Candidates:

- MobileSAM,
- SAM 2 Tiny,
- another lightweight promptable model.

Decision criterion:

> best quality/latency tradeoff for screenshot object extraction.

---

## 46.3 Default mask candidate behavior

Possible behavior:

- display highest-scoring candidate,
- preserve all candidates,
- allow Tab cycling.

Need to test whether candidate cycling is intuitive enough to justify always exposing it.

---

## 46.4 Box semantics

Questions:

- allow one box only?
- allow multiple boxes?
- does adding a box reset previous point prompts?
- can points exist outside a box?
- should the box be editable after creation?

Likely initial answer:

> one editable box + arbitrary point prompts.

---

## 46.5 Prompt deletion interaction

Candidates:

- select + Delete,
- contextual X,
- right-click menu,
- both keyboard and contextual X.

Likely:

> keyboard first, small X for discoverability.

---

## 46.6 Model initialization

Options:

- load at application startup,
- load on first screenshot,
- preload image encoder lazily.

Benchmark before deciding.

---

## 46.7 Overlay architecture

Potential Qt approaches:

- QGraphicsScene/QGraphicsView,
- custom QWidget painting,
- QML/Qt Quick.

Initial recommendation:

> use the simplest architecture that supports smooth prompt dragging and mask overlays.

QGraphicsScene may naturally suit draggable prompt objects, but a custom painted widget may result in less framework complexity.

Prototype before committing.

---

# 47. Design Decisions Already Made

The following should be considered deliberate unless evidence suggests revisiting them:

### D1. Desktop application, not hosted website

Reason:

- screen integration,
- local inference,
- privacy,
- clipboard workflow.

### D2. PySide6 / Qt for initial UI

Reason:

- desktop-native interaction,
- cross-platform potential,
- custom overlay support,
- clipboard/screen APIs.

### D3. Python-first implementation

Reason:

- CV ecosystem,
- PyTorch model integration,
- rapid iteration.

### D4. Segmentation backend behind an interface

Reason:

- model landscape evolves rapidly,
- model choice requires benchmarking.

### D5. Editable user prompts

Reason:

- ambiguity is inherent to segmentation,
- correction is the project's primary interaction advantage.

### D6. Local inference

Reason:

- privacy,
- latency,
- cost,
- simplicity.

### D7. No generic image-editor scope

Reason:

- preserve focus and finishability.

---

# 48. Architectural Invariants

These are stronger than ordinary recommendations.

New implementation work should preserve them unless DESIGN.md is revised.

1. Qt-specific types do not enter the segmentation layer.
2. Model-specific tensor types do not enter the UI layer.
3. Coordinate conversion is centralized.
4. CaptureSession is authoritative during an active capture.
5. Segmentation backends implement a common interface.
6. Image encoding should be reused across prompt refinements where the backend supports it.
7. The GUI event loop must not be blocked by long inference operations.
8. Stale asynchronous model results must never overwrite newer state.
9. Export logic does not belong in rendering widgets.
10. Future features do not enter MVP implementation accidentally.

---

# 49. Suggested Codex Workflow

Before implementing a milestone, Codex should:

1. read this document,
2. inspect current repository structure,
3. identify the milestone being implemented,
4. avoid implementing later milestones,
5. preserve architectural invariants,
6. state any proposed architectural deviation before making it,
7. add tests for deterministic logic,
8. keep model-specific logic isolated.

Suggested initial Codex instruction:

```text
Read DESIGN.md fully.

Implement milestone 0.1 only: the interactive segmentation sandbox.

Do not implement screenshot capture, global shortcuts, packaging, text prompting,
lasso selection, or later milestones.

Preserve the architectural boundaries defined in DESIGN.md.

Before coding, inspect the repository and briefly describe the concrete modules you
intend to create or modify. If you believe the architecture needs to deviate from
DESIGN.md, explain why before making that deviation.
```

---

# 50. Milestone 0.1 Acceptance Criteria

Milestone 0.1 is complete when:

- the application opens a normal Qt window,
- the user can load an image,
- the image is encoded by a segmentation backend,
- left-click can create a positive prompt,
- the user can switch to negative prompt mode,
- prompts are visibly rendered,
- prompts can be moved,
- prompts can be deleted,
- predictions update after prompt edits,
- a selected mask is rendered transparently over the image,
- multiple mask candidates are supported if the backend provides them,
- the UI remains responsive during inference,
- segmentation logic is isolated from Qt,
- coordinate transformations have tests,
- prompt/session state has tests.

---

# 51. Definition of Done for the Project

ObjectSnip should eventually be considered successful when a user can:

1. install it,
2. configure a shortcut,
3. see any object on screen,
4. invoke ObjectSnip,
5. select the object with one click in easy cases,
6. refine ambiguous cases without frustration,
7. press Enter,
8. paste a clean transparent cutout into another application.

The product succeeds if this workflow is meaningfully faster than:

```text
screenshot
→ crop
→ background-removal tool
→ fix
→ download/copy
→ paste
```

The technical sophistication is valuable only insofar as it makes that interaction reliable.

---

# 52. Long-Term Possibilities

These ideas are intentionally deferred.

They should be treated as separate product decisions rather than inevitable roadmap items.

## Semantic selection

```text
type "glasses"
→ select glasses
```

## Select similar

```text
select one object
→ find all visually similar objects
```

## Semantic redaction

```text
select one username
→ blur similar/private elements
```

## Object removal

```text
select object
→ remove
→ local inpainting
```

## Screen object history

Store recently extracted objects locally.

## Smart export

Recognize destination/application and optimize:

- alpha,
- resolution,
- padding,
- file format.

## Multi-object composition

Select several independent masks before copying.

## Alternative segmentation backends

Allow models optimized for:

- CPU,
- GPU,
- small objects,
- people,
- UI elements.

---

# 53. Final Product Heuristic

When deciding whether to add a feature, ask:

> Does this make it faster or easier to select and extract a visual object from the screen?

If the answer is no, it probably belongs in another application.

ObjectSnip should remain a small, focused utility with unusually good object-selection interaction.
