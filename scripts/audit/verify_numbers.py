"""Check the report's quoted numbers against the actual stored artifacts."""

import json
from pathlib import Path

ROOT = Path(r"D:/MAIB/Term - 3/Deep Learning/Collusion-Network-Detection")


def load(rel):
    p = ROOT / rel
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


checks = []


def chk(name, claimed, actual, tol=0.0006):
    if actual is None:
        checks.append((name, claimed, "ARTIFACT MISSING", "?"))
        return
    ok = abs(claimed - actual) <= tol
    checks.append((name, claimed, round(actual, 4), "OK" if ok else "*** MISMATCH ***"))


# Elliptic baselines
sb = load("eval_outputs/elliptic_pp/baselines/scoreboard.json")
if sb:
    b = sb["baselines"]
    chk("B1 rules AUC-PR", 0.0576, b["b1_rules"]["auc_pr"])
    chk("B2 XGB AUC-PR", 0.8076, b["b2_xgb"]["auc_pr"])
    chk("B3 XGB-Graph AUC-PR", 0.8104, b["b3_xgb_graph"]["auc_pr"])

# Mendeley baselines
mb = load("eval_outputs/mendeley_eu/baselines/scoreboard.json")
if mb:
    b = mb["baselines"]
    chk("Mendeley B1", 0.3426, b["b1_rules"]["auc_pr"])
    chk("Mendeley B2", 0.3925, b["b2_xgb"]["auc_pr"])
    chk("Mendeley B3", 0.3775, b["b3_xgb_graph"]["auc_pr"])
    chk("Mendeley B4", 0.3811, b["b4_screens"]["auc_pr"])
ms = load("eval_outputs/mendeley_eu/baselines_screens_ablation/scoreboard.json")
if ms:
    chk("Mendeley B2+screens", 0.4558, ms["baselines"]["b2_xgb"]["auc_pr"])

# GNN multiseed
f = load("eval_outputs/elliptic_pp/gnn_gatv2_focal_multiseed/multiseed.json")
if f:
    chk("GATv2-focal 5-seed mean", 0.4729, f["aggregate"]["auc_pr_mean"])
    chk("GATv2-focal 5-seed std", 0.0525, f["aggregate"]["auc_pr_std"])
    chk("GATv2-focal P@100 mean", 0.812, f["aggregate"]["precision@100_mean"], 0.002)
w = load("eval_outputs/elliptic_pp/gnn_gatv2_wce_multiseed/multiseed.json")
if w:
    chk("GATv2-wce 5-seed mean", 0.4388, w["aggregate"]["auc_pr_mean"])
    chk("GATv2-wce 5-seed std", 0.0505, w["aggregate"]["auc_pr_std"])
    chk("GATv2-wce P@100 mean", 0.724, w["aggregate"]["precision@100_mean"], 0.002)

# ensemble
e = load("eval_outputs/elliptic_pp/ensemble_multiseed/ensemble_multiseed.json")
if e:
    m = e["members"]
    chk("calibrated ensemble", 0.4434, m["ensemble_calibrated"]["auc_pr_mean"])
    chk("rank fusion", 0.0511, m["ensemble_rank"]["auc_pr_mean"])
    chk("rank fusion std", 0.0019, m["ensemble_rank"]["auc_pr_std"])
    chk("supervised (=-unsup arm)", 0.4729, m["supervised"]["auc_pr_mean"])

# seed-0 ablation arms
for d, claimed in [
    ("gnn_gatv2_focal", 0.5492),
    ("gnn_gatv2_focal_unidir", 0.3549),
    ("gnn_gatv2_focal_multi", 0.3781),
    ("gnn_gatv2_focal_line", 0.4986),
]:
    r = load(f"eval_outputs/elliptic_pp/{d}/run.json")
    chk(f"seed0 {d}", claimed, r["node_level"]["auc_pr"] if r else None)

# Mendeley R-GCN
rg = load("eval_outputs/mendeley_eu/gnn_rgcn_focal_multiseed/multiseed.json")
if rg:
    chk("R-GCN 5-seed mean", 0.2808, rg["aggregate"]["auc_pr_mean"])
    chk("R-GCN 5-seed std", 0.0087, rg["aggregate"]["auc_pr_std"])

# OCDS injection
inj = load("eval_outputs/ocds_georgia/injection_recovery_multiseed/injection_multiseed.json")
if inj:
    rec = inj["recovery_multiseed"]
    chk(
        "coordinated_cluster rank-fusion @2000",
        0.9225,
        rec["ensemble_rank"]["coordinated_cluster"]["recall@2000"]["mean"],
    )
    chk("floor common_control @2000", 0.4286, rec["floor"]["common_control"]["recall@2000"]["mean"])
    chk("floor common_control std", 0.0, rec["floor"]["common_control"]["recall@2000"]["std"])
    best = lambda mo: max(rec[a][mo]["recall@2000"]["mean"] for a in rec if mo in rec[a])
    chk("rotation best-arm @2000", 0.084, best("rotation"), 0.001)
    chk("partition best-arm @2000", 0.172, best("partition"), 0.001)
    chk("cover_bid best-arm @2000", 0.010, best("cover_bid"), 0.001)
    tot = sum(rec["floor"][m]["n_members"] for m in rec["floor"])
    chk("planted members total", 940, tot, 0)
    chk("population", 163327, inj["population"], 0)

# transfer
lo = load("eval_outputs/mendeley_eu/transfer_loco_matrix/matrix.json")
if lo:
    chk("Mendeley macro lift", 1.17, lo["summary"]["macro_lift_mean"], 0.006)
    worst = min(f["lift_mean"] for f in lo["folds"] if f.get("status") == "completed")
    chk("Mendeley worst fold lift", 0.90, worst, 0.006)
lm = load("eval_outputs/garcia_rodriguez/transfer_lomo_matrix/matrix.json")
if lm:
    chk("Garcia macro lift", 1.57, lm["summary"]["macro_lift_mean"], 0.006)

# label noise
ln = load("eval_outputs/elliptic_pp/label_noise_curve/noise_curve.json")
if ln:
    top = max(ln["curve"], key=lambda c: c["rate"])
    chk("label-noise 20% test AUC-PR", 0.5978, top["auc_pr_mean"], 0.001)

# significance
sg = load("eval_outputs/elliptic_pp/significance/significance.json")
if sg:
    for c in sg["comparisons"].values():
        print(
            f"  significance: {c['label_a']} vs {c['label_b']}  "
            f"delta={c['delta']:+.3f} CI[{c['delta_ci_low']:.3f},{c['delta_ci_high']:.3f}] p={c['p_value']}"
        )

print()
w = max(len(c[0]) for c in checks)
bad = 0
for name, claimed, actual, status in checks:
    if status != "OK":
        bad += 1
    print(f"{name:<{w}}  report={claimed:<12} artifact={actual:<12} {status}")
print(f"\n{len(checks) - bad}/{len(checks)} quoted numbers verified against artifacts")

# --- AMLworld (added 2026-07-25) -------------------------------------------
amlb = load("eval_outputs/amlworld_hi_small/baselines/scoreboard.json")
if amlb:
    b = amlb["baselines"]
    chk("AMLworld B2 AUC-PR", 0.0064, b["b2_xgb"]["auc_pr"], 0.0001)
    chk("AMLworld B3 AUC-PR", 0.0062, b["b3_xgb_graph"]["auc_pr"], 0.0001)
    chk("AMLworld prevalence", 0.0104, b["b2_xgb"]["prevalence_baseline"], 0.0001)

amli = load("eval_outputs/amlworld_hi_small/injection_recovery/injection_recovery_report.json")
if amli:
    chk("AMLworld injection population", 262921, amli["population"], 0)
    chk("AMLworld planted members", 640, amli["n_injected_members"], 0)
    rec = amli["recovery"]
    get = lambda arm, mo: next((x["recall@2000"] for x in rec[arm] if x["motif_type"] == mo), None)
    chk("AMLworld floor common_control@2000", 0.5625, get("floor", "common_control"))
    for mo in ("cycle", "fan_in", "fan_out", "pass_through"):
        best = max(get(a, mo) or 0.0 for a in rec)
        chk(f"AMLworld {mo} best-arm@2000", 0.0, best, 1e-9)

w = max(len(c[0]) for c in checks)
bad2 = sum(1 for c in checks if c[3] != "OK")
print(f"\n--- with AMLworld: {len(checks) - bad2}/{len(checks)} verified ---")
for name, claimed, actual, status in checks:
    if status != "OK":
        print(f"  MISMATCH {name}: report={claimed} artifact={actual}")
