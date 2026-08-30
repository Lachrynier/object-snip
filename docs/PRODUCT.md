# Product

**Status:** Core workflow implemented
**Working name:** ObjectSnip

This document owns the stable product intent and scope. Exact interactions
belong to feature specifications; implementation choices belong to architecture
or decision records.

## Purpose

ObjectSnip lets a desktop user select a visual object directly from a frozen
screenshot and export it as a transparent image through the clipboard or a PNG
file.

The intended common path is:

```text
shortcut → choose context region → lock → select object → copy or save
```

Traditional screenshot tools select rectangles. ObjectSnip treats the visual
object as the selection primitive and treats model output as an editable
proposal when the first result is ambiguous.

The initial rectangle is not the final object selection. It limits the image to
a useful context region before model encoding. This avoids processing unrelated
screen content—for example, browser chrome surrounding a video—and lets the
user decide how much nearby context the model receives.

## Target user and problem

The initial user frequently moves visual material between desktop applications:
for example, while preparing notes, slides, documentation, teaching material,
bug reports, or quick visual compositions.

Today, isolating one irregular object commonly requires capturing, cropping,
opening another tool, removing the background, correcting it, and copying the
result. ObjectSnip aims to collapse that workflow into one local interaction.

Professional image editing is not the initial use case.

## Product principles

These principles are **Draft** until individually accepted.

1. **Local-first.** Core capture and inference work without a cloud service or
   account. Screenshots remain on the machine.
2. **Fast common path.** Easy objects should require one prompt and one confirm
   action; refinement tools should stay out of the way.
3. **Editable proposals.** Segmentation is probabilistic, so the user can
   correct ambiguity rather than merely retry.
4. **Model replaceability.** Product behavior does not depend on one model
   package or tensor API.
5. **Focused utility.** Features must directly improve selecting or extracting
   an object from the screen.
6. **Graceful degradation.** Failure of automatic segmentation should not make
   the product permanently useless; manual fallbacks may be evaluated later.
7. **Performance is UX.** Prompt refinement and visual feedback must feel
   interactive.
8. **Privacy by default.** No telemetry or screenshot upload is required for
   the core product.

## Initial product boundary

The first useful product supports:

- a Fedora Wayland desktop workflow, currently the only manually tested setup;
- a resident system-tray application invoked with `Super+Shift+O` initially;
- a frozen screenshot of one screen;
- a movable and resizable rectangular context region that the user explicitly
  locks;
- positive and negative point prompts;
- editable prompts and updated mask proposals;
- transparent clipboard output;
- transparent PNG file output;
- cancellation without output.

This is a product boundary, not the active implementation milestone. See
[`ROADMAP.md`](ROADMAP.md) for sequence and status.

## Non-goals for the initial product

The following are **Deferred** unless this document and the roadmap are
deliberately revised:

- general image annotation or editing;
- OCR, screen recording, or a browser extension;
- cloud inference, accounts, collaboration, or social sharing;
- text-prompt detection, semantic search, or automatic object detection;
- inpainting, background generation, or object removal;
- image history or multi-object composition;
- automatic updates and polished cross-platform installers;
- full Windows and macOS support.

Ideas mentioned in prior design discussions do not become commitments unless
they are promoted into a live owning document.

## Success criterion

The core product workflow is implemented: a user can invoke ObjectSnip over a
visible object, select or refine it, and copy or save a clean transparent
cutout. Broader platform validation and distribution work remain before this
can be considered a generally supported release.

## Product heuristic

When considering a feature, ask:

> Does this make it faster or easier to select and extract a visual object from
> the screen?

If not, it probably belongs elsewhere.
