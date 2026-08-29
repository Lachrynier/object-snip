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

All entries are Draft until reviewed.

| Input or event | Intended result | Milestone |
|---|---|---|
| Receive locked context crop | Reset prompt/history state and encode the crop | 0.2 |
| Left click in Include mode | Add a positive point at the corresponding crop position | 0.2 |
| Left click in Exclude mode | Add a negative point at the corresponding crop position | 0.2 |
| Select and drag a point | Move it visually; request updated predictions without blocking input | 0.2 |
| `Delete` or `Backspace` | Remove the selected prompt | 0.2 |
| `1` | Activate Include mode | 0.2 |
| `2` | Activate Exclude mode | 0.2 |
| Mouse wheel over image | Zoom toward or away from the image point under the cursor | 0.2 |
| Drag with Pan tool active | Move the zoomed image within the viewport | 0.2 |
| Middle-button drag | Temporarily pan without changing the active toolbar tool | 0.2 |
| Reset zoom toolbar action | Return to the centered fit-to-window view | 0.2 |
| `Tab` / `Shift+Tab` | Select next / previous mask candidate when available | 0.2, optional pending evaluation |
| `Ctrl+Z` / `Ctrl+Shift+Z` | Undo / redo a session mutation | 0.3 unless promoted |
| Drag in Box mode | Create or replace an editable approximate box prompt | 0.3, Draft |
| `3` | Activate Box mode | 0.3, Draft |

No output shortcut is defined here. Confirmation, copy, and save are owned by
`export.md`; overlay cancellation is owned by `capture.md`.

## Prompt rules

- Include means “this position belongs to the desired object.”
- Exclude means “this position does not belong to the desired object.”
- Prompts persist until explicitly edited, deleted, undone, or the image/session
  is replaced.
- A point is visibly typed as include or exclude, selectable, movable, and
  deletable.
- Prompt positions are stored in image coordinates, independent of view zoom or
  Qt widget coordinates.
- Zooming keeps the image point beneath the cursor stationary in the viewport;
  zooming out applies the reciprocal transform. Prompt markers retain a constant
  screen-space size at every zoom level.
- The centered fit-to-window image bounds form a fixed viewport. Zoomed content
  is clipped to those bounds, and panning cannot reveal background within them.
- Middle-button panning is independent of the persistent Pan toolbar action, and
  wheel zoom remains available during either pan gesture.
- Any prompt-set mutation advances the session prediction revision.
- Only a result for the current applicable revision may replace the visible
  mask.

## Mask presentation

The active mask remains visible without obscuring the source image. The initial
presentation should use a translucent tint and a clear boundary. Dimming outside
the selection is optional and should be tested rather than assumed.

Mask rendering updates from the returned mask without reconstructing the whole
UI scene. The visible candidate is session state, not state held only by a
painted item.

## Candidate masks

When the backend returns multiple candidates, preserve them in backend-provided
order with scores where meaningful. Display the first candidate initially.
Candidate cycling is included in the sandbox for evaluation but is not yet an
accepted core interaction.

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
- [ ] Existing points can be selected and moved; points can be deleted by clicking
      their marker.
- [x] Each committed prompt edit requests prediction for the new revision.
- [x] A backend-neutral segmentation result can contain one or more masks.
- [x] The highest-scoring mask is displayed transparently over the image.
- [ ] Candidate cycling works when a backend provides multiple candidates, or
      the experiment is explicitly removed after evaluation.
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
