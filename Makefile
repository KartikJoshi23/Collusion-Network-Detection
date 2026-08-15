# Optional thin aliases of the poethepoet tasks for *nix CI (§8).
# The canonical, cross-platform task definitions live in pyproject.toml.

.PHONY: fmt lint typecheck test data check

fmt:
	uv run poe fmt

lint:
	uv run poe lint

typecheck:
	uv run poe typecheck

test:
	uv run poe test

data:
	uv run poe data

check:
	uv run poe check
