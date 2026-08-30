# Export

**Status:** Implemented
**First milestone:** 0.3

This document owns confirmation, transparent cutout construction, clipboard
output, saved files, crop bounds, and output errors.

## Goal

Turn the active screenshot and mask into a transparent image that can be pasted
into another application with minimal friction.

## Primary user flow

1. User has an active non-empty selection.
2. User chooses **Copy object**.
3. ObjectSnip constructs an RGBA cutout from screenshot pixels and mask alpha.
4. The cutout is placed on the system clipboard.
5. ObjectSnip confirms the copy and keeps the selection open for further use.

The user can instead choose **Save object as PNG**, select a destination, and
save the same transparent cutout to a file.

## Behavior

| Input or event | Intended result | Milestone |
|---|---|---|
| **Copy object** with valid mask | Copy transparent, tightly bounded cutout and show confirmation | 0.3 |
| Export without valid mask | Export actions remain unavailable | 0.3 |
| Clipboard failure | Keep recoverable session state and show concise error | 0.3 |
| **Save object as PNG** with valid mask | Prompt for a path, save a transparent PNG, and show its location | 0.3 |
| File-save failure | Keep recoverable session state and show concise error | 0.3 |

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

- [x] Mask application produces correct RGBA values in unit tests.
- [x] Output is cropped to the non-transparent bounds.
- [x] Edge-touching and single-pixel masks are handled correctly.
- [x] Empty masks do not overwrite the clipboard.
- [x] The copy action places an image with transparency on the clipboard.
- [x] The save action writes a transparent PNG to a user-selected path.
- [x] Successful export provides confirmation and preserves the active session.
- [x] Failure preserves a recoverable session and presents concise feedback.
- [x] Export transformation is usable without Qt or a running model.
- [x] The complete export workflow has been manually tested on Fedora Wayland.

## Open decisions

- Does binary alpha look adequate for hair and anti-aliased screen objects?
- Should later output add configurable padding or preserve original placement?
- Which clipboard destination applications and additional desktop environments
  should form the recorded interoperability test set?

## Deferred

Soft/feathered alpha, mask-only output, original-plus-mask output, full-screen
bounds, destination-aware formats, export history, and automatic file naming are
outside the initial export milestone.
