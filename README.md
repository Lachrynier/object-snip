# ObjectSnip

ObjectSnip is a local-first desktop tool for selecting an object from a frozen
screenshot and copying it as a transparent image.

The project is in early development. The first vertical slice provides a tray
application and an editable context-region workflow; model inference comes
afterward.

## Documentation

Start with [`docs/INDEX.md`](docs/INDEX.md). It identifies the authoritative
document and minimal reading set for each kind of work.

## Development

The project uses modern Python packaging and tooling through
[`uv`](https://docs.astral.sh/uv/).

```bash
uv sync
uv run objectsnip
```

Choose **Capture region** from the tray menu (or double-click its icon), draw a
rectangle, adjust it by dragging its interior, edges, or corners, then choose
**Lock region**. Locking currently verifies the crop handoff with a tray
notification; segmentation is intentionally not implemented yet.

Run project checks with:

```bash
uv run pytest
uv run ruff check .
uv run pyright
```

The intended `Super+Shift+O` global shortcut is deferred until a platform
integration adapter is added; the current slice does not pretend a window-local
shortcut is global.

### Wayland compatibility

On native Wayland, ObjectSnip requests the screenshot through the standardized
XDG Desktop Portal. The request is asynchronous and the desktop may mediate
permission before returning the image. On other Qt platforms, the current
implementation uses Qt's direct screen-grab API.

Rectangle and crop logic receive the same `QImage` through either path and do
not depend on the capture mechanism.

### Visual capture debugging

Enable explicit debug output to save both the screenshot received from the
capture backend and the region produced by **Lock region**:

```bash
uv run objectsnip --debug-captures
```

The default directory is `.artifacts/captures`, which is ignored by Git. Each
session produces a timestamp-matched pair:

```text
<timestamp>-source.png
<timestamp>-region.png
```

Override the directory when useful:

```bash
uv run objectsnip --debug-captures /tmp/objectsnip-captures
```

Debug image saving is disabled unless the flag is present. Paths are printed to
the terminal, and the locked-region path is included in the tray notification.
