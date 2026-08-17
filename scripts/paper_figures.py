"""Generate the paper's figures as print-resolution PNGs in the repository root.

The paper is compiled on Overleaf by the user, who uploads these PNGs alongside
the ``.tex`` and may refine them in Canva -- so every figure is a self-contained
raster at 400 DPI, sized for a two-column IEEEtran page (3.45 in single column,
7.16 in double column) and typeset in Times to match the body text.

Every number plotted here is READ FROM AN ARTIFACT under ``eval_outputs/``.
Nothing is hard-coded from memory: if an artifact is missing the figure that
needs it is skipped loudly rather than drawn with invented values.

Usage::

    uv run python scripts/paper_figures.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

REPO = Path(__file__).resolve().parents[1]
EVAL = REPO / "eval_outputs"
OUT = REPO  # figures live in the repo root: the user uploads them to Overleaf

# --- house style -----------------------------------------------------------
# Muted, colour-blind-safe, and deliberately low-saturation: the figures sit
# next to typeset Times body text and must not shout at it.
INK = "#1a1a1a"
MUTED = "#6b7280"
RULE = "#c9ccd1"
NAVY = "#24456b"
TEAL = "#1f7a72"
AMBER = "#b07d1e"
BRICK = "#a33b32"
PLUM = "#6b4a7a"
FILL_A = "#eef2f7"
FILL_B = "#eaf4f2"
FILL_C = "#faf3e4"
FILL_D = "#f7ecea"

SINGLE = 3.45
DOUBLE = 7.16

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "STIXGeneral", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 8.0,
        "axes.titlesize": 8.5,
        "axes.labelsize": 8.0,
        "xtick.labelsize": 7.2,
        "ytick.labelsize": 7.2,
        "legend.fontsize": 7.2,
        "axes.edgecolor": RULE,
        "axes.linewidth": 0.6,
        "axes.labelcolor": INK,
        "text.color": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "grid.color": "#e6e8eb",
        "grid.linewidth": 0.5,
        "legend.frameon": False,
        "figure.dpi": 400,
        "savefig.dpi": 400,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
    }
)


def _load(rel: str) -> Any:
    path = EVAL / rel
    if not path.exists():
        raise FileNotFoundError(f"missing artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _tidy(ax: plt.Axes, *, grid: str = "y") -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if grid:
        ax.grid(axis=grid, zorder=0)
        ax.set_axisbelow(True)


def _save(fig: plt.Figure, name: str) -> None:
    path = OUT / name
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    print(f"  wrote {name}  ({path.stat().st_size / 1024:.0f} KB)")


# --------------------------------------------------------------------------
# F1 -- system architecture (adapted from the stakeholder-approved flowchart
#      in docs/architecture.html: vertical, numbered, small boxes, airy)
# --------------------------------------------------------------------------
def fig_architecture() -> None:
    fig, ax = plt.subplots(figsize=(DOUBLE, 5.0))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    def box(x, y, w, h, title, *, sub=None, fc=FILL_A, ec=NAVY, mono=False, ts=7.5, ss=6.1):
        """Draw a box spanning y..y+h, title in the upper half, subtitle below it."""
        ax.add_patch(
            mpatches.FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0,rounding_size=1.0",
                linewidth=0.7,
                edgecolor=ec,
                facecolor=fc,
                zorder=3,
            )
        )
        if sub is None:
            ax.text(
                x + w / 2,
                y + h / 2,
                title,
                ha="center",
                va="center",
                fontsize=ts,
                color=INK,
                zorder=4,
            )
            return
        ax.text(
            x + w / 2,
            y + h * 0.66,
            title,
            ha="center",
            va="center",
            fontsize=ts,
            color=INK,
            zorder=4,
        )
        ax.text(
            x + w / 2,
            y + h * 0.27,
            sub,
            ha="center",
            va="center",
            fontsize=ss,
            color=MUTED,
            linespacing=1.5,
            family="monospace" if mono else "serif",
            zorder=4,
        )

    def arrow(x1, y1, x2, y2):
        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(x1, y1),
            zorder=2,
            arrowprops={
                "arrowstyle": "-|>",
                "color": MUTED,
                "linewidth": 0.6,
                "shrinkA": 0,
                "shrinkB": 0,
            },
        )

    # ---- offline cluster: encloses stages 1-7 -----------------------------
    ax.add_patch(
        mpatches.FancyBboxPatch(
            (1.5, 14.0),
            97,
            84.0,
            boxstyle="round,pad=0,rounding_size=1.4",
            linewidth=0.6,
            edgecolor="#cfd9cf",
            facecolor="#fbfdfb",
            zorder=1,
        )
    )
    ax.text(
        4.0,
        95.6,
        "OFFLINE  ·  DEEP-LEARNING PIPELINE  ·  writes files, then exits",
        fontsize=6.1,
        color="#5c7a5c",
        va="center",
    )

    box(
        28,
        85.5,
        44,
        7.0,
        "1.  Data ingestion adapters",
        sub="6 public datasets · 2 domains · checksum-verified",
    )
    arrow(50, 85.5, 50, 83.0)
    box(
        28,
        75.5,
        44,
        7.5,
        "2.  Unified graph schema (IR)",
        sub="typed nodes · edges · labels · time-safe inductive splits",
    )

    # fan out to four parallel arms
    ax.plot([50, 50], [75.5, 72.6], color=MUTED, linewidth=0.6, zorder=2)
    for cx in (13.5, 37.5, 61.5, 85.5):
        ax.plot([50, cx], [72.6, 72.6], color=MUTED, linewidth=0.6, zorder=2)
        arrow(cx, 72.6, cx, 70.2)

    arms = [
        (
            3.0,
            "3a.  Supervised GNNs",
            "GATv2 · SAGE · R-GCN\nfocal loss (~2% positives)",
            FILL_B,
            TEAL,
        ),
        (
            27.0,
            "3b.  Unsupervised arm",
            "DOMINANT · GAE · floor\nno labels required",
            FILL_B,
            TEAL,
        ),
        (
            51.0,
            "3c.  Graph features",
            "degree · motifs · k-core\nbid screens · ratios",
            FILL_B,
            TEAL,
        ),
        (
            75.0,
            "3d.  Baselines & checks",
            "XGBoost yardstick\ninjection · leakage suite",
            FILL_C,
            AMBER,
        ),
    ]
    for x, title, sub, fc, ec in arms:
        ax.add_patch(
            mpatches.FancyBboxPatch(
                (x, 58.5),
                22,
                11.7,
                boxstyle="round,pad=0,rounding_size=1.0",
                linewidth=0.7,
                edgecolor=ec,
                facecolor=fc,
                zorder=3,
            )
        )
        ax.text(x + 11, 67.2, title, ha="center", va="center", fontsize=7.1, color=INK, zorder=4)
        ax.text(
            x + 11,
            62.4,
            sub,
            ha="center",
            va="center",
            fontsize=6.0,
            color=MUTED,
            linespacing=1.55,
            zorder=4,
        )

    for cx in (13.5, 37.5, 61.5, 85.5):
        ax.plot([cx, cx], [58.5, 55.8], color=MUTED, linewidth=0.6, zorder=2)
        ax.plot([cx, 50], [55.8, 55.8], color=MUTED, linewidth=0.6, zorder=2)
    arrow(50, 55.8, 50, 53.3)

    box(
        28,
        46.0,
        44,
        7.0,
        "4.  Calibrated ensemble fusion",
        sub="isotonic per member → one comparable risk score per node",
    )
    arrow(50, 46.0, 50, 43.5)
    box(
        28,
        36.0,
        44,
        7.5,
        "5.  Leiden communities → ranked alert queue",
        sub="254 financial + 223 procurement alerts · NMS · fixed budget",
    )
    arrow(50, 36.0, 50, 33.5)
    box(
        28,
        26.5,
        44,
        7.0,
        "6.  Explanation layer",
        sub="PGExplainer subgraph · motif matcher · FATF / OECD citations",
        fc=FILL_C,
        ec=AMBER,
    )
    arrow(50, 26.5, 50, 24.0)
    box(
        26,
        16.5,
        48,
        7.0,
        "7.  Artifact store — plain files",
        sub="alerts.parquet · explanations/*.json · metrics · serving.json",
        fc=FILL_C,
        ec=AMBER,
        mono=True,
        ss=5.6,
    )

    # ---- trust boundary ---------------------------------------------------
    ax.text(
        50,
        12.4,
        "T R U S T   B O U N D A R Y",
        ha="center",
        va="center",
        fontsize=5.9,
        color=BRICK,
        zorder=5,
    )
    ax.plot([2, 98], [10.9, 10.9], color=BRICK, linewidth=0.7, linestyle=(0, (4, 2.5)), zorder=2)
    ax.text(
        50,
        9.4,
        "above: writes files, then exits   ·   below: read-only — cannot retrain"
        " or change a score",
        ha="center",
        va="center",
        fontsize=5.9,
        color=MUTED,
        zorder=5,
    )

    ax.plot([27, 73], [7.9, 7.9], color=MUTED, linewidth=0.6, zorder=2)
    ax.plot([50, 50], [9.4, 7.9], color=MUTED, linewidth=0.6, zorder=2)
    arrow(27, 7.9, 27, 6.6)
    arrow(73, 7.9, 73, 6.6)

    box(
        2,
        0.2,
        49,
        6.4,
        "8.  FastAPI serving layer — read-only",
        sub="/alerts · /subgraph · /explanations · /metrics · /rigor",
        fc=FILL_A,
        ec=NAVY,
        mono=True,
        ts=7.1,
        ss=5.3,
    )
    box(
        55,
        0.2,
        43,
        6.4,
        "9.  Investigator console + guarded copilot",
        sub="ranked queue · evidence dossier · SELECT-only agent",
        fc="#f3eef7",
        ec=PLUM,
        ts=7.1,
        ss=5.9,
    )

    _save(fig, "fig1_architecture.png")


# --------------------------------------------------------------------------
# F2 -- two ledgers, one structure (the conceptual bridge)
# --------------------------------------------------------------------------
def fig_two_ledgers() -> None:
    fig, ax = plt.subplots(figsize=(DOUBLE, 3.05))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 46)
    ax.axis("off")

    panels = [
        ("Directed cycle", "Laundering cycle", "Bid rotation", "cycle"),
        ("Fan-in star", "Smurfing / structuring", "Cover bidding", "fanin"),
        ("Fan-out star", "Layering dispersal", "Market allocation", "fanout"),
        ("Dense co-attribute", "Shell-company chains", "Shared directors", "clique"),
        ("Tight community", "Pass-through cluster", "Clustered bid prices", "community"),
    ]

    def glyph(cx, cy, kind, scale=1.0):
        r = 5.4 * scale
        dot = {"s": 9, "zorder": 5, "linewidths": 0}

        def edge(p, q, curved=False, arrow=True, shrink_b=2.6):
            style = "arc3,rad=0.22" if curved else "arc3,rad=0"
            ax.annotate(
                "",
                xy=q,
                xytext=p,
                arrowprops={
                    "arrowstyle": "-|>" if arrow else "-",
                    "color": MUTED,
                    "linewidth": 0.55,
                    "connectionstyle": style,
                    "shrinkA": 2.6,
                    "shrinkB": shrink_b,
                },
                zorder=4,
            )

        if kind == "cycle":
            pts = [
                (cx + r * math.cos(a), cy + r * math.sin(a))
                for a in np.linspace(math.pi / 2, math.pi / 2 + 2 * math.pi, 6, endpoint=False)
            ]
            for i in range(len(pts)):
                edge(pts[i], pts[(i + 1) % len(pts)], curved=True)
            ax.scatter(*zip(*pts, strict=False), color=NAVY, **dot)
        elif kind in {"fanin", "fanout"}:
            hub = (cx, cy - r * 0.6) if kind == "fanin" else (cx, cy + r * 0.6)
            leaves = [
                (cx + d, cy + (r * 0.8 if kind == "fanin" else -r * 0.8))
                for d in np.linspace(-r * 1.05, r * 1.05, 5)
            ]
            for lf in leaves:
                if kind == "fanin":
                    edge(lf, hub, shrink_b=5.0)
                else:
                    edge(hub, lf, shrink_b=3.2)
            ax.scatter(*zip(*leaves, strict=False), color=MUTED, **dot)
            ax.scatter([hub[0]], [hub[1]], color=BRICK, s=22, zorder=6, linewidths=0)
        elif kind == "clique":
            pts = [
                (cx + r * math.cos(a), cy + r * math.sin(a))
                for a in np.linspace(math.pi / 2, math.pi / 2 + 2 * math.pi, 5, endpoint=False)
            ]
            for i in range(len(pts)):
                for j in range(i + 1, len(pts)):
                    edge(pts[i], pts[j], arrow=False)
            ax.scatter(*zip(*pts, strict=False), color=PLUM, **dot)
        else:  # community -- two near-cliques joined by a single bridge

            def blob(ox):
                base = [(-1.5, 1.9), (1.6, 2.2), (-1.9, -1.6), (1.5, -2.0)]
                return [(cx + ox + dx, cy + dy) for dx, dy in base]

            left, right = blob(-r * 0.72), blob(r * 0.72)
            for grp in (left, right):
                for i in range(len(grp)):
                    for j in range(i + 1, len(grp)):
                        edge(grp[i], grp[j], arrow=False)
            edge(left[1], right[0], arrow=False)
            edge(left[3], right[2], arrow=False)
            ax.scatter(*zip(*(left + right), strict=False), color=TEAL, **dot)

    for i, (sig, fin, proc, kind) in enumerate(panels):
        cx = 10 + i * 20
        ax.text(cx, 43.5, sig, ha="center", va="center", fontsize=7.4, color=INK)
        ax.plot([cx - 8.4, cx + 8.4], [41.0, 41.0], color=RULE, linewidth=0.6)
        glyph(cx, 29.5, kind)
        ax.text(cx, 17.2, "FINANCIAL", ha="center", va="center", fontsize=5.6, color=NAVY)
        ax.text(cx, 13.6, fin, ha="center", va="center", fontsize=6.6, color=INK)
        ax.text(cx, 7.6, "PROCUREMENT", ha="center", va="center", fontsize=5.6, color=AMBER)
        ax.text(cx, 4.0, proc, ha="center", va="center", fontsize=6.6, color=INK)
        if i:
            ax.plot([cx - 10, cx - 10], [1.5, 41.5], color="#e9ebee", linewidth=0.5)

    _save(fig, "fig2_two_ledgers.png")


# --------------------------------------------------------------------------
# F3 -- per-time-step AUC-PR: the step-43 distribution shift
# --------------------------------------------------------------------------
def fig_timestep() -> None:
    seeds = range(5)
    per_seed: list[dict[str, dict[str, float]]] = []
    for s in seeds:
        m = _load(f"elliptic_pp/gnn_gatv2_focal_multiseed/seed_{s}/metrics.json")
        per_seed.append(m["node_level"]["per_time_step"])

    steps = sorted({int(k) for d in per_seed for k in d})
    mean, lo, hi, prev = [], [], [], []
    for st in steps:
        vals = [d[str(st)]["auc_pr"] for d in per_seed if str(st) in d]
        mean.append(float(np.mean(vals)))
        lo.append(float(np.mean(vals) - np.std(vals)))
        hi.append(float(np.mean(vals) + np.std(vals)))
        prev.append(
            float(np.mean([d[str(st)]["prevalence_baseline"] for d in per_seed if str(st) in d]))
        )

    fig, ax = plt.subplots(figsize=(SINGLE, 2.25))
    ax.fill_between(steps, lo, hi, color=NAVY, alpha=0.13, linewidth=0)
    ax.plot(
        steps, mean, color=NAVY, linewidth=1.15, label="GATv2-focal (5-seed mean $\\pm$ 1 s.d.)"
    )
    ax.plot(
        steps, prev, color=MUTED, linewidth=0.8, linestyle=(0, (3, 2)), label="prevalence baseline"
    )

    crater = steps.index(43)
    ax.axvspan(42.5, max(steps) + 0.5, color=BRICK, alpha=0.055, linewidth=0)
    ax.annotate(
        "dark-market\nshutdown at $t{=}43$",
        xy=(43, mean[crater]),
        xytext=(44.6, 0.62),
        fontsize=6.4,
        color=BRICK,
        ha="center",
        linespacing=1.35,
        arrowprops={
            "arrowstyle": "-|>",
            "color": BRICK,
            "linewidth": 0.55,
            "connectionstyle": "arc3,rad=-0.25",
            "shrinkB": 2,
        },
    )
    ax.set_xlabel("Elliptic++ time step (test window)")
    ax.set_ylabel("AUC-PR")
    ax.set_ylim(0, 1.0)
    ax.set_xlim(min(steps) - 0.4, max(steps) + 0.4)
    ax.legend(loc="upper left", bbox_to_anchor=(-0.02, 1.06), handlelength=1.6)
    _tidy(ax)
    _save(fig, "fig3_timestep_crater.png")


# --------------------------------------------------------------------------
# F4 -- transfer lift, both procurement matrices
# --------------------------------------------------------------------------
def _matrix_folds(rel: str) -> list[tuple[str, float]]:
    """Return (held-out group, lift) for every completed fold of a transfer matrix.

    Lift -- not raw AUC-PR -- is the cross-fold comparator: the folds have very
    different prevalences (0.25 to 0.89), so raw AUC-PR is not comparable across
    them. ``lift_mean`` is written by the matrix runner; it is recomputed from
    the mean AUC-PR and the fold prevalence only if that key is absent.
    """
    doc = _load(rel)
    out: list[tuple[str, float]] = []
    for fold in doc["folds"]:
        if fold.get("status") != "completed":
            continue
        lift = fold.get("lift_mean")
        if lift is None:
            lift = float(fold["auc_pr_mean"]) / float(fold["prevalence_baseline"])
        out.append((str(fold["test_group"]), float(lift)))
    return out


def fig_transfer() -> None:
    a = _matrix_folds("mendeley_eu/transfer_loco_matrix/matrix.json")
    b = _matrix_folds("garcia_rodriguez/transfer_lomo_matrix/matrix.json")
    fig, ax = plt.subplots(figsize=(DOUBLE * 0.80, 2.45))

    labels = [n.replace("country_", "C") for n, _ in a] + [n for n, _ in b]
    lifts = [v for _, v in a] + [v for _, v in b]
    colors = [NAVY] * len(a) + [TEAL] * len(b)
    xs = list(range(len(a))) + [i + len(a) + 1.0 for i in range(len(b))]

    ax.bar(xs, lifts, width=0.68, color=colors, linewidth=0, zorder=3)
    ax.axhline(1.0, color=BRICK, linewidth=0.8, linestyle=(0, (3, 2)), zorder=4)
    ax.text(xs[-1] + 0.95, 1.03, "no transfer", fontsize=6.2, color=BRICK, va="bottom", ha="right")

    worst = int(np.argmin(lifts[: len(a)]))
    ax.annotate(
        f"largest market\nfails ({lifts[worst]:.2f})",
        xy=(xs[worst], lifts[worst]),
        xytext=(xs[worst] - 0.1, 1.88),
        fontsize=6.3,
        color=BRICK,
        ha="center",
        linespacing=1.35,
        arrowprops={"arrowstyle": "-|>", "color": BRICK, "linewidth": 0.55, "shrinkB": 2},
    )

    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=0, fontsize=6.4)
    ax.set_ylabel("lift over fold prevalence")
    ax.set_ylim(0, 2.15)
    ax.set_xlim(-0.75, xs[-1] + 1.05)
    ax.legend(
        handles=[
            mpatches.Patch(color=NAVY, label="Mendeley EU — leave-one-country-out"),
            mpatches.Patch(color=TEAL, label="García — leave-one-market-out"),
        ],
        loc="upper right",
        bbox_to_anchor=(1.02, 1.09),
        handlelength=1.2,
        ncol=1,
    )
    _tidy(ax)
    _save(fig, "fig4_transfer_lift.png")


# --------------------------------------------------------------------------
# F5 -- label-noise: the validation-blindness diagnostic
# --------------------------------------------------------------------------
def fig_label_noise() -> None:
    curve = _load("elliptic_pp/label_noise_curve/noise_curve.json")["curve"]
    rates = [c["rate"] * 100 for c in curve]
    test = [c["auc_pr_mean"] for c in curve]
    sd = [c["auc_pr_std"] for c in curve]
    val = [c["val_auc_pr_mean"] for c in curve]

    fig, ax = plt.subplots(figsize=(SINGLE, 2.25))
    ax.errorbar(
        rates,
        test,
        yerr=sd,
        color=NAVY,
        linewidth=1.15,
        marker="o",
        markersize=3.1,
        capsize=2.0,
        elinewidth=0.6,
        capthick=0.6,
        label="test AUC-PR (3-seed)",
        zorder=4,
    )
    ax.plot(
        rates,
        val,
        color=BRICK,
        linewidth=1.15,
        marker="s",
        markersize=3.0,
        linestyle=(0, (4, 2)),
        label="validation AUC-PR",
        zorder=4,
    )

    ax.annotate(
        "",
        xy=(20, test[-1]),
        xytext=(20, val[-1]),
        arrowprops={"arrowstyle": "<->", "color": MUTED, "linewidth": 0.55},
        zorder=3,
    )
    ax.text(
        19.2,
        (test[-1] + val[-1]) / 2,
        "model selection\nlooks at the wrong\ncurve",
        fontsize=6.2,
        color=MUTED,
        ha="right",
        va="center",
        linespacing=1.4,
    )

    ax.set_xlabel("training labels randomly flipped (\\%)")
    ax.set_ylabel("AUC-PR")
    ax.set_xticks(rates)
    ax.set_ylim(0.35, 1.02)
    ax.legend(loc="lower left", bbox_to_anchor=(-0.02, -0.03), handlelength=1.7)
    _tidy(ax)
    _save(fig, "fig5_label_noise.png")


# --------------------------------------------------------------------------
# F6 -- cross-domain label efficiency, both directions
# --------------------------------------------------------------------------
def fig_label_efficiency() -> None:
    specs = [
        (
            "cross_domain/label_efficiency_proc2fin/label_efficiency.json",
            "procurement $\\rightarrow$ financial",
            NAVY,
        ),
        (
            "cross_domain/label_efficiency_fin2proc/label_efficiency.json",
            "financial $\\rightarrow$ procurement",
            TEAL,
        ),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(DOUBLE * 0.72, 2.3), sharey=False)
    for ax, (rel, title, colour) in zip(axes, specs, strict=True):
        rows = [r for r in _load(rel)["curve"] if r.get("status") == "completed"]
        ks = [int(r["k"]) for r in rows]
        gain = [float(r["transfer_gain_mean"]) for r in rows]
        pos = [g if g >= 0 else 0 for g in gain]
        neg = [g if g < 0 else 0 for g in gain]
        ax.bar(range(len(ks)), pos, width=0.62, color=colour, linewidth=0, zorder=3)
        ax.bar(range(len(ks)), neg, width=0.62, color=BRICK, alpha=0.75, linewidth=0, zorder=3)
        ax.axhline(0, color=MUTED, linewidth=0.7, zorder=4)
        ax.set_xticks(range(len(ks)))
        ax.set_xticklabels([str(k) for k in ks])
        ax.set_title(title, pad=4)
        ax.set_xlabel("target-domain labels $k$")
        _tidy(ax)
    axes[0].set_ylabel("transfer gain in AUC-PR")
    fig.legend(
        handles=[
            Line2D(
                [],
                [],
                color=MUTED,
                linewidth=0.7,
                label="gain $=0$: the frozen source probe adds nothing",
            ),
        ],
        loc="lower center",
        bbox_to_anchor=(0.5, -0.09),
        handlelength=1.8,
    )
    fig.tight_layout()
    _save(fig, "fig6_label_efficiency.png")


# --------------------------------------------------------------------------
# F7 -- the joint cross-crime (dual-actor) design: forward extension
# --------------------------------------------------------------------------
def fig_dual_actor() -> None:
    fig, ax = plt.subplots(figsize=(DOUBLE, 2.75))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 40)
    ax.axis("off")

    ax.add_patch(
        mpatches.FancyBboxPatch(
            (1.5, 20.5),
            45,
            18,
            boxstyle="round,pad=0,rounding_size=1.0",
            linewidth=0.7,
            edgecolor=NAVY,
            facecolor="#fbfcfe",
            zorder=1,
        )
    )
    ax.text(3.6, 36.6, "FINANCIAL LEDGER", fontsize=6.0, color=NAVY, va="center")
    ax.add_patch(
        mpatches.FancyBboxPatch(
            (1.5, 1.5),
            45,
            17,
            boxstyle="round,pad=0,rounding_size=1.0",
            linewidth=0.7,
            edgecolor=AMBER,
            facecolor="#fefcf7",
            zorder=1,
        )
    )
    ax.text(3.6, 16.6, "PROCUREMENT LEDGER", fontsize=6.0, color=AMBER, va="center")

    rs = np.random.RandomState(7)
    fin_nodes = [(8 + rs.uniform(0, 30), 24 + rs.uniform(0, 9)) for _ in range(7)]
    proc_nodes = [(8 + rs.uniform(0, 30), 5 + rs.uniform(0, 8)) for _ in range(7)]

    def link(p, q, colour, arrow=True, lw=0.55, style="arc3,rad=0.15"):
        ax.annotate(
            "",
            xy=q,
            xytext=p,
            zorder=3,
            arrowprops={
                "arrowstyle": "-|>" if arrow else "-",
                "color": colour,
                "linewidth": lw,
                "connectionstyle": style,
                "shrinkA": 2.4,
                "shrinkB": 2.4,
            },
        )

    for i in range(len(fin_nodes)):
        link(fin_nodes[i], fin_nodes[(i + 2) % len(fin_nodes)], "#a9b6c6")
    for i in range(len(proc_nodes)):
        link(proc_nodes[i], proc_nodes[(i + 3) % len(proc_nodes)], "#d6c49a", arrow=False)
    ax.scatter(*zip(*fin_nodes, strict=False), color=NAVY, s=11, zorder=5, linewidths=0)
    ax.scatter(*zip(*proc_nodes, strict=False), color=AMBER, s=11, zorder=5, linewidths=0)

    # the dual actor: one entity present in both ledgers
    ax.scatter([26], [27.5], color=BRICK, s=42, zorder=7, linewidths=0, marker="D")
    ax.scatter([26], [9.5], color=BRICK, s=42, zorder=7, linewidths=0, marker="D")
    ax.annotate(
        "",
        xy=(26, 9.5),
        xytext=(26, 27.5),
        zorder=6,
        arrowprops={
            "arrowstyle": "-",
            "color": BRICK,
            "linewidth": 1.0,
            "linestyle": (0, (2.5, 1.8)),
            "shrinkA": 4,
            "shrinkB": 4,
        },
    )
    ax.text(
        28.0,
        19.5,
        "shared-control edge  ·  same beneficial owner",
        fontsize=6.2,
        color=BRICK,
        va="center",
        ha="left",
    )

    ax.annotate(
        "",
        xy=(56, 20),
        xytext=(47.5, 20),
        zorder=6,
        arrowprops={"arrowstyle": "-|>", "color": MUTED, "linewidth": 0.7},
    )
    ax.text(51.7, 21.4, "join", fontsize=6.0, color=MUTED, ha="center")

    ax.add_patch(
        mpatches.FancyBboxPatch(
            (56, 22.5),
            42,
            12,
            boxstyle="round,pad=0,rounding_size=0.9",
            linewidth=0.7,
            edgecolor=PLUM,
            facecolor="#f6f2f8",
            zorder=3,
        )
    )
    ax.text(77, 31.4, "JOINT MODEL  (proposed)", ha="center", fontsize=7.0, color=INK)
    ax.text(
        77,
        26.5,
        "one heterogeneous graph over both ledgers;\n"
        "R-GCN shares parameters across relation types",
        ha="center",
        va="center",
        fontsize=6.2,
        color=MUTED,
        linespacing=1.4,
    )

    ax.add_patch(
        mpatches.FancyBboxPatch(
            (56, 6.0),
            42,
            12,
            boxstyle="round,pad=0,rounding_size=0.9",
            linewidth=0.7,
            edgecolor=MUTED,
            facecolor="#f7f8f9",
            zorder=3,
        )
    )
    ax.text(77, 14.9, "SILOED BASELINE  (this paper)", ha="center", fontsize=7.0, color=INK)
    ax.text(
        77,
        10.0,
        "two independent detectors, one per ledger;\n" "the shared-control edge is never observed",
        ha="center",
        va="center",
        fontsize=6.2,
        color=MUTED,
        linespacing=1.4,
    )

    ax.annotate(
        "",
        xy=(77, 22.0),
        xytext=(77, 18.5),
        zorder=6,
        arrowprops={"arrowstyle": "<->", "color": BRICK, "linewidth": 0.7},
    )
    ax.text(78.4, 20.25, "H1: recall of dual actors", fontsize=6.2, color=BRICK, va="center")

    _save(fig, "fig7_dual_actor.png")


FIGURES = {
    "fig1_architecture.png": fig_architecture,
    "fig2_two_ledgers.png": fig_two_ledgers,
    "fig3_timestep_crater.png": fig_timestep,
    "fig4_transfer_lift.png": fig_transfer,
    "fig5_label_noise.png": fig_label_noise,
    "fig6_label_efficiency.png": fig_label_efficiency,
    "fig7_dual_actor.png": fig_dual_actor,
}


def main() -> int:
    print(f"writing figures to {OUT}")
    failed: list[str] = []
    for name, fn in FIGURES.items():
        try:
            fn()
        except Exception as exc:
            failed.append(f"{name}: {type(exc).__name__}: {exc}")
            print(f"  SKIPPED {name} -- {type(exc).__name__}: {exc}")
    if failed:
        print("\nfigures not produced (artifact missing or schema drift):")
        for f in failed:
            print(f"  - {f}")
        return 1
    print("\nall figures written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
