# 0001 — Python and PySide6 for the initial desktop prototype

**Status:** Accepted  
**Date:** 2026-08-27

## Context

The initial product needs a custom desktop overlay, screen and clipboard access,
interactive image rendering, and integration with locally run computer-vision
models. Iteration speed matters more initially than final package size or native
platform polish.

## Decision

Use Python as the initial implementation language and PySide6/Qt as the initial
desktop UI framework. Keep domain, coordinate, segmentation, and export logic
independent of Qt so this framework choice does not define the whole system.

Use `uv` for Python version management, virtual environments, dependency
resolution and locking, packaging workflows, and project command execution.
Keep tool configuration centralized in `pyproject.toml` when the application
scaffold is created.

Use the simplest PyTorch-compatible backend during exploration. Backend choice
is deliberately not part of this decision and must follow measurement.

## Consequences

- Python provides direct access to the current segmentation ecosystem and fast
  experimentation.
- `uv` provides one reproducible workflow for environments, dependencies, lock
  files, and commands.
- Qt supplies desktop windows, rendering, events, clipboard support, and
  cross-platform potential through one framework.
- Packaging, runtime size, and model distribution may be harder than in a
  smaller native utility.
- Linux desktop integration, especially global shortcuts and Wayland capture,
  will still require platform-specific adapters.
- Keeping Qt out of domain logic preserves the option to change UI technology
  later without rewriting model-independent behavior.

The exact lint, formatting, type-checking, and test configuration will be chosen
with the first `pyproject.toml`; it need not be frozen by this decision.
