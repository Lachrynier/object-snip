# Object selection

**Status:** Draft  
**First milestone:** 0.2

This document owns user-visible selection behavior: tools, prompts, candidate
masks, editing, visualization, and selection-related shortcuts. It does not own
screen acquisition or output behavior.

## Goal

Let a user indicate an object with a minimal prompt, inspect the proposed mask,
and correct ambiguity through direct edits.

The common case should be one positive point followed by confirmation. The 0.2
segmentation milestone stops after producing and displaying the selection;
confirmation and
output are specified in [`export.md`](export.md).

## 0.2 user flow

1. Selection receives the locked context crop from capture.
2. The workspace displays the crop immediately while encoding it in the
   background.
3. User clicks the desired object in Include mode once encoding is ready.
4. An include marker appears immediately and prediction starts asynchronously.
5. The newest valid mask is displayed over the image.
6. If necessary, the user adds an exclude point, moves or deletes a point, or
   selects another candidate.

While encoding is pending, the image remains visible beneath a translucent
`Preparing image…` state and prompt input is unavailable. An encoding failure
offers Retry. Closing or replacing the workspace invalidates pending results.

## Behavior

“Implemented” describes the current code. Planned entries remain Draft product
behavior and should not be presented as available controls.

| Input or event | Intended result | Status |
|---|---|---|
| Receive locked context crop | Reset prompt state and encode the crop | Implemented |
| Left click in Positive mode | Add a positive point at the corresponding crop position | Implemented |
| Left click in Negative mode | Add a negative point at the corresponding crop position | Implemented |
| Click an existing marker | Remove that prompt | Implemented |
| Select and drag a point | Move it visually and request updated predictions | Planned for 0.2 |
| `Delete` or `Backspace` | Remove the selected prompt | Planned for 0.2 |
| `1` / `2` | Activate Positive / Negative mode | Planned for 0.2 |
| Mouse wheel over image | Zoom toward or away from the image point under the cursor | Implemented |
| Drag with Pan active | Move the zoomed image within the viewport | Implemented |
| Middle-button drag | Temporarily pan without changing the toolbar tool | Implemented |
| Reset zoom toolbar action | Return to the centered fit-to-window view | Implemented |
| Mask toolbar action | Display the selected candidate | Implemented |
| `Tab` / `Shift+Tab` | Select next / previous mask candidate | Optional Draft |
| `Ctrl+Z` / `Ctrl+Shift+Z` | Undo / redo a session mutation | Planned for 0.3 |
| Drag in Box mode | Create or replace an editable approximate box prompt | Planned for 0.3 |
| `3` | Activate Box mode | Planned for 0.3 |

No output shortcut is defined here. Confirmation, copy, and save are owned by
`export.md`; overlay cancellation is owned by `capture.md`.

## Prompt rules

- Include means “this position belongs to the desired object.”
- Exclude means “this position does not belong to the desired object.”
- Prompts persist until explicitly edited, deleted, undone, or the image/session
  is replaced.
- A point is visibly typed as positive or negative and can be removed by
  clicking its marker. Selection and dragging remain planned.
- Prompt positions are stored in image coordinates, independent of view zoom or
  Qt widget coordinates.
- Zooming keeps the image point beneath the cursor stationary in the viewport;
  zooming out applies the reciprocal transform. Prompt markers retain a constant
  screen-space size at every zoom level.
- At fit-to-window zoom, the centered image bounds form the viewport. As the
  image is enlarged, the viewport expands with it into the letterboxed area,
  up to the full window below the toolbar. Panning cannot reveal background
  within the viewport.
- Middle-button panning is independent of the persistent Pan toolbar action, and
  wheel zoom remains available during either pan gesture.
- Any prompt-set mutation advances the session prediction revision.
- Only a result for the current applicable revision may replace the visible
  mask.

## Mask presentation

The toolbar offers five inspection views without changing the active mask,
prompts, zoom, pan, or exported result:

- **Overlay** shows the source image with the mask filled using the selected
  color and opacity.
- **Mask** shows included pixels as white and excluded pixels as black.
- **Cutout** shows the minimal export bounding box over a checkerboard
  transparency grid, with the rest of the full image coordinate frame darkened.
- **Outline** shows the source image with a translucent colored interior and a
  solid outline in the same base color. Opacity applies to the interior only.
- **Excluded** leaves selected pixels unchanged and dims excluded pixels using
  the selected color and opacity, without an outline.

The mask color is chosen from a compact preset palette and is also used by the
active candidate button. Opacity is available for Overlay, Outline, and Excluded
and remains visible but disabled in Mask and Cutout views. The opacity label is
centered above its slider inside a single framed control. An open-eye/closed-eye
toolbar toggle controls prompt-marker visibility in every view without changing
or removing the prompts. The selection window opens maximized with normal window
controls.

Mask rendering updates from the returned mask without reconstructing the whole
UI scene. The visible candidate is session state, not state held only by a
painted item.

## Candidate masks

When the backend returns multiple candidates, rank them by score and display the
highest-scoring candidate initially. Toolbar controls select any returned mask.
The active candidate's low-resolution logits are passed into the next prediction
as refinement state.

Changing a candidate does not require a new model prediction.

## Responsiveness

- Model work does not run on the GUI event loop.
- A marker follows pointer movement immediately.
- Prediction during dragging may be debounced or rate-limited.
- Releasing a dragged prompt requests a final prediction.
- An older result never flashes over a newer prompt state.

Numeric latency targets belong in benchmark results until measurements support
a product requirement.

## 0.2 acceptance criteria

- [x] A locked context crop can be encoded and displayed for selection through
      the real SAM 2.1 backend or deterministic fake.
- [x] Include and exclude points can be added and are visually distinct.
- [x] Existing points can be deleted by clicking their marker.
- [ ] Existing points can be selected and moved.
- [x] Each committed prompt edit requests prediction for the new revision.
- [x] A backend-neutral segmentation result can contain one or more masks.
- [x] The highest-scoring mask is displayed transparently over the image.
- [x] Candidate selection works when a backend provides multiple candidates.
- [ ] The UI stays responsive while prediction is running.
- [x] Out-of-order prediction completion cannot display a stale result.
- [x] View/image coordinate transformations have deterministic tests.
- [ ] Prompt and session transitions have deterministic tests.
- [x] UI/session development can run with a deterministic fake segmenter.
- [x] At least one real promptable backend works through the same interface.

## Open decisions

- Is candidate cycling intuitive enough to remain visible in the core product?
- Should prompt movement create one history item per drag or per prediction?
- Is explicit Exclude mode preferable to a modifier-click shortcut?
- Is history needed in 0.2 to validate the state design, or can it wait for 0.3?
- For the later Box tool: one box or multiple; may points exist outside it; does
  adding it preserve existing points?
- QGraphicsView/custom QWidget/Qt Quick should be decided through the smallest
  interaction prototype rather than this specification.

## Deferred selection modes

Loose lasso, exact manual lasso, text prompts, automatic detection, multi-object
selection, and hard mask painting are outside 0.2–0.3 unless deliberately
promoted through the product and roadmap documents.
