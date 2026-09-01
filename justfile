# Show the available project commands.
default:
    @just --list

# Install or update the locked development environment.
setup:
    uv sync

# Download and verify an official SAM 2.1 checkpoint (small by default).
model model="small":
    uv run python scripts/download_sam2.py --model {{model}}

# Start the system-tray application.
run *args:
    uv run objectsnip {{args}}

# Start with source and region screenshots saved under .artifacts/captures.
debug:
    uv run objectsnip --debug-captures

# Regenerate the committed application icon assets.
icon:
    uv run python scripts/render_icon.py

# Run the unit test suite.
test:
    uv run pytest

# Check code for lint violations.
lint:
    uv run ruff check .

# Verify that code is already formatted.
format-check:
    uv run ruff format --check .

# Format the codebase.
format:
    uv run ruff format .

# Run static type analysis.
typecheck:
    uv run pyright

# Run every non-mutating quality gate.
check: lint format-check typecheck test

# Apply safe lint fixes and format the codebase.
fix:
    uv run ruff check . --fix
    uv run ruff format .

# Build source and wheel distributions.
build:
    uv build
