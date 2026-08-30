# Capture and context region

**Status:** Implemented with open platform and interaction decisions
**First milestone:** 0.1

This document owns application invocation, screen acquisition, frozen-screen
presentation, editable context-region selection, locking, cancellation, and
capture-related platform behavior. It does not own object prompts or output.

## Goal

Let the user quickly isolate the part of the screen that contains the desired
object and useful surrounding context. Unrelated pixels should not be passed to
the image encoder.

For example, when extracting something from a browser video, the user can
include the video area while excluding tabs and other browser chrome.

The context rectangle is not an object mask or final crop for export. It defines
the image on which semantic object selection will operate.

## 0.1 user flow

1. ObjectSnip is running in the system tray.
2. User chooses **Capture region** from the tray menu or presses
   `Super+Shift+O`; both invoke the same action.
3. ObjectSnip immediately captures the relevant screen and displays those
   frozen pixels in a fullscreen, frameless overlay.
4. User drags to create a rectangular context region.
5. The draft rectangle can be moved or resized precisely.
6. User activates **Lock region**.
7. ObjectSnip commits the enclosed screenshot pixels as the context crop.
8. The object-selection workspace opens and begins encoding the committed crop
   asynchronously.

## Invocation and lifecycle

| Input or event | Intended result |
|---|---|
| Application starts | Remain available through a system-tray item |
| Tray capture action while idle | Capture and open the context-region overlay |
| `Esc` while overlay is active | Cancel without committing a crop or producing output |
| Shortcut while overlay is active | Do not create a nested capture session |
| Application exits | Unregister the shortcut and remove the tray item |

`Super+Shift+O` is the initial global shortcut: `O` is mnemonic for “object.”
On Wayland it is registered through the XDG Global Shortcuts portal, so the
desktop can mediate and persist the binding.

## Frozen-screen behavior

The desktop is not literally frozen. Invocation captures the screen before the
overlay appears, then the overlay displays that captured image. Region editing
therefore operates on stable pixels even if the underlying video or application
continues changing.

The initial scope is one screen. The target-screen rule remains an open
platform decision.

## Draft context rectangle

The first pointer drag on empty overlay space creates a rectangle between press
and current pointer positions. While draft, it is visibly distinct from the
outside area and supports:

- dragging inside the rectangle to move it;
- dragging an edge to resize it along one axis;
- dragging a corner to resize it along both axes;
- replacing it by beginning a new drag outside it;
- precise hit targets that remain usable at high DPI.

The rectangle is normalized regardless of drag direction and clamped to the
captured image bounds. It must remain non-empty. A minimum useful size and
keyboard-based fine adjustment remain open decisions.

Moving or resizing changes only draft session state. It does not crop, encode,
or invoke segmentation on every pointer movement.

## Locking the region

A visible **Lock region** button is enabled only for a valid non-empty draft.
Activating it:

1. converts the draft bounds to integer frozen-image pixel bounds;
2. copies the enclosed pixels into a committed context crop;
3. establishes crop-local coordinates whose origin is the crop's top-left;
4. prevents further draft editing in milestone 0.1; and
5. emits the crop through the capture-to-segmentation handoff.

The handoff opens the object-selection workspace and invokes a backend-neutral
image segmenter. The real SAM 2.1 backend encodes the crop; its deterministic
fake mirrors the same contract for tests. Object prompts remain owned by the
selection workflow.

## Display and coordinate rules

- Capture returns pixels plus enough display geometry and scale metadata to map
  overlay input to exact frozen-image pixels.
- Coordinate conversion follows `ARCHITECTURE.md`; UI handlers contain no ad
  hoc device-pixel-ratio arithmetic.
- Context-crop coordinates are translated from frozen-image coordinates at lock
  time.
- Visual draft bounds and committed pixel bounds must have a defined,
  deterministic rounding convention.

## Platform scope

Linux is the initial platform. System tray, shortcut registration, and screen
capture remain behind small adapters so X11/Wayland details do not enter region
geometry or later segmentation logic.

The prototype should use the simplest reliable path in the primary developer
environment. Full X11/Wayland breadth is not an implicit 0.1 requirement.

The current Linux implementation uses the standardized XDG Screenshot Portal
when Qt is running on Wayland. Portal capture is asynchronous and KDE or another
desktop may mediate permission. Other Qt platforms use direct screen capture.

## 0.1 acceptance criteria

- [x] Application starts and remains accessible through a system-tray item.
- [x] The tray menu's **Capture region** action invokes capture.
- [x] `Super+Shift+O` globally invokes the same capture action on Wayland.
- [x] Invocation captures one screen before showing the overlay.
- [x] A fullscreen frameless overlay displays the stable captured pixels.
- [x] Dragging creates a normalized rectangular draft in every drag direction.
- [x] Dragging inside moves the rectangle without changing its size.
- [x] Each edge and corner resizes the expected bounds.
- [x] Creating, moving, and resizing remain clamped to image bounds.
- [x] Starting a drag outside the draft replaces it.
- [x] Draft edits do not invoke the segmentation boundary.
- [x] **Lock region** is unavailable for an invalid or empty rectangle.
- [x] Locking produces exactly the enclosed pixels as a committed context crop.
- [x] Crop-local coordinates begin at the committed crop's top-left.
- [x] Locking opens selection and starts image encoding exactly once.
- [x] `Esc` cancels without committing a crop or producing output.
- [x] A second invocation cannot create a nested capture session.
- [x] Rectangle hit-testing, bounds, clamping, and coordinate transformations
      have deterministic unit tests.
- [x] Capture/platform code remains independent of segmentation backends.
- [x] Native Wayland capture receives pixels asynchronously through the desktop
      screenshot portal.

## Open decisions

- How is the target screen chosen: pointer location, active window, or another
  deterministic rule?
- Which shortcut/capture path is appropriate for the primary Linux display
  server?
- How should an invocation during active capture notify the user, if at all?
- What is the minimum valid context-region size?
- Should arrow keys allow precise movement/resizing before lock?
- Should double-clicking inside the region also lock it?
- In a later milestone, should the user be able to unlock after encoding, with
  the understood cost of discarding prompts and re-encoding?

## Deferred

Configurable shortcuts, multi-monitor capture, mixed-DPI displays, full
Wayland/X11 breadth, Windows, macOS, screen recording, capture history, and
polished native permission flows remain outside the current capture scope.
