"""Repository-hygiene tests: the rules that protect the research (§9.1, R15, R18).

Raw data and secrets must never be committable. These tests read the actual
.gitignore so a careless edit that unprotects them fails CI.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _gitignore_lines() -> list[str]:
    text = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip()]


def test_gitignore_exists() -> None:
    assert (REPO_ROOT / ".gitignore").is_file()


def test_raw_data_is_gitignored() -> None:
    lines = _gitignore_lines()
    for pattern in ("data/raw/", "data/interim/", "data/processed/", "eval_outputs/"):
        assert (
            pattern in lines
        ), f"{pattern} missing from .gitignore — raw data must not be committed"


def test_env_files_are_gitignored() -> None:
    lines = _gitignore_lines()
    assert ".env" in lines, ".env missing from .gitignore (R18)"
    assert "!.env.example" in lines, ".env.example should stay committed as the template"


def test_env_example_contains_no_values() -> None:
    """Every assignment in .env.example must be empty or a safe default."""
    allowed_values = {"", "offline"}
    for line in (REPO_ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        _, _, value = line.partition("=")
        assert value.strip() in allowed_values, f"unexpected value in .env.example: {line!r}"


def test_repro_map_matches_configs() -> None:
    """§7 step 33: docs/reproducibility.md and configs/experiment/ must agree
    in BOTH directions — every committed experiment config appears in the
    reproducibility map, and the map references no phantom config. 'One YAML =
    one reproducible experiment', made mechanical."""
    import re

    doc = (REPO_ROOT / "docs" / "reproducibility.md").read_text(encoding="utf-8")
    referenced = set(re.findall(r"`([\w./]+\.yaml)`(?:\s|/|\|)", doc))
    referenced = {name.removeprefix("configs/experiment/") for name in referenced}
    on_disk = {p.name for p in (REPO_ROOT / "configs" / "experiment").glob("*.yaml")}
    missing_from_doc = on_disk - referenced
    phantom_in_doc = {r for r in referenced if r not in on_disk and "/" not in r}
    assert not missing_from_doc, (
        f"configs missing from docs/reproducibility.md: {sorted(missing_from_doc)} — "
        "every experiment config gets a row in the repro map"
    )
    assert (
        not phantom_in_doc
    ), f"repro map references configs that do not exist: {sorted(phantom_in_doc)}"


def test_m8_governance_docs_present_and_caveated() -> None:
    """§7 step 33 deliverables (model card, datasheets, ethics statement) exist
    and the two governance docs carry the exact screening caveat (R11)."""
    from collusiongraph import SCREENING_CAVEAT

    datasheets = REPO_ROOT / "docs" / "datasheets"
    for name in (
        "elliptic_pp",
        "amlworld_hi_small",
        "mendeley_eu",
        "garcia_rodriguez",
        "ocds_georgia",
    ):
        assert (datasheets / f"{name}.md").is_file(), f"datasheet missing: {name}"
    for doc in ("model_card.md", "ethics_and_scope.md"):
        text = (REPO_ROOT / "docs" / doc).read_text(encoding="utf-8")
        assert (
            SCREENING_CAVEAT.split(" — ")[0].lower() in text.lower()
        ), f"{doc} must carry the screening caveat (R11)"


def test_red_team_review_covers_the_checklist() -> None:
    """§9.3: the pre-submission red-team pass exists and addresses every
    checklist dimension by name; findings carry RT- ids so the writing phase
    can cite them."""
    text = (REPO_ROOT / "docs" / "red_team_review.md").read_text(encoding="utf-8")
    for dimension in (
        "Leakage",
        "Imbalance reporting",
        "Baseline fairness",
        "transfer reporting",
        "Reproduction-from-scratch",
    ):
        assert dimension in text, f"red-team review must address: {dimension}"
    assert "RT-1" in text, "findings must carry RT- ids"


def test_significance_quotes_stay_seed_labeled() -> None:
    """RT-1 regression pin: wherever the model card quotes the paired-bootstrap
    deltas it must label them seed-0 — they are not differences of multi-seed
    means and presenting them beside means without the label misleads."""
    text = (REPO_ROOT / "docs" / "model_card.md").read_text(encoding="utf-8")
    assert "seed-0 paired bootstrap" in text, (
        "model card must label the paired-bootstrap deltas as seed-0 "
        "comparisons (docs/red_team_review.md RT-1)"
    )
