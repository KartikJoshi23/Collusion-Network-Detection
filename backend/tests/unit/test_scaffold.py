"""Week-1 scaffold tests: package importability and CLI honesty."""

import collusiongraph
import pytest
from collusiongraph.cli import _ROADMAP, main


def test_package_importable() -> None:
    assert collusiongraph.__version__


def test_screening_caveat_is_verbatim() -> None:
    """The ethics caveat is a fixed string (§3.2 alert schema, R11) —
    weakening it anywhere must fail a test."""
    assert collusiongraph.SCREENING_CAVEAT == ("screening signal only — no determination of guilt")


@pytest.mark.parametrize("command", sorted(_ROADMAP))
def test_unimplemented_subcommands_exit_nonzero(command: str) -> None:
    """Scaffold subcommands must not pretend to work."""
    assert main([command]) == 1
