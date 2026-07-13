"""Leakage-test wiring check (§9.1 — the tests that protect the paper).

Real leakage assertions land in Week 2 alongside the splitters
(strict-inductive temporal, LOCO/LOMO, as-of-timestamp features) and MUST
replace this file. This placeholder only proves the `leakage` marker and
CI step are wired so the Week-2 tests cannot be silently skipped.
"""

import collusiongraph.splits
import pytest


@pytest.mark.leakage
def test_leakage_suite_is_wired() -> None:
    """The splits package exists and the leakage marker is collected in CI."""
    assert collusiongraph.splits.__doc__ is not None
