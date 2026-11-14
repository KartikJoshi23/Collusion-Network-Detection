"""The paper's number checker (scripts/audit/verify_numbers.py) must catch a
stale printed value and any result number that nothing explains."""

import importlib.util
import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]


def _checker():
    spec = importlib.util.spec_from_file_location(
        "verify_numbers", REPO_ROOT / "scripts" / "audit" / "verify_numbers.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TEX = r"""\documentclass{article}
\begin{document}
\setlength{\tabcolsep}{2.5pt}
Trees reach $0.8123 \pm 0.0012$ and the gap is $-0.301$ (CI $[-0.324, -0.276]$).
Folds range 11.3--81.8\%. Overlap runs from $0.65$ to $0.88$; Fid$-$ is 0.000.
% a comment with 9.99 is ignored
\begin{thebibliography}{0}
\bibitem{x} Vol. 12.5.
\end{thebibliography}
\end{document}
"""


def _setup(tmp_path: Path, monkeypatch, manifest: dict) -> tuple[Path, Path]:
    vn = _checker()
    monkeypatch.setattr(vn, "REPO", tmp_path)
    art = {
        "b3": {"mean": 0.81234, "std": 0.00118},
        "delta": {"avg": -0.30061, "lo": -0.32363, "hi": -0.27608},
        "overlap": {"a|b": 0.6464, "a|c": 0.7034, "b|c": 0.8784},
        "fminus": -0.00049,
    }
    (tmp_path / "art.json").write_text(json.dumps(art), encoding="utf-8")
    tex = tmp_path / "paper.tex"
    tex.write_text(TEX, encoding="utf-8")
    man = tmp_path / "manifest.yaml"
    man.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    return man, tex


BASE = {
    "numbers": [
        {
            "id": "trees",
            "file": "art.json",
            "items": [
                {"id": "mean", "v": "0.8123", "key": "b3.mean"},
                {"id": "sd", "v": "0.0012", "key": "b3.std"},
            ],
        },
        {
            "id": "delta",
            "file": "art.json",
            "fmt": "{:.3f}",
            "items": [
                {"id": "avg", "v": "-0.301", "key": "delta.avg"},
                {"id": "lo", "v": "-0.324", "key": "delta.lo"},
                {"id": "hi", "v": "-0.276", "key": "delta.hi"},
            ],
        },
        {
            "id": "overlap",
            "file": "art.json",
            "fmt": "{:.2f}",
            "items": [
                {"id": "min", "v": "0.65", "key": "overlap.*", "reduce": "min"},
                {"id": "max", "v": "0.88", "key": "overlap.*", "reduce": "max"},
            ],
        },
        {"id": "fm", "v": "0.000", "fmt": "{:.3f}", "file": "art.json", "key": "fminus"},
    ],
    "allow": [{"reason": "dataset facts", "values": ["11.3", "81.8"]}],
}


def test_clean_manuscript_passes(tmp_path, monkeypatch) -> None:
    man, tex = _setup(tmp_path, monkeypatch, BASE)
    vn = _checker()
    monkeypatch.setattr(vn, "REPO", tmp_path)
    failures, unlisted = vn.check(man, tex)
    assert failures == []
    assert unlisted == []  # lengths, comments and the bibliography are ignored


def test_stale_value_and_unexplained_number_are_caught(tmp_path, monkeypatch) -> None:
    broken = json.loads(json.dumps(BASE))
    broken["numbers"][0]["items"][0]["v"] = "0.8124"  # stale manifest value
    broken["allow"] = []  # 11.3 and 81.8 are now unexplained
    man, tex = _setup(tmp_path, monkeypatch, broken)
    vn = _checker()
    monkeypatch.setattr(vn, "REPO", tmp_path)
    failures, unlisted = vn.check(man, tex)
    assert any("artifact gives 0.8123" in f for f in failures)
    assert any("0.8124 not found" in f for f in failures)
    # the printed 0.8123 is now unexplained too, and so are the dataset facts
    assert unlisted == ["0.8123", "11.3", "81.8"]
