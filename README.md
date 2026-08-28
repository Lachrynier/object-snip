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

## Project commands

The root `justfile` is the executable source of truth for routine development
commands. Run `just` to list them.

| Command | Purpose |
|---|---|
| `just setup` | Install or update the locked development environment |
| `just run` | Start the system-tray application |
| `just debug` | Start with capture artifacts saved under `.artifacts/captures` |
| `just test` | Run the test suite |
| `just lint` | Check for Ruff lint violations |
| `just format-check` | Verify formatting without changing files |
| `just format` | Format the codebase |
| `just typecheck` | Run Pyright static analysis |
| `just check` | Run every non-mutating quality gate |
| `just fix` | Apply safe lint fixes and formatting |
| `just build` | Build source and wheel distributions |

Before committing, normally run:

```bash
just check
```

The recipes intentionally delegate environment and Python command execution to
`uv`. A future CI workflow should invoke `just check` rather than reproduce the
individual commands.

## VS Code debugging

Run `just setup` first, then open the repository directory in VS Code. The
shared launch configurations use `.venv/bin/python` and appear in the **Run and
Debug** panel:

- **ObjectSnip: Run** starts the normal tray application.
- **ObjectSnip: Debug captures** also saves source and region artifacts under
  `.artifacts/captures`.

Both launch the `objectsnip` module in the integrated terminal, so breakpoints
work inside Qt event callbacks and portal responses. Useful initial breakpoint
locations include:

- `ObjectSnipApplication.start_capture()`;
- `PortalScreenshotService.request()`;
- `PortalScreenshotService._on_response()`;
- `ObjectSnipApplication._portal_captured()`;
- `CaptureOverlay.mousePressEvent()`; and
- `CaptureOverlay._lock_region()`.

The workspace also enables pytest discovery.

`Super+Shift+O` invokes **Capture region** globally. On Wayland, ObjectSnip
registers it through the XDG Global Shortcuts portal; the desktop may show a
one-time confirmation or allow choosing a different binding.

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
