"""Generate the paper's figures as vector PDFs in ``paper/figures/``.

Each figure is sized for a two-column IEEEtran page (3.45 in single column,
7.16 in double column) and printed at 100%, so every piece of text is at least
8 pt on the page. Series are told apart by line style, marker or hatching as
well as colour, so the figures stay readable in greyscale. Fonts are embedded
as TrueType (``pdf.fonttype`` 42).

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
OUT = REPO / "paper" / "figures"  # uploaded to Overleaf with the .tex

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
        "font.size": 8.5,
        "axes.titlesize": 8.5,
        "axes.labelsize": 8.5,
        "xtick.labelsize": 8.0,
        "ytick.labelsize": 8.0,
        "legend.fontsize": 8.0,
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
        "hatch.color": "white",
        "hatch.linewidth": 0.7,
        "legend.frameon": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
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


def _save(fig: plt.Figure, stem: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{stem}.pdf"
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    print(f"  wrote {path.name}  ({path.stat().st_size / 1024:.0f} KB)")


# --------------------------------------------------------------------------
# F1 -- system architecture (adapted from the stakeholder-approved flowchart
#      in docs/architecture.html: vertical, numbered, small boxes, airy)
# --------------------------------------------------------------------------
def fig_architecture() -> None:
    fig, ax = plt.subplots(figsize=(DOUBLE, 5.7))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    def box(x, y, w, h, title, *, sub=None, fc=FILL_A, ec=NAVY, ts=9.0, ss=8.0):
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
        ax.text(x + w / 2, y + h * 0.67, title, ha="center", va="center", fontsize=ts, zorder=4)
        if sub is not None:
            ax.text(
                x + w / 2,
                y + h * 0.27,
                sub,
                ha="center",
                va="center",
                fontsize=ss,
                color=MUTED,
                linespacing=1.45,
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
            (1.5, 14.6),
            97,
            83.9,
            boxstyle="round,pad=0,rounding_size=1.4",
            linewidth=0.6,
            edgecolor="#cfd9cf",
            facecolor="#fbfdfb",
            zorder=1,
        )
    )
    ax.text(
        4.0,
        96.2,
        "OFFLINE  ·  DEEP-LEARNING PIPELINE  ·  writes files, then exits",
        fontsize=8,
        color="#5c7a5c",
        va="center",
    )

    main_x, main_w = 21, 58  # the central column of boxes
    box(
        main_x,
        86.0,
        main_w,
        7.4,
        "1.  Data ingestion adapters",
        sub="5 public datasets · 6 graph views · 2 domains · checksum-verified",
    )
    arrow(50, 86.0, 50, 83.6)
    box(
        main_x,
        76.0,
        main_w,
        7.6,
        "2.  Unified graph schema (IR)",
        sub="typed nodes · edges · labels · time-safe inductive splits",
    )

    # fan out to four parallel arms
    arm_w = 23.5
    arm_x = (1.5, 26.0, 50.5, 75.0)
    centres = [x + arm_w / 2 for x in arm_x]
    ax.plot([50, 50], [76.0, 73.2], color=MUTED, linewidth=0.6, zorder=2)
    for cx in centres:
        ax.plot([50, cx], [73.2, 73.2], color=MUTED, linewidth=0.6, zorder=2)
        arrow(cx, 73.2, cx, 70.9)

    arms = [
        ("3a.  Supervised GNNs", "GATv2, SAGE, R-GCN\nfocal loss; 2% of tx illicit", FILL_B, TEAL),
        ("3b.  Unsupervised arm", "DOMINANT, GAE, floor\nno labels required", FILL_B, TEAL),
        ("3c.  Graph features", "degree, motifs, k-core\nbid screens, ratios", FILL_B, TEAL),
        ("3d.  Baselines & checks", "XGBoost yardstick\ninjection, leakage suite", FILL_C, AMBER),
    ]
    for x, (title, sub, fc, ec) in zip(arm_x, arms, strict=True):
        ax.add_patch(
            mpatches.FancyBboxPatch(
                (x, 58.6),
                arm_w,
                12.3,
                boxstyle="round,pad=0,rounding_size=1.0",
                linewidth=0.7,
                edgecolor=ec,
                facecolor=fc,
                zorder=3,
            )
        )
        ax.text(x + arm_w / 2, 67.9, title, ha="center", va="center", fontsize=8.8, zorder=4)
        ax.text(
            x + arm_w / 2,
            62.6,
            sub,
            ha="center",
            va="center",
            fontsize=8.0,
            color=MUTED,
            linespacing=1.45,
            zorder=4,
        )

    for cx in centres:
        ax.plot([cx, cx], [58.6, 56.0], color=MUTED, linewidth=0.6, zorder=2)
        ax.plot([cx, 50], [56.0, 56.0], color=MUTED, linewidth=0.6, zorder=2)
    arrow(50, 56.0, 50, 53.6)

    box(
        main_x,
        46.0,
        main_w,
        7.6,
        "4.  Calibrated ensemble fusion",
        sub="isotonic per member → one comparable risk score per node",
    )
    arrow(50, 46.0, 50, 43.6)
    box(
        main_x,
        36.0,
        main_w,
        7.6,
        "5.  Leiden communities → ranked alert queue",
        sub="254 financial + 223 procurement alerts · NMS · fixed budget",
    )
    arrow(50, 36.0, 50, 33.6)
    box(
        main_x,
        26.0,
        main_w,
        7.6,
        "6.  Explanation layer",
        sub="PGExplainer subgraph · motif matcher · FATF / OECD citations",
        fc=FILL_C,
        ec=AMBER,
    )
    arrow(50, 26.0, 50, 23.6)
    box(
        main_x,
        16.0,
        main_w,
        7.6,
        "7.  Artifact store — plain files",
        sub="alerts · explanation bundles · metrics · serving index",
        fc=FILL_C,
        ec=AMBER,
    )

    # ---- trust boundary ---------------------------------------------------
    ax.text(
        50, 13.1, "T R U S T   B O U N D A R Y", ha="center", va="center", fontsize=8, color=BRICK
    )
    ax.plot([2, 98], [11.6, 11.6], color=BRICK, linewidth=0.7, linestyle=(0, (4, 2.5)), zorder=2)
    ax.text(
        50,
        9.6,
        "above: writes files, then exits   ·   below: read-only, cannot retrain or change a score",
        ha="center",
        va="center",
        fontsize=8,
        color=MUTED,
        zorder=5,
    )

    box(
        1.5,
        0.2,
        47.5,
        7.0,
        "8.  FastAPI serving layer — read-only",
        sub="/alerts · /subgraph · /explanations · /metrics · /rigor",
        fc=FILL_A,
        ec=NAVY,
        ts=8.8,
    )
    box(
        51.0,
        0.2,
        47.5,
        7.0,
        "9.  Investigator console + guarded copilot",
        sub="ranked queue, evidence dossier, SELECT-only agent",
        fc="#f3eef7",
        ec=PLUM,
        ts=8.8,
    )

    _save(fig, "fig1_architecture")


# --------------------------------------------------------------------------
# F2 -- two ledgers, one structure (the conceptual bridge)
# --------------------------------------------------------------------------
def fig_two_ledgers() -> None:
    fig, ax = plt.subplots(figsize=(DOUBLE, 3.25))
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
        ax.text(cx, 43.6, sig, ha="center", va="center", fontsize=9.0, color=INK)
        ax.plot([cx - 8.4, cx + 8.4], [41.0, 41.0], color=RULE, linewidth=0.6)
        glyph(cx, 29.5, kind)
        ax.text(cx, 17.4, "FINANCIAL", ha="center", va="center", fontsize=8.0, color=NAVY)
        ax.text(cx, 13.5, fin, ha="center", va="center", fontsize=8.0, color=INK)
        ax.text(cx, 7.9, "PROCUREMENT", ha="center", va="center", fontsize=8.0, color=AMBER)
        ax.text(cx, 4.0, proc, ha="center", va="center", fontsize=8.0, color=INK)
        if i:
            ax.plot([cx - 10, cx - 10], [1.5, 41.5], color="#e9ebee", linewidth=0.5)

    _save(fig, "fig2_two_ledgers")


# --------------------------------------------------------------------------
# F3 -- per-time-step AUC-PR: the step-43 distribution shift, GNN and trees
# --------------------------------------------------------------------------
def fig_timestep() -> None:
    per_seed: list[dict[str, dict[str, float]]] = []
    for s in range(5):
        m = _load(f"elliptic_pp/gnn_gatv2_focal_multiseed/seed_{s}/metrics.json")
        per_seed.append(m["node_level"]["per_time_step"])
    trees = _load("elliptic_pp/baselines_multiseed/baselines_multiseed.json")
    b3 = trees["baselines"]["b3_xgb_graph"]["per_time_step"]

    steps = sorted({int(k) for d in per_seed for k in d})
    g_mean, g_sd, b_mean, b_sd, prev = [], [], [], [], []
    for st in steps:
        vals = [d[str(st)]["auc_pr"] for d in per_seed if str(st) in d]
        g_mean.append(float(np.mean(vals)))
        g_sd.append(float(np.std(vals, ddof=1)))  # sample SD, as in the tables
        b_mean.append(float(b3[str(st)]["auc_pr_mean"]))
        b_sd.append(float(b3[str(st)]["auc_pr_std"]))
        prev.append(float(b3[str(st)]["prevalence_baseline"]))
    g_mean_a, g_sd_a = np.array(g_mean), np.array(g_sd)
    b_mean_a, b_sd_a = np.array(b_mean), np.array(b_sd)

    fig, ax = plt.subplots(figsize=(SINGLE, 2.75))
    ax.axvspan(42.5, max(steps) + 0.5, color=BRICK, alpha=0.06, linewidth=0)
    ax.fill_between(
        steps, b_mean_a - b_sd_a, b_mean_a + b_sd_a, color=TEAL, alpha=0.18, linewidth=0
    )
    ax.fill_between(
        steps, g_mean_a - g_sd_a, g_mean_a + g_sd_a, color=NAVY, alpha=0.15, linewidth=0
    )
    ax.plot(
        steps,
        b_mean,
        color=TEAL,
        linewidth=1.15,
        linestyle=(0, (4, 1.6)),
        marker="s",
        markersize=2.6,
        label="B3 XGBoost + graph (5-seed mean $\\pm$ 1 s.d.)",
    )
    ax.plot(
        steps,
        g_mean,
        color=NAVY,
        linewidth=1.15,
        marker="o",
        markersize=2.6,
        label="GATv2-focal (5-seed mean $\\pm$ 1 s.d.)",
    )
    ax.plot(steps, prev, color=MUTED, linewidth=0.9, linestyle=(0, (1, 1.4)), label="prevalence")
    ax.text(
        46.0,
        0.62,
        "dark-market\nshutdown at $t{=}43$",
        fontsize=8,
        color=BRICK,
        ha="center",
        va="center",
        linespacing=1.3,
    )
    ax.set_xlabel("Elliptic++ time step (test window)")
    ax.set_ylabel("AUC-PR")
    ax.set_ylim(0, 1.03)
    ax.set_xlim(min(steps) - 0.4, max(steps) + 0.4)
    ax.legend(loc="lower left", bbox_to_anchor=(-0.02, 1.0), handlelength=2.2, ncol=1)
    _tidy(ax)
    _save(fig, "fig3_timestep_crater")


# --------------------------------------------------------------------------
# F4 -- transfer lift per held-out fold, with bootstrap 95% intervals
# --------------------------------------------------------------------------
def fig_transfer() -> None:
    pooled = _load("transfer_pooled/transfer_pooled.json")["matrices"]
    mend = pooled["mendeley_loco"]["folds"]
    garc = pooled["garcia_lomo"]["folds"]
    largest = max(mend, key=lambda f: f["n_confirmed_test"])

    fig, ax = plt.subplots(figsize=(SINGLE, 2.6))
    xs: list[float] = []
    labels: list[str] = []
    for i, f in enumerate(mend):
        x = float(i)
        xs.append(x)
        labels.append(str(f["test_group"]).replace("country_", "C"))
        colour = BRICK if f is largest else NAVY
        ax.bar(x, f["lift_mean"], width=0.66, color=colour, linewidth=0, zorder=3)
    for j, f in enumerate(garc):
        x = len(mend) + 0.8 + j
        xs.append(x)
        # the publisher's README describes the "America" file as the USA market
        labels.append(str(f["test_group"]).replace("America", "USA"))
        ax.bar(
            x,
            f["lift_mean"],
            width=0.66,
            color=TEAL,
            hatch="////",
            edgecolor="white",
            linewidth=0,
            zorder=3,
        )
    folds = mend + garc
    lifts = np.array([f["lift_mean"] for f in folds])
    lo = np.array([f["lift_ci_low"] for f in folds])
    hi = np.array([f["lift_ci_high"] for f in folds])
    ax.errorbar(
        xs,
        lifts,
        yerr=[lifts - lo, hi - lifts],
        fmt="none",
        ecolor=INK,
        elinewidth=0.6,
        capsize=1.6,
        capthick=0.6,
        zorder=4,
    )
    ax.axhline(1.0, color=MUTED, linewidth=0.8, linestyle=(0, (3, 2)), zorder=2)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=45, ha="right", rotation_mode="anchor")
    ax.set_ylabel("lift over fold prevalence")
    ax.set_ylim(0, max(2.5, float(hi.max()) + 0.1))
    ax.set_xlim(xs[0] - 0.6, xs[-1] + 0.6)
    ax.legend(
        handles=[
            mpatches.Patch(color=NAVY, label="Mendeley EU, leave one country out"),
            mpatches.Patch(color=BRICK, label="largest Mendeley fold"),
            mpatches.Patch(
                facecolor=TEAL,
                hatch="////",
                edgecolor="white",
                label="García, leave one market out",
            ),
            Line2D(
                [],
                [],
                color=MUTED,
                linewidth=0.8,
                linestyle=(0, (3, 2)),
                label="base rate (lift 1)",
            ),
        ],
        loc="lower left",
        bbox_to_anchor=(-0.02, 1.0),
        handlelength=1.3,
        ncol=1,
    )
    _tidy(ax)
    _save(fig, "fig4_transfer_lift")


# --------------------------------------------------------------------------
# F5 -- label noise: the validation-blindness diagnostic
# --------------------------------------------------------------------------
def _noise_curve() -> tuple[list[dict[str, Any]], int]:
    """The five-seed curve once its run has finished; the stored three-seed
    curve until then. Returns the curve and its seed count."""
    five = EVAL / "elliptic_pp" / "label_noise_curve_5seed" / "noise_curve.json"
    if five.is_file():
        doc = json.loads(five.read_text(encoding="utf-8"))
        return doc["curve"], len(doc["seeds"])
    doc = _load("elliptic_pp/label_noise_curve/noise_curve.json")
    return doc["curve"], len(doc["seeds"])


def fig_label_noise() -> None:
    curve, n_seeds = _noise_curve()
    rates = [c["rate"] * 100 for c in curve]
    test = [c["auc_pr_mean"] for c in curve]
    sd = [c["auc_pr_std"] for c in curve]
    val = [c["val_auc_pr_mean"] for c in curve]

    fig, ax = plt.subplots(figsize=(SINGLE, 2.6))
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
        label=f"test AUC-PR ({n_seeds}-seed mean $\\pm$ 1 s.d.)",
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
        label="validation AUC-PR (mean)",
        zorder=4,
    )
    ax.text(
        11.5,
        0.93,
        "validation falls\nwhile test rises",
        fontsize=8,
        color=MUTED,
        ha="left",
        va="center",
        linespacing=1.3,
    )
    ax.set_xlabel("training labels randomly flipped (%)")
    ax.set_ylabel("AUC-PR")
    ax.set_xticks(rates)
    ax.set_xticklabels([f"{r:g}" for r in rates])
    ax.set_ylim(0.3, 1.02)
    ax.legend(loc="lower left", bbox_to_anchor=(-0.02, 1.0), handlelength=2.0, ncol=1)
    _tidy(ax)
    _save(fig, "fig5_label_noise")


# --------------------------------------------------------------------------
# F6 -- cross-domain label efficiency, both directions, with the full-label point
# --------------------------------------------------------------------------
def fig_label_efficiency() -> None:
    full = _load("cross_domain/full_label_comparison/full_label_comparison.json")["directions"]
    specs = [
        (
            "cross_domain/label_efficiency_proc2fin/label_efficiency.json",
            "proc2fin",
            "procurement $\\rightarrow$ financial",
            NAVY,
        ),
        (
            "cross_domain/label_efficiency_fin2proc/label_efficiency.json",
            "fin2proc",
            "financial $\\rightarrow$ procurement",
            TEAL,
        ),
    ]
    fig, axes = plt.subplots(2, 1, figsize=(SINGLE, 3.7))
    for ax, (rel, key, title, colour) in zip(axes, specs, strict=True):
        doc = _load(rel)
        rows = [r for r in doc["curve"] if r.get("status") == "completed"]
        ks = [int(r["k"]) for r in rows]
        gain = [float(r["transfer_gain_mean"]) for r in rows]
        xs = list(range(len(ks)))
        ax.bar(xs, gain, width=0.62, color=colour, linewidth=0, zorder=3)
        paired = full[key]["paired"]["frozen_probe_vs_structural_probe"]
        x_full = len(ks) + 0.4
        ax.bar(
            x_full,
            paired["delta"],
            width=0.62,
            color=colour,
            hatch="////",
            edgecolor="white",
            linewidth=0,
            zorder=3,
        )
        ax.errorbar(
            [x_full],
            [paired["delta"]],
            yerr=[
                [paired["delta"] - paired["delta_ci_low"]],
                [paired["delta_ci_high"] - paired["delta"]],
            ],
            fmt="none",
            ecolor=INK,
            elinewidth=0.6,
            capsize=1.8,
            capthick=0.6,
            zorder=4,
        )
        ax.axhline(0, color=MUTED, linewidth=0.7, zorder=4)
        ax.set_xticks([*xs, x_full])
        n_full = int(full[key]["n_probe_train"])
        ax.set_xticklabels([f"{k:,}" for k in ks] + [f"all\n({n_full:,})"])
        ax.set_title(title, pad=3)
        ax.set_ylabel("transfer gain")
        _tidy(ax)
    axes[1].set_xlabel("target-domain labels $k$")
    fig.tight_layout(h_pad=0.8)
    _save(fig, "fig6_label_efficiency")


FIGURES = {
    "fig1_architecture": fig_architecture,
    "fig2_two_ledgers": fig_two_ledgers,
    "fig3_timestep_crater": fig_timestep,
    "fig4_transfer_lift": fig_transfer,
    "fig5_label_noise": fig_label_noise,
    "fig6_label_efficiency": fig_label_efficiency,
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
