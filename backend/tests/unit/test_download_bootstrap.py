"""Bootstrap behavior of scripts/download_data.py (handoff-prompt Step 0).

A collaborator machine clones the repo with manifests committed but raw data
(gitignored) absent. ``acquire`` must download in that state and then verify
against the committed checksums — never silently rewrite the manifest, and
never re-download over a present-but-mismatched directory.
"""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

_spec = importlib.util.spec_from_file_location(
    "download_data", REPO_ROOT / "scripts" / "download_data.py"
)
assert _spec is not None and _spec.loader is not None
download_data = importlib.util.module_from_spec(_spec)
sys.modules["download_data"] = download_data
_spec.loader.exec_module(download_data)

CONTENT = b"tiny fixture bytes"
SHA = hashlib.sha256(CONTENT).hexdigest()


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    """Redirect the module's RAW/MANIFESTS roots into a temp tree."""
    raw = tmp_path / "raw"
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    monkeypatch.setattr(download_data, "RAW", raw)
    monkeypatch.setattr(download_data, "MANIFESTS", manifests)
    return raw, manifests


def _write_manifest(manifests: Path, name: str) -> None:
    (manifests / f"{name}.json").write_text(
        json.dumps(
            {
                "dataset": name,
                "source": "test",
                "license": "test",
                "downloaded_at": "2026-07-15",
                "status": "complete",
                "files": [{"path": "a.csv", "bytes": len(CONTENT), "sha256": SHA}],
                "notes": "",
            }
        ),
        encoding="utf-8",
    )


def _good_fetch(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "a.csv").write_bytes(CONTENT)


def _bad_fetch(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "a.csv").write_bytes(b"corrupted download")


def test_first_run_downloads_and_writes_manifest(sandbox) -> None:
    _raw, manifests = sandbox
    result = download_data.acquire("ds", "src", "lic", "", _good_fetch)
    assert result.status == "complete"
    manifest = json.loads((manifests / "ds.json").read_text(encoding="utf-8"))
    assert manifest["files"][0]["sha256"] == SHA


def test_bootstrap_downloads_when_raw_dir_absent(sandbox) -> None:
    raw, manifests = sandbox
    _write_manifest(manifests, "ds")
    result = download_data.acquire("ds", "src", "lic", "", _good_fetch)
    assert result.status == "verified"
    assert (raw / "ds" / "a.csv").read_bytes() == CONTENT


def test_bootstrap_flags_checksum_mismatch_on_bad_download(sandbox) -> None:
    _raw, manifests = sandbox
    _write_manifest(manifests, "ds")
    result = download_data.acquire("ds", "src", "lic", "", _bad_fetch)
    assert result.status == "mismatch"
    assert "a.csv" in result.detail


def test_existing_mismatched_dir_is_not_refetched(sandbox) -> None:
    raw, manifests = sandbox
    _write_manifest(manifests, "ds")
    _bad_fetch(raw / "ds")

    def _must_not_run(dest: Path) -> None:
        raise AssertionError("fetch must not run over an existing raw dir")

    result = download_data.acquire("ds", "src", "lic", "", _must_not_run)
    assert result.status == "mismatch"


def test_verified_when_data_already_present(sandbox) -> None:
    raw, manifests = sandbox
    _write_manifest(manifests, "ds")
    _good_fetch(raw / "ds")

    def _must_not_run(dest: Path) -> None:
        raise AssertionError("fetch must not run when data verifies")

    result = download_data.acquire("ds", "src", "lic", "", _must_not_run)
    assert result.status == "verified"
