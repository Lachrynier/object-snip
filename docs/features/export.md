# Export

**Status:** Draft  
**First milestone:** 0.3

This document owns confirmation, transparent cutout construction, clipboard
output, saved files, crop bounds, and output errors.

## Goal

Turn the active screenshot and mask into a transparent image that can be pasted
into another application with minimal friction.

## Primary user flow

1. User has an active non-empty selection.
2. User presses `Enter`.
3. ObjectSnip constructs an RGBA cutout from screenshot pixels and mask alpha.
4. The cutout is placed on the system clipboard.
5. The capture overlay closes only after successful clipboard output.

## Behavior

| Input or event | Intended result | Milestone |
|---|---|---|
| `Enter` with valid mask | Copy transparent, tightly bounded cutout and finish capture | 0.3 |
| `Enter` without valid mask | Keep session open and give concise feedback | 0.3 |
| Clipboard failure | Keep recoverable session state and show concise error | 0.3 |
| `Ctrl+S` with valid mask | Prompt for a path and save transparent PNG | 0.3, optional Draft |

`Esc` cancellation belongs to [`capture.md`](capture.md), not this document.

## Image construction

Given screenshot RGB pixels `I` and a mask `M`, output RGBA pixels use `I` for
color and `M` for alpha. Backend-specific tensors are converted before entering
export logic.

The initial accepted candidate is a binary 0/255 alpha mask because its behavior
is testable and backend-neutral. Soft alpha and feathering remain experiments
until visual evaluation demonstrates an improvement without halos.

## Bounds

Default output is the smallest rectangle containing non-transparent mask pixels.
Full-screenshot bounds and added padding are Deferred. An empty mask is an error,
not a zero-size image.

The crop calculation and mask application are pure logic independent of Qt and
the system clipboard.

## Clipboard

Clipboard output should preserve alpha transparency where the platform and
destination support it. Interoperability should be manually checked against a
small recorded set of representative destinations; that evidence belongs in a
test note rather than being duplicated here.

Clipboard content changes only after explicit user confirmation.

## 0.3 acceptance criteria

- [ ] Mask application produces correct RGBA values in unit tests.
- [ ] Output is cropped to the non-transparent bounds.
- [ ] Edge-touching and single-pixel masks are handled correctly.
- [ ] Empty masks do not overwrite the clipboard.
- [ ] `Enter` copies an image with transparency through the platform adapter.
- [ ] A successful copy closes the overlay and returns the application to idle.
- [ ] Failure preserves a recoverable session and presents concise feedback.
- [ ] Export transformation is usable without Qt or a running model.
- [ ] Clipboard transparency is manually verified in representative destination
      applications on the supported environment.

## Open decisions

- Is save-to-PNG required for 0.3 or should clipboard reliability come first?
- Should successful file save also close the overlay?
- Does binary alpha look adequate for hair and anti-aliased screen objects?
- Should later output add configurable padding or preserve original placement?

## Deferred

Soft/feathered alpha, mask-only output, original-plus-mask output, full-screen
bounds, destination-aware formats, export history, and automatic file naming are
outside the initial export milestone.
