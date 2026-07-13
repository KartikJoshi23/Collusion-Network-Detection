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
