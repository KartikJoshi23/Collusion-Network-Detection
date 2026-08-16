"""Generate the paper's figures as high-resolution PNGs in the repo root.

These are clean, accurate reference images (300 DPI) sized for a two-column
paper; upload them to Overleaf next to the .tex, or import into Canva to
polish. The script also prints the exact numbers used so nothing is transcribed
by hand.

    uv run python scripts/paper_figures.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

REPO = Path(__file__).resolve().parents[1]
DPI = 300

# ---- professional, print-muted palette -------------------------------------
INK = "#1B2430"
MUTED = "#6B7280"
FIN = "#2F5C8F"  # money / financial
PROC = "#6A4C93"  # procurement
GOOD = "#2E7D5B"
AMBER = "#B0701A"
BAD = "#B0413E"
ARROW = "#8A93A0"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10.5,
        "text.color": INK,
        "axes.edgecolor": MUTED,
    }
)


def _tint(hex_color: str, amount: float = 0.10) -> tuple:
    """Blend a colour toward white (soft fill)."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return tuple(c + (1 - c) * (1 - amount) for c in (r, g, b))


def _box(ax, cx, cy, w, h, text, color, fs=10.5, bold=False):
    ax.add_patch(
        FancyBboxPatch(
            (cx - w / 2, cy - h / 2),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.10",
            linewidth=1.6,
            edgecolor=color,
            facecolor=_tint(color),
        )
    )
    ax.text(
        cx,
        cy,
        text,
        ha="center",
        va="center",
        fontsize=fs,
        color=INK,
        weight="bold" if bold else "normal",
        linespacing=1.15,
    )


def _arrow(ax, p1, p2, color=ARROW, lw=1.6, head=True):
    ax.add_patch(
        FancyArrowPatch(
            p1,
            p2,
            arrowstyle="-|>" if head else "-",
            mutation_scale=14,
            color=color,
            lw=lw,
            shrinkA=2,
            shrinkB=2,
        )
    )


# ============================================================ FIG 1: pipeline
def fig_pipeline():
    fig, ax = plt.subplots(figsize=(8.2, 6.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 11)
    ax.axis("off")

    _box(ax, 2.3, 10.1, 3.0, 0.95, "Six public\ndatasets", MUTED, 10)
    _box(ax, 6.7, 10.1, 3.4, 0.95, "Unified graph schema (IR)", INK, 10)
    _arrow(ax, (3.8, 10.1), (5.0, 10.1))

    arms = [
        (1.55, "Supervised\nGNNs", FIN),
        (4.05, "Unsupervised\nautoencoders", PROC),
        (6.4, "Structural\nfeatures", AMBER),
        (8.6, "Classical\nbaselines", MUTED),
    ]
    for cx, label, col in arms:
        _box(ax, cx, 8.35, 2.05, 1.05, label, col, 9.5)
        _arrow(ax, (6.7, 9.55), (cx, 8.9), color="#B8BEC6", lw=1.0)

    _box(ax, 5.0, 6.55, 4.4, 0.95, "Calibrated ensemble fusion", FIN, 10.5, bold=True)
    for cx, _l, _c in arms:
        _arrow(ax, (cx, 7.8), (5.0, 7.05), color="#B8BEC6", lw=1.0, head=False)

    _box(ax, 2.9, 5.0, 3.7, 0.95, "Leiden roll-up\n$\\rightarrow$ ranked queue", GOOD, 9.8)
    _box(ax, 7.1, 5.0, 3.7, 0.95, "Explanation +\nmotif match", AMBER, 9.8)
    _arrow(ax, (4.4, 6.1), (3.2, 5.5))
    _arrow(ax, (5.6, 6.1), (6.8, 5.5))

    # offline group boundary
    ax.add_patch(
        FancyBboxPatch(
            (0.25, 4.35),
            9.5,
            6.35,
            boxstyle="round,pad=0.02,rounding_size=0.15",
            linewidth=1.3,
            edgecolor=GOOD,
            facecolor="none",
            linestyle=(0, (6, 4)),
        )
    )
    ax.text(
        0.5,
        10.85,
        "OFFLINE PIPELINE — trains, writes files, then exits",
        fontsize=8.5,
        color=GOOD,
        weight="bold",
    )

    # trust boundary
    ax.plot([0.25, 9.75], [3.75, 3.75], color=BAD, lw=1.5, linestyle=(0, (7, 4)))
    ax.text(
        5.0, 3.95, "T R U S T   B O U N D A R Y", ha="center", fontsize=9, color=BAD, weight="bold"
    )
    ax.text(
        5.0,
        3.42,
        "below: read-only — cannot retrain or alter a score",
        ha="center",
        fontsize=8,
        color=BAD,
    )
    _arrow(ax, (5.0, 3.75), (5.0, 2.85), color=BAD, lw=1.4)

    _box(ax, 1.75, 2.2, 2.7, 0.95, "Read-only\nAPI", FIN, 9.8)
    _box(ax, 5.0, 2.2, 3.0, 0.95, "Investigator\nconsole (7 views)", INK, 9.8)
    _box(ax, 8.25, 2.2, 2.7, 0.95, "GenAI Copilot\ngrounded, guarded", PROC, 9.5)

    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    out = REPO / "fig_pipeline.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight", facecolor="white", pad_inches=0.08)
    plt.close(fig)
    print("wrote", out.name)


# ======================================================= FIG 2: joint graph
def fig_joint_graph():
    import numpy as np

    fig, ax = plt.subplots(figsize=(8.2, 3.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.4)
    ax.axis("off")

    ax.text(2.0, 4.05, "Financial layer", ha="center", fontsize=11, color=FIN, weight="bold")
    ax.text(2.0, 3.62, "money through a ring of accounts", ha="center", fontsize=8.5, color=MUTED)
    ax.text(8.0, 4.05, "Procurement layer", ha="center", fontsize=11, color=PROC, weight="bold")
    ax.text(8.0, 3.62, "firms bidding on tenders", ha="center", fontsize=8.5, color=MUTED)

    # financial ring (directed laundering cycle)
    fc = np.array([2.0, 1.9])
    ang = np.linspace(90, 90 - 360, 7)[:-1] * np.pi / 180
    ring = fc + 1.05 * np.c_[np.cos(ang), np.sin(ang)]
    for i in range(len(ring)):
        a, b = ring[i], ring[(i + 1) % len(ring)]
        _arrow(ax, a, b, color=FIN, lw=1.5)
    ax.scatter(ring[:, 0], ring[:, 1], s=260, c="white", edgecolors=FIN, linewidths=2.0, zorder=4)

    # procurement bipartite cluster
    pc = np.array([8.0, 1.9])
    firms = pc + np.c_[[-1.15, -1.15, -1.15], [1.0, 0.0, -1.0]]
    tenders = pc + np.c_[[0.75, 0.75], [0.55, -0.55]]
    for f in firms:
        for t in tenders:
            ax.plot([f[0], t[0]], [f[1], t[1]], color=PROC, lw=0.9, alpha=0.55, zorder=1)
    ax.scatter(
        firms[:, 0], firms[:, 1], s=260, c="white", edgecolors=PROC, linewidths=2.0, zorder=4
    )
    ax.scatter(
        tenders[:, 0],
        tenders[:, 1],
        s=150,
        marker="s",
        c="white",
        edgecolors=PROC,
        linewidths=1.6,
        zorder=4,
    )

    # dual actor bridging both layers
    dual = np.array([5.0, 1.9])
    ax.scatter(*dual, s=620, c=AMBER, edgecolors=INK, linewidths=2.0, zorder=6, marker="H")
    _arrow(ax, dual, ring[3], color=AMBER, lw=2.2)
    _arrow(ax, dual, firms[1], color=AMBER, lw=2.2)
    _arrow(ax, dual, firms[0], color=AMBER, lw=1.6)
    ax.text(5.0, 0.95, "dual actor", ha="center", fontsize=9.5, color=AMBER, weight="bold")
    ax.text(5.0, 0.6, "(shared control)", ha="center", fontsize=8.5, color=AMBER)

    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    out = REPO / "fig_joint_graph.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight", facecolor="white", pad_inches=0.06)
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
    best: dict[str, tuple[float, float]] = {}
    for _arm, motifs in rm.items():
        for motif, entry in motifs.items():
            v = entry.get(budget)
            if isinstance(v, dict) and "mean" in v:
                m, s = float(v["mean"]), float(v.get("std", 0.0))
                if motif not in best or m > best[motif][0]:
                    best[motif] = (m, s)

    meta = {
        "coordinated_cluster": ("Bid-together ring", GOOD, "CAUGHT"),
        "common_control": ("Hidden common owner", AMBER, "PARTIAL"),
        "partition": ("Market carve-up", BAD, "ESCAPES"),
        "rotation": ("Take-turns", BAD, "ESCAPES"),
        "cover_bid": ("Cover bidding", BAD, "ESCAPES"),
    }
    order = ["coordinated_cluster", "common_control", "partition", "rotation", "cover_bid"]
    rows = [m for m in order if m in best]
    means = [best[m][0] * 100 for m in rows]
    stds = [best[m][1] * 100 for m in rows]

    print("Injection recovery (best arm, recall@2000, % +/- std):")
    for m in rows:
        print(f"   {meta[m][0]:22s} {best[m][0]*100:5.1f}% +/- {best[m][1]*100:4.1f}")

    fig, ax = plt.subplots(figsize=(7.4, 3.1))
    y = list(range(len(rows)))[::-1]
    for yi, m, mean, sd in zip(y, rows, means, stds, strict=True):
        _label, col, verd = meta[m]
        ax.barh(
            yi,
            mean,
            xerr=sd,
            height=0.6,
            color=_tint(col, 0.85),
            edgecolor=col,
            linewidth=1.4,
            error_kw=dict(ecolor=MUTED, lw=1.1, capsize=3),
        )
        ax.text(
            mean + sd + 3,
            yi,
            f"{mean:.0f}%   {verd}",
            va="center",
            ha="left",
            fontsize=10,
            color=col,
            weight="bold",
        )

    ax.set_yticks(y)
    ax.set_yticklabels([meta[m][0] for m in rows], fontsize=10)
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.tick_params(labelsize=9)
    ax.set_xlabel("recovered at top 2000 reviewed (%)", fontsize=9.5)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)

    fig.subplots_adjust(left=0.28, right=0.98, top=0.97, bottom=0.16)
    out = REPO / "fig_injection_recovery.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight", facecolor="white", pad_inches=0.06)
    plt.close(fig)
    print("wrote", out.name)


if __name__ == "__main__":
    fig_pipeline()
    fig_joint_graph()
    fig_injection_recovery()
    print("done.")
