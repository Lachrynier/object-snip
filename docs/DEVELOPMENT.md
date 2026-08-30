# Development guide

This guide covers the local development workflow. User-facing setup and usage
belong in the repository [`README.md`](../README.md).

## Environment setup

ObjectSnip uses Python 3.12, `uv` for environment and package management, and
`just` for common project commands.

```bash
uv sync
just model [<model>]
just run [--model <model>]
```

`just model` downloads and verifies the default SAM 2.1 Small checkpoint. Pass
`tiny`, `base-plus`, or `large` to download another supported size. See
[`SAM2.md`](SAM2.md) for model and device options.

## Project commands

Run `just` to list the available recipes.

| Command | Purpose |
|---|---|
| `just setup` | Install or update the locked development environment |
| `just model` | Download and verify the default Small checkpoint |
| `just model tiny` | Download and verify another model size |
| `just run` | Start ObjectSnip |
| `just debug` | Start ObjectSnip with capture artifacts enabled |
| `just test` | Run the unit test suite |
| `just lint` | Check Ruff lint rules |
| `just format-check` | Verify formatting |
| `just format` | Format Python files |
| `just typecheck` | Run Pyright |
| `just check` | Run lint, formatting, type, and unit checks |
| `just fix` | Apply safe Ruff fixes and formatting |
| `just build` | Build source and wheel distributions |

Run `just check` before committing when practical. Recipes delegate Python and
environment execution to `uv`; CI should use the same entry points rather than
duplicate their commands.

## VS Code

Run `just setup`, then open the repository directory in VS Code. Shared launch
configurations use `.venv/bin/python` and appear in **Run and Debug**:

- **ObjectSnip: Run** starts the normal tray application.
- **ObjectSnip: Debug captures** starts it with capture artifacts enabled.

Both run the `objectsnip` module in the integrated terminal. The workspace also
enables pytest discovery.

## Testing the real model

Ordinary unit tests use the deterministic fake segmenter and do not require a
model checkpoint or accelerator. Run the opt-in SAM integration test with:

```bash
OBJECTSNIP_RUN_SAM2_TESTS=1 uv run pytest tests/integration/test_sam2_backend.py
```

## Capture troubleshooting

The optional debug-capture mode records the screenshot received from the
capture backend and the exact crop produced by **Lock region**. It remains
useful for diagnosing portal, display-scaling, and crop-coordinate problems.

```bash
just debug
```

By default, ignored files are written under `.artifacts/captures` as a
timestamp-matched pair:

```text
<timestamp>-source.png
<timestamp>-region.png
```

To choose another directory:

```bash
uv run objectsnip --debug-captures /tmp/objectsnip-captures
```

Debug saving is disabled during normal runs. Treat recorded screenshots as
sensitive: they can contain anything visible on the captured display.
