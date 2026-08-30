# Roadmap

**Status:** Draft  
**Active milestone:** 0.2 — Interactive object selection

This document owns sequencing, milestone scope, and status. Feature documents
own behavior; roadmap entries link to them rather than restating all their
requirements.

## Status summary

| Milestone | Status | Purpose |
|---|---|---|
| 0.0 Documentation baseline | Implemented | Establish small, maintainable sources of truth |
| 0.1 Capture and context region | Implemented | Prove portable tray invocation and precise model-input cropping without SAM |
| 0.2 Interactive object selection | In progress | Prove model-backed prompt and mask interaction on the locked crop |
| 0.3 Daily utility | Deferred | Complete the invoke-select-copy workflow |
| 0.4 Selection quality | Deferred | Improve difficult masks after the core works |
| 0.5 Platform robustness | Deferred | Harden desktop integration and distribution |
| 1.0 Stable core utility | Deferred | Deliver a reliable supported product |

## 0.1 — Capture and context region

Implement [`features/capture.md`](features/capture.md): a resident system-tray
application, tray-menu invocation, frozen-screen overlay, editable context
rectangle, and explicit crop locking. Global shortcut registration follows as
a platform adapter after this portable slice.

Purpose:

- prove the tray invocation and frozen-screen interaction early;
- let users exclude irrelevant pixels before expensive model work;
- establish screen, frozen-image, and crop-local coordinates;
- establish a clean capture-to-segmentation handoff without loading SAM.

Exit criteria are the 0.1 acceptance criteria in `features/capture.md`.

Explicitly excluded: SAM or another real segmenter, object prompts, mask
rendering, clipboard output, saved output, lasso, packaging, and multi-monitor
support.

## 0.2 — Interactive object selection

Feed the locked context crop into a common segmentation interface and implement
the 0.2 scope in [`features/selection.md`](features/selection.md).

The current slice provides the object-selection window, background image
encoding lifecycle, real SAM 2.1 Hiera Small backend, contract-compatible fake,
loading state, retry behavior, positive and negative point prompts, click-to-
remove markers, zoom and pan controls, ranked mask rendering, toolbar candidate
selection, refinement from the active candidate, and stale-result rejection.
Point dragging and keyboard controls remain to be implemented.

Purpose:

- test whether point-based refinement is useful;
- validate model-independent prompt/session boundaries;
- let UI and session tests use a deterministic fake backend;
- measure real-backend first-result and refinement latency.

Do not broaden OS integration or add output while debugging selection quality.

## 0.3 — Daily utility

Connect the accepted capture and selection workflows to
[`features/export.md`](features/export.md). The result should be useful enough
for regular developer use on the primary Linux environment.

Box prompts, keyboard candidate cycling, clipboard confirmation, and
save-to-file remain Draft choices in their owning feature documents; accepting
them changes this milestone's exact scope.

## Later milestones

- **0.4 Selection quality:** evaluate loose lasso, candidate navigation, mask
  boundaries, alpha treatment, and model benchmark results.
- **0.5 Platform robustness:** multi-monitor/DPI behavior, broader Wayland/X11
  integration, device fallback, packaging, settings, and error recovery.
- **1.0 Stable core utility:** installable and documented on the supported
  platform, reliable invocation and clipboard behavior, acceptable latency, and
  no known major coordinate defects.

## Deferred idea parking lot

Semantic text selection, similar-object selection, redaction, inpainting,
history, destination-aware export, and multi-object composition are not product
commitments. Promote an idea by first changing `PRODUCT.md`, then creating or
extending its owning feature specification and placing it in a milestone.

## Next product review

Before expanding the active milestone, review and either accept, revise, or
defer:

1. the context-region open decisions in `features/capture.md`;
2. the product principles in `PRODUCT.md`;
3. the architecture invariants in `ARCHITECTURE.md`.

The Python, PySide6, and `uv` direction is accepted in
`decisions/0001-python-pyside.md`.
