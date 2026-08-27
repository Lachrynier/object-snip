# Show the available project commands.
default:
    @just --list

# Install or update the locked development environment.
setup:
    uv sync

# Start the system-tray application.
run:
    uv run objectsnip

# Start with source and region screenshots saved under .artifacts/captures.
debug:
    uv run objectsnip --debug-captures

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
