"""Dataset acquisition sprint — download, checksum, and license-record every dataset.

Per implementation-plan.md §4.3 and §7 Week 1: raw data lands in ``data/raw/``
(gitignored); only the manifests in ``data/manifests/`` (checksums + source URLs +
download dates + licenses) are committed.

Behavior per dataset:
  * no manifest yet             -> download, checksum, write manifest (first run, master machine)
  * manifest exists, no raw dir -> download, then verify against the committed checksums
                                   (collaborator bootstrap)
  * manifest exists, raw dir    -> verify local files against the committed checksums

Blocked datasets (e.g. missing Kaggle credentials) are reported loudly and recorded
with ``status: blocked`` — the script continues with the rest (never stall the session
on one blocker). Exit code is 0 unless ``--strict`` is passed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import requests
from tqdm import tqdm

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW = REPO_ROOT / "data" / "raw"
MANIFESTS = REPO_ROOT / "data" / "manifests"

ELLIPTIC_PP_DRIVE_FOLDER = (
    "https://drive.google.com/drive/folders/1MRPXz79Lu_JGLlJ21MDfML44dKN9R08l"
)
PYG_ELLIPTIC_BASE = "https://data.pyg.org/datasets/elliptic"
MENDELEY_FILES = {
    "GTI_labelled_cartel_data_NOV2023.csv": (
        "https://data.mendeley.com/public-files/datasets/f3y4nrn3s6/files/"
        "6081fd75-cb35-435e-a04e-87b860cc7743/file_downloaded"
    ),
    "GTI_labelled_cartel_data_NOV2023.RData": (
        "https://data.mendeley.com/public-files/datasets/f3y4nrn3s6/files/"
        "a38b3790-dad6-4d1a-a048-1a11063d54b9/file_downloaded"
    ),
}
GARCIA_SUPPLEMENT_URL = "https://ars.els-cdn.com/content/image/1-s2.0-S0926580521004982-mmc2.zip"
AMLWORLD_KAGGLE_SLUG = "ealtman2019/ibm-transactions-for-anti-money-laundering-aml"
AMLWORLD_HI_SMALL_FILES = ["HI-Small_Trans.csv", "HI-Small_Patterns.txt", "HI-Small_accounts.csv"]
# OCP Data Registry publication 52 (Georgia OpenTender) — §4.3 D5 publisher,
# selected 2026-07-20 for standard bids.details[] coverage incl. losing bidders
# (Decision log). Per-year compiled-release JSONL; ~14 MB/year, ~230 MB total.
OCDS_GEORGIA_DOWNLOAD = "https://data.open-contracting.org/en/publication/52/download?name="
OCDS_GEORGIA_YEARS = range(2010, 2026)  # registry coverage 2010-11 .. 2025-01

KAGGLE_SETUP_HELP = (
    "Kaggle credentials not found. Setup (documented in README.md):\n"
    "  1. kaggle.com -> account settings -> 'Create New API Token' (downloads kaggle.json)\n"
    "  2. Place it at %USERPROFILE%\\.kaggle\\kaggle.json (Windows) or ~/.kaggle/kaggle.json\n"
    "  3. Re-run: uv run poe data"
)


@dataclass
class Result:
    dataset: str
    status: str  # complete | blocked | verified | mismatch
    detail: str = ""
    files: list[dict] = field(default_factory=list)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# Mendeley's public-files endpoint rejects default python-requests UAs with 403.
_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CollusionGraph-data-bootstrap"}


def stream_download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120, headers=_HEADERS) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("Content-Length", 0))
        with (
            dest.open("wb") as fh,
            tqdm(total=total, unit="B", unit_scale=True, desc=dest.name) as bar,
        ):
            for chunk in resp.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
                bar.update(len(chunk))


def collect_files(root: Path) -> list[dict]:
    return [
        {
            "path": p.relative_to(root).as_posix(),
            "bytes": p.stat().st_size,
            "sha256": sha256_of(p),
        }
        for p in sorted(root.rglob("*"))
        if p.is_file()
    ]


def write_manifest(name: str, source: str, license_: str, files: list[dict], notes: str) -> None:
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    manifest = {
        "dataset": name,
        "source": source,
        "license": license_,
        "downloaded_at": date.today().isoformat(),
        "status": "complete",
        "files": files,
        "notes": notes,
    }
    (MANIFESTS / f"{name}.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def verify_against_manifest(name: str, dataset_dir: Path) -> Result:
    manifest = json.loads((MANIFESTS / f"{name}.json").read_text(encoding="utf-8"))
    missing, bad = [], []
    for entry in manifest["files"]:
        local = dataset_dir / entry["path"]
        if not local.is_file():
            missing.append(entry["path"])
        elif sha256_of(local) != entry["sha256"]:
            bad.append(entry["path"])
    if missing or bad:
        return Result(name, "mismatch", f"missing={missing} checksum_mismatch={bad}")
    return Result(name, "verified", f"{len(manifest['files'])} files match the manifest")


def acquire(name: str, source: str, license_: str, notes: str, fetch) -> Result:
    """Shared skeleton: fetch when absent, verify against the committed manifest."""
    dataset_dir = RAW / name
    if not (MANIFESTS / f"{name}.json").exists():
        fetch(dataset_dir)
        files = collect_files(dataset_dir)
        if not files:
            raise RuntimeError("fetch produced no files")
        write_manifest(name, source, license_, files, notes)
        return Result(name, "complete", f"{len(files)} files downloaded + checksummed", files)
    if not dataset_dir.exists():
        # Collaborator bootstrap: manifest is committed but raw data (gitignored)
        # is absent on this machine — download, then verify the checksums below.
        # A dir that exists but mismatches stays a mismatch (corruption, not bootstrap).
        fetch(dataset_dir)
    return verify_against_manifest(name, dataset_dir)


# ── Dataset-specific fetchers ─────────────────────────────────────────────


def fetch_elliptic_pp(dest: Path) -> None:
    import gdown

    dest.mkdir(parents=True, exist_ok=True)
    downloaded = gdown.download_folder(
        url=ELLIPTIC_PP_DRIVE_FOLDER, output=str(dest), quiet=False, use_cookies=False
    )
    if not downloaded:
        raise RuntimeError("gdown could not retrieve the Google Drive folder")


def fetch_elliptic_base(dest: Path) -> None:
    for stem in ("elliptic_txs_features", "elliptic_txs_edgelist", "elliptic_txs_classes"):
        zip_path = dest / f"{stem}.csv.zip"
        stream_download(f"{PYG_ELLIPTIC_BASE}/{stem}.csv.zip", zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(dest)
        zip_path.unlink()  # keep only the CSVs; checksums cover the extracted files


def fetch_mendeley(dest: Path) -> None:
    # Mendeley's CDN 403s the `requests` library (TLS fingerprinting) but accepts
    # stdlib urllib with a browser UA — verified 2026-07-13.
    import urllib.request

    dest.mkdir(parents=True, exist_ok=True)
    for filename, url in MENDELEY_FILES.items():
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with (
            urllib.request.urlopen(req, timeout=120) as resp,
            (dest / filename).open("wb") as fh,
        ):
            shutil.copyfileobj(resp, fh)


def fetch_garcia(dest: Path) -> None:
    zip_path = dest / "1-s2.0-S0926580521004982-mmc2.zip"
    stream_download(GARCIA_SUPPLEMENT_URL, zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest / "extracted")


def fetch_ocds_georgia(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for year in OCDS_GEORGIA_YEARS:
        name = f"{year}.jsonl.gz"
        stream_download(f"{OCDS_GEORGIA_DOWNLOAD}{name}", dest / name)


def kaggle_credentials_present() -> bool:
    import os

    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    return (
        kaggle_json.is_file()
        or "KAGGLE_API_TOKEN" in os.environ  # new-style KGAT_* token (Kaggle CLI >= 2)
        or ("KAGGLE_USERNAME" in os.environ and "KAGGLE_KEY" in os.environ)
    )


def fetch_amlworld_hi_small(dest: Path) -> None:
    if not kaggle_credentials_present():
        raise PermissionError(KAGGLE_SETUP_HELP)
    dest.mkdir(parents=True, exist_ok=True)
    for filename in AMLWORLD_HI_SMALL_FILES:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "kaggle",
                "datasets",
                "download",
                "-d",
                AMLWORLD_KAGGLE_SLUG,
                "-f",
                filename,
                "-p",
                str(dest),
            ],
            check=True,
        )
        # kaggle wraps single files in a zip; unwrap for stable checksums
        wrapped = dest / f"{filename}.zip"
        if wrapped.exists():
            with zipfile.ZipFile(wrapped) as zf:
                zf.extractall(dest)
            wrapped.unlink()


DATASETS: dict[str, dict] = {
    "elliptic_pp": {
        "source": "https://github.com/git-disl/EllipticPlusPlus "
        f"(data: {ELLIPTIC_PP_DRIVE_FOLDER})",
        "license": (
            "No explicit license published. Released for research by Elmougy & Liu "
            "(KDD 2023, arXiv:2306.06108); cite the paper; usage questions to the "
            "authors (yelmougy3@gatech.edu). Not redistributed in this repository."
        ),
        "notes": "Primary financial anchor (D1). Transactions + Actors datasets, 8 CSVs.",
        "fetch": fetch_elliptic_pp,
    },
    "elliptic": {
        "source": f"{PYG_ELLIPTIC_BASE}/elliptic_txs_{{features,edgelist,classes}}.csv.zip "
        "(PyG mirror of the original Elliptic dataset)",
        "license": (
            "No explicit SPDX license. Original dataset released by Elliptic for AML "
            "research (Weber et al. 2019, arXiv:1908.02591); mirrored by PyTorch "
            "Geometric. Research use with citation. Not redistributed here."
        ),
        "notes": "Base Elliptic (D1); loadable via PyG EllipticBitcoinDataset "
        "pointed at data/raw/elliptic.",
        "fetch": fetch_elliptic_base,
    },
    "amlworld_hi_small": {
        "source": f"https://www.kaggle.com/datasets/{AMLWORLD_KAGGLE_SLUG} (HI-Small variant)",
        "license": (
            "Community Data License Agreement - Sharing - Version 1.0 "
            "(CDLA-Sharing-1.0) — verified via Kaggle dataset metadata 2026-07-13. "
            "Altman et al., NeurIPS 2023, arXiv:2306.16424."
        ),
        "notes": "D2: synthetic AML with 8 ground-truth laundering patterns. "
        "Requires Kaggle API auth. Caveat (Kaggle discussion #427517): transactions "
        "dated after the primary date range are all laundering — handle in splits.",
        "fetch": fetch_amlworld_hi_small,
    },
    "mendeley_eu": {
        "source": "https://data.mendeley.com/datasets/f3y4nrn3s6/2 "
        "(DOI 10.17632/f3y4nrn3s6.2, v2 2025-08-12)",
        "license": "CC BY NC 3.0 (as stated on the Mendeley Data record)",
        "notes": (
            "D4: primary labeled procurement anchor. Fazekas, Wachs, Tóth & Abdou; "
            "companion paper IJIO S0167718725000943. Losing-bid coverage caveat per §4.3 D4."
        ),
        "fetch": fetch_mendeley,
    },
    "garcia_rodriguez": {
        "source": f"{GARCIA_SUPPLEMENT_URL} (supplement ec0010/mmc2 to Automation in "
        "Construction 133:104047, S0926580521004982)",
        "license": (
            "Article is open access under CC BY-NC-ND 4.0 (per Crossref license "
            "metadata for DOI 10.1016/j.autcon.2021.104047); supplement downloaded "
            "from Elsevier (ars.els-cdn.com). Not redistributed here."
        ),
        "notes": "D3: multi-country collusion dataset (Brazil, Italy, Japan, Switzerland ×2, US).",
        "fetch": fetch_garcia,
    },
    "ocds_georgia": {
        "source": "https://data.open-contracting.org/en/publication/52 "
        "(OCP Data Registry: Georgia OpenTender, compiled releases, per-year JSONL)",
        "license": (
            "CC BY-NC-SA 4.0 (as stated on the registry publication page, "
            "verified 2026-07-20). Research use with attribution; not "
            "redistributed in this repository."
        ),
        "notes": (
            "D5: unlabeled OCDS publisher for the unsupervised regime + synthetic "
            "injection at scale (§7 step 30). Selected for standard bids.details[] "
            "coverage with identified losing bidders (co-bid structure). "
            "Coverage 2010-11..2025-01, updated half-yearly."
        ),
        "fetch": fetch_ocds_georgia,
    },
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="*", choices=sorted(DATASETS), help="subset of datasets")
    parser.add_argument("--strict", action="store_true", help="exit 1 if anything is blocked")
    args = parser.parse_args(argv)

    names = args.only or list(DATASETS)
    results: list[Result] = []
    for name in names:
        spec = DATASETS[name]
        print(f"\n=== {name} ===")
        try:
            results.append(
                acquire(name, spec["source"], spec["license"], spec["notes"], spec["fetch"])
            )
        except PermissionError as exc:  # credentials missing — blocked, not failed
            results.append(Result(name, "blocked", str(exc)))
        except Exception as exc:  # report honestly, keep going with the rest
            results.append(Result(name, "blocked", f"{type(exc).__name__}: {exc}"))
            shutil.rmtree(RAW / name, ignore_errors=True)  # no half-downloaded state

    print("\n" + "=" * 72)
    ok = True
    for r in results:
        flag = "OK " if r.status in ("complete", "verified") else "!! "
        ok = ok and r.status in ("complete", "verified")
        first_line = r.detail.splitlines()[0] if r.detail else ""
        print(f"{flag}{r.dataset:<20} {r.status:<10} {first_line}")
    print("=" * 72)
    if not ok:
        print("Some datasets are blocked/mismatched — see details above and PROGRESS.md.")
    return 0 if ok or not args.strict else 1


if __name__ == "__main__":
    sys.exit(main())
