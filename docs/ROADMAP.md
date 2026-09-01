# Roadmap

**Status:** Current
**Active milestone:** 0.5 — Platform robustness

This document owns sequencing, milestone scope, and status. Feature documents
own behavior; roadmap entries link to them rather than restating all their
requirements.

## Status summary

| Milestone | Status | Purpose |
|---|---|---|
| 0.0 Documentation baseline | Implemented | Establish small, maintainable sources of truth |
| 0.1 Capture and context region | Implemented | Prove portable tray invocation and precise model-input cropping without SAM |
| 0.2 Interactive object selection | Implemented | Prove model-backed prompt and mask interaction on the locked crop |
| 0.3 Daily utility | Implemented | Complete the invoke-select-export workflow |
| 0.4 Selection quality | Deferred | Improve difficult masks after the core works |
| 0.5 Platform robustness | In progress | Validate and harden desktop integration beyond Fedora Wayland and Windows 11 |
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

The implemented slice provides the object-selection window, background image
encoding lifecycle, real SAM 2.1 Hiera Small backend, contract-compatible fake,
loading state, retry behavior, positive and negative point prompts, click-to-
remove markers, zoom and pan controls, ranked mask rendering, toolbar candidate
selection, refinement from the active candidate, and stale-result rejection.

Purpose:

- test whether point-based refinement is useful;
- validate model-independent prompt/session boundaries;
- let UI and session tests use a deterministic fake backend;
- measure real-backend first-result and refinement latency.

## 0.3 — Daily utility

The accepted capture and selection workflows now connect to
[`features/export.md`](features/export.md). The active object can be copied to
the clipboard or saved as a tightly cropped transparent PNG, and both actions
provide confirmation without discarding the current selection.

The complete workflow is working and has been manually tested on Fedora Linux
under Wayland and on Windows 11. That validates those two configurations only,
not broader platform support.

## Later milestones

- **0.4 Selection quality:** evaluate loose lasso, candidate navigation, mask
  boundaries, alpha treatment, and model benchmark results.
- **0.5 Platform robustness:** validate additional distributions and desktop
  environments, X11, multi-monitor/DPI behavior, device fallback, packaging,
  settings, and error recovery.
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
