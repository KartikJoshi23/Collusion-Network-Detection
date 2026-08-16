"""Generate the paper's figures as PNGs in the repo root, and print the exact
numbers used in the manuscript so nothing is transcribed by hand.

Run:  uv run python scripts/paper_figures.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

REPO = Path(__file__).resolve().parents[1]
DPI = 200

# ----------------------------------------------------------------- palette
INK = "#1a1a1a"
MUTED = "#5b6472"
FIN = "#2563eb"  # financial / money — blue
PROC = "#7c3aed"  # procurement — violet
GOOD = "#15a34a"
BAD = "#d64545"
AMBER = "#b45309"
LINE = "#c8cdd6"
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.edgecolor": MUTED,
        "text.color": INK,
        "axes.labelcolor": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
    }
)


def _box(ax, x, y, w, h, text, fc, ec, fs=8.5, tc=None):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.008,rounding_size=0.02",
            linewidth=1.3,
            edgecolor=ec,
            facecolor=fc,
        )
    )
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=tc or INK)


def _arrow(ax, x1, y1, x2, y2, color=MUTED, style="-|>", lw=1.3):
    ax.add_patch(
        FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=11, color=color, lw=lw)
    )


# ============================================================ FIG 1: pipeline
def fig_pipeline():
    fig, ax = plt.subplots(figsize=(7.1, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.6)
    ax.axis("off")

    # offline cluster
    ax.add_patch(
        FancyBboxPatch(
            (0.1, 1.55),
            9.8,
            2.9,
            boxstyle="round,pad=0.02,rounding_size=0.05",
            linewidth=1.1,
            edgecolor=GOOD,
            facecolor="#15a34a10",
            linestyle=(0, (5, 3)),
        )
    )
    ax.text(
        0.28,
        4.25,
        "OFFLINE PIPELINE  (trains, writes files, exits)",
        fontsize=7.5,
        color=GOOD,
        weight="bold",
    )

    _box(ax, 0.4, 3.4, 1.7, 0.66, "Six public\ndatasets", "#eef2f9", MUTED, 7.6)
    _box(ax, 2.5, 3.4, 1.9, 0.66, "Unified graph\nschema (IR)", "#eef2f9", INK, 7.8)
    _arrow(ax, 2.1, 3.73, 2.5, 3.73)

    arms = [
        ("Supervised\nGNNs", FIN),
        ("Unsupervised\nautoencoders", PROC),
        ("Structural\nfeatures", AMBER),
        ("Classical\nbaselines", MUTED),
    ]
    for i, (t, c) in enumerate(arms):
        _box(ax, 4.75 + i * 1.28, 3.35, 1.16, 0.75, t, "#ffffff", c, 6.9)
        _arrow(ax, 4.4, 3.73, 4.75 + i * 1.28, 3.73, LINE, "-", 0.9)

    _box(ax, 3.3, 2.45, 3.4, 0.6, "Calibrated ensemble fusion", "#ffffff", FIN, 8.4)
    for i in range(4):
        _arrow(ax, 4.75 + i * 1.28 + 0.58, 3.35, 5.0, 3.05, LINE, "-", 0.8)

    _box(ax, 1.7, 1.72, 3.1, 0.58, "Leiden roll-up → ranked queue", "#ffffff", GOOD, 8.2)
    _box(ax, 5.2, 1.72, 3.1, 0.58, "Explanation + motif match", "#ffffff", AMBER, 8.2)
    _arrow(ax, 4.3, 2.45, 3.3, 2.3)
    _arrow(ax, 5.7, 2.45, 6.7, 2.3)

    # trust boundary
    ax.plot([0.1, 9.9], [1.35, 1.35], color=BAD, lw=1.3, linestyle=(0, (6, 4)))
    ax.text(
        5.0,
        1.42,
        "TRUST BOUNDARY  ·  below reads only, cannot retrain or alter a score",
        ha="center",
        fontsize=6.8,
        color=BAD,
        weight="bold",
    )

    _box(ax, 0.4, 0.45, 2.4, 0.66, "Read-only API", "#eef2f9", FIN, 8)
    _box(ax, 3.1, 0.45, 3.0, 0.66, "Investigator console\n(7 views)", "#eef2f9", INK, 7.6)
    _box(ax, 6.4, 0.45, 3.1, 0.66, "GenAI Copilot\n(grounded, guarded)", "#eef2f9", PROC, 7.4)
    _arrow(ax, 5.0, 1.35, 5.0, 1.11, BAD, "-|>", 1.1)

    fig.tight_layout(pad=0.3)
    out = REPO / "fig_pipeline.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", out.name)


# ======================================================= FIG 2: joint graph
def fig_joint_graph():
    import numpy as np

    fig, ax = plt.subplots(figsize=(7.1, 3.0))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.2)
    ax.axis("off")

    ax.text(
        2.3, 3.95, "Financial layer  (pays)", ha="center", fontsize=8.5, color=FIN, weight="bold"
    )
    ax.text(
        7.7,
        3.95,
        "Procurement layer  (bids-on / awarded)",
        ha="center",
        fontsize=8.5,
        color=PROC,
        weight="bold",
    )

    # financial ring (accounts)
    fc = np.array([2.3, 2.1])
    fin_nodes = (
        fc
        + 1.0
        * np.c_[
            np.cos(np.linspace(0, 2 * np.pi, 7)[:-1]), np.sin(np.linspace(0, 2 * np.pi, 7)[:-1])
        ]
    )
    for i in range(len(fin_nodes)):
        a, b = fin_nodes[i], fin_nodes[(i + 1) % len(fin_nodes)]
        _arrow(ax, a[0], a[1], b[0], b[1], FIN, "-|>", 1.0)
    ax.scatter(
        fin_nodes[:, 0],
        fin_nodes[:, 1],
        s=150,
        c="#ffffff",
        edgecolors=FIN,
        linewidths=1.6,
        zorder=3,
    )

    # procurement bipartite-ish cluster (firms + tenders)
    pc = np.array([7.7, 2.1])
    firms = pc + np.c_[[-1.0, -1.0, -1.0], [0.9, 0.0, -0.9]]
    tenders = pc + np.c_[[0.7, 0.7], [0.5, -0.5]]
    for f in firms:
        for t in tenders:
            _arrow(ax, f[0], f[1], t[0], t[1], PROC, "-", 0.8)
    ax.scatter(
        firms[:, 0], firms[:, 1], s=150, c="#ffffff", edgecolors=PROC, linewidths=1.6, zorder=3
    )
    ax.scatter(
        tenders[:, 0],
        tenders[:, 1],
        s=90,
        marker="s",
        c="#f3eefe",
        edgecolors=PROC,
        linewidths=1.3,
        zorder=3,
    )

    # the DUAL ACTOR — one node bridging both layers
    dual = np.array([5.0, 2.1])
    ax.scatter(*dual, s=340, c=AMBER, edgecolors=INK, linewidths=1.6, zorder=5, marker="H")
    ax.text(
        5.0,
        1.35,
        "dual actor\n(shared control)",
        ha="center",
        fontsize=7.2,
        color=AMBER,
        weight="bold",
    )
    # bridges: dual actor into both layers
    _arrow(ax, dual[0], dual[1], fin_nodes[0][0], fin_nodes[0][1], AMBER, "-|>", 1.4)
    _arrow(ax, dual[0], dual[1], firms[1][0], firms[1][1], AMBER, "-|>", 1.4)
    _arrow(ax, dual[0], dual[1], firms[0][0], firms[0][1], AMBER, "-|>", 1.1)

    ax.text(
        5.0,
        0.55,
        "One heterogeneous graph. The common-control motif is the seam a joint model\n"
        "message-passes across — raising the prior on a firm in one layer "
        "from its behaviour in the other.",
        ha="center",
        fontsize=6.9,
        color=MUTED,
    )

    fig.tight_layout(pad=0.3)
    out = REPO / "fig_joint_graph.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", out.name)


# =============================================== FIG 3: injection recovery (real)
def fig_injection_recovery():
    art = REPO / "eval_outputs/ocds_georgia/injection_recovery_multiseed/injection_multiseed.json"
    if not art.is_file():
        print("SKIP injection figure — artifact missing")
        return
    d = json.loads(art.read_text(encoding="utf-8"))
    rm = d["recovery_multiseed"]
    budget = "recall@2000"
    # best arm per shape at the top budget (matches the report/dashboard reading)
    best: dict[str, tuple[float, float]] = {}
    for _arm, motifs in rm.items():
        for motif, entry in motifs.items():
            v = entry.get(budget)
            if isinstance(v, dict) and "mean" in v:
                m, s = float(v["mean"]), float(v.get("std", 0.0))
                if motif not in best or m > best[motif][0]:
                    best[motif] = (m, s)

    label = {
        "coordinated_cluster": "Bid-together ring",
        "common_control": "Hidden common owner",
        "partition": "Market carve-up",
        "rotation": "Take-turns",
        "cover_bid": "Cover bidding",
    }
    order = ["coordinated_cluster", "common_control", "partition", "rotation", "cover_bid"]
    shapes = [m for m in order if m in best]
    means = [best[m][0] * 100 for m in shapes]
    stds = [best[m][1] * 100 for m in shapes]
    names = [label.get(m, m) for m in shapes]
    colors = [GOOD if v >= 60 else (AMBER if v >= 30 else BAD) for v in means]

    print("Injection recovery (best arm, recall@2000, % ± std):")
    for n, m, s in zip(names, means, stds, strict=True):
        print(f"   {n:22s} {m:5.1f}% ± {s:4.1f}")

    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    y = range(len(shapes))
    ax.barh(
        list(y),
        means,
        xerr=stds,
        color=colors,
        edgecolor=INK,
        linewidth=0.6,
        height=0.62,
        error_kw=dict(ecolor=MUTED, lw=1),
    )
    ax.set_yticks(list(y))
    ax.set_yticklabels(names, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("recovered at top 2000 (%)", fontsize=8)
    ax.set_xlim(0, 100)
    for i, (m, s) in enumerate(zip(means, stds, strict=True)):
        ax.text(min(m + s + 2, 96), i, f"{m:.0f}%", va="center", fontsize=7.5, color=INK)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(pad=0.3)
    out = REPO / "fig_injection_recovery.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", out.name)


if __name__ == "__main__":
    fig_pipeline()
    fig_joint_graph()
    fig_injection_recovery()
    print("done.")
