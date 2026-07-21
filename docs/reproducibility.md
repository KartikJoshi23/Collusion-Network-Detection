# Reproducibility Package (§7 step 33, M8)

*The paper's reproducibility statement, in executable form. Every published
number maps to exactly one committed config; a hygiene test enforces that this
map and `configs/experiment/` never drift apart (bidirectionally). Headline
values quoted below are the ledger-recorded measurements (PROGRESS.md is the
running record; multi-seed = mean ± std over 5 seeds unless stated).*

## 1. Environment (frozen)

- Python 3.11 (`.python-version`), dependencies pinned in `uv.lock` — `uv sync`
  recreates the exact venv. Node 20+ with `frontend/package-lock.json` for the
  console.
- **Deliberate exclusion:** pyg-lib / torch-sparse are not installed on the
  Windows dev machines — `NeighborLoader` minibatching work (AMLworld) runs on
  a GPU/Linux machine only. Everything published to date is CPU, full-batch.
- Bootstrap: `uv sync` → `uv run pre-commit install` → `copy .env.example .env`
  → `uv run poe data` → `uv run poe test`.

## 2. Data (never redistributed)

`uv run poe data` downloads every dataset from its canonical source and
verifies byte-exact checksums against the committed manifests
(`data/manifests/*.json`, which also record licenses). AMLworld requires
per-machine Kaggle credentials (README). Per-dataset provenance and caveats:
`docs/datasheets/`.

## 3. The number → config map

Run any row with `uv run collusiongraph <verb> -c <config>` (the `train` verb
auto-dispatches on config shape). Outputs land in the gitignored
`eval_outputs/`; the ledger records the measured values.

### Elliptic++ (financial anchor; prevalence 0.065)

| Config (`configs/experiment/`) | Produces |
|---|---|
| `baselines_elliptic_pp.yaml` | B1 0.0576 / B2 0.8076 / B3 0.8104 AUC-PR (trees byte-reproduce cross-machine) |
| `gnn_elliptic_pp_gatv2_focal.yaml` | headline GATv2-focal single-seed run (seed-0 0.5492 on the master class) |
| `gnn_elliptic_pp_gatv2_focal_multiseed.yaml` | the paper number: **0.4729 ± 0.0525** (5 seeds) |
| `gnn_elliptic_pp_gatv2_wce.yaml` / `gnn_elliptic_pp_gatv2_wce_multiseed.yaml` | −focal ablation: 0.4869 seed-0; **0.4435 ± 0.0615** — second-order |
| `gnn_elliptic_pp_sage_focal.yaml` / `gnn_elliptic_pp_sage_wce.yaml` | SAGE loss pair: 0.4743 vs 0.3882 (focal decisive on SAGE) |
| `gnn_elliptic_pp_gatv2_focal_unidir.yaml` | −bidirectional edges: 0.3549 (the strongest component ablation) |
| `gnn_elliptic_pp_gatv2_focal_multi.yaml` | raw+structural channels: 0.3781 (added channels hurt) |
| `gnn_elliptic_pp_gatv2_focal_line.yaml` | raw+line channel: 0.4986 (B-LG, not adopted) |
| `gnn_elliptic_pp_gatv2_focal_cf.yaml` | context-fusion arm (B-CF, not adopted) |
| `ensemble_elliptic_pp.yaml` | calibrated fusion seed-0 + members (unsup members ≤ prevalence) |
| `ensemble_elliptic_pp_multiseed.yaml` | **calibrated 0.4434 ± 0.0501 vs rank 0.0511 ± 0.0019** |
| `alert_queue_elliptic_pp.yaml` | M2-era SAGE queue (historical first queue) |
| `alert_queue_elliptic_pp_ensemble.yaml` | the published queue: 254 alerts, P@50 0.32 |
| `gnn_elliptic_actor_rgcn.yaml` / `alert_queue_elliptic_actor.yaml` | actor view: AUC-PR 0.2473 with seed-stable queue head P@100 ≥ 0.98 |
| `injection_recovery_elliptic_pp.yaml` | M3 injection-recovery report (floor catches common_control 1.0) |
| `explanations_elliptic_pp.yaml` | 50/50 PGExplainer bundles |
| `explainer_ablation_elliptic_pp.yaml` | the §7-27 three-arm fidelity ablation (PGExplainer adopted) |
| `sensitivity_elliptic_pp.yaml` | NMS/hit-rule grid (queue protocol-robust) |
| `label_noise_elliptic_pp.yaml` | the noise curve: clean 0.4827 ± 0.0616 → 20% 0.5978 ± 0.0248 (val-blindness diagnostic) |

Paired-bootstrap significance rows (calibrated-vs-rank Δ +0.471 CI
[0.440, 0.499]; GATv2-vs-B3 Δ −0.261 CI [−0.285, −0.235]) regenerate via
`collusiongraph.eval.significance.compare_score_files` over the stored score
parquets and are persisted by `scripts/build_demo_artifacts.py`.

### Mendeley EU (procurement anchor; within-sample prevalence 0.358)

| Config | Produces |
|---|---|
| `baselines_mendeley_eu.yaml` | B1 0.3426 / B2 0.3925 / B3 0.3775 / B4 0.3811 |
| `baselines_mendeley_b4_precomputed.yaml` | B4 + dataset screens: 0.3874 (wash-to-negative at the queue head) |
| `baselines_mendeley_screens_ablation.yaml` | **B2+screens 0.4558 (best firm-level number)**; B3+screens 0.3450 |
| `gnn_mendeley_rgcn.yaml` / `gnn_mendeley_rgcn_multiseed.yaml` | the honest negative: 0.2731 seed-0; **0.2808 ± 0.0087, seed-stable below prevalence** |
| `transfer_loco_mendeley.yaml` | single-fold LOCO (country_5: 0.8025…, byte-reproduces cross-machine) |
| `transfer_loco_matrix_mendeley.yaml` | full 7×5 LOCO matrix: macro lift 1.17, largest market fails (0.90) |
| `alert_queue_mendeley_eu.yaml` | the published queue: 223 alerts, P@4 0.50 |
| `explanations_mendeley_eu.yaml` | 20/20 matcher bundles (no learned attribution — R12) |
| `sensitivity_mendeley_eu.yaml` | protocol-sensitivity grid |

### García Rodríguez / cross-domain / OCDS

| Config | Produces |
|---|---|
| `transfer_lomo_matrix_garcia.yaml` | 4×5 LOMO matrix: macro lift 1.57, positive on every market (Italy P@10 1.00) |
| `cross_domain_probe_proc2fin.yaml` | frozen-probe proc→fin: 0.1501 vs 0.065 prevalence (byte-reproduces cross-machine) |
| `cross_domain_probe_fin2proc.yaml` | frozen-probe fin→proc: 0.2843 < 0.358 prevalence (negative) |
| `label_efficiency_proc2fin.yaml` / `label_efficiency_fin2proc.yaml` | label-efficiency curves: transfer never pays at ≤500 target labels, either direction |
| `injection_recovery_ocds_georgia.yaml` | at-scale injection, seed 0 (163,327-node window) |
| `injection_recovery_ocds_georgia_multiseed.yaml` | the paper verdict: coordinated_cluster **0.9275 ± 0.162 @2000**; award-pattern motifs evade |

### Studies & serving

| Config | Produces |
|---|---|
| `practitioner_study.yaml` | §10.3 rater packets + manifest (runbook: `docs/practitioner_study.md`) |

Demo/serving artifacts rebuild with `uv run poe demo-artifacts` (twice — the
second pass wires explanations into `serving.json`); the Copilot goldens gate
is `uv run poe copilot-goldens` (needs `NVIDIA_API_KEY`).

## 4. Seeds & determinism (measured, not assumed)

- Every config carries an explicit `seed:`; multi-seed campaigns run seeds
  0–4 and are resumable (completed seeds are never retrained).
- **Byte-reproducible cross-machine (verified):** XGBoost baselines; the LOCO
  country_5 R-GCN fold; the frozen-encoder probe numbers.
- **Same-machine deterministic only:** torch GNN training. Cross-machine,
  CPU scatter reductions differ — measured GATv2 seed-0 0.5492 (master class)
  vs 0.5318 (laptop-C), a ±0.02 machine-class variance.
- **Seed variance (±0.05) dominates machine variance (±0.02)** — the paper
  quotes multi-seed means with stds, never a best seed. Where a comparison
  crosses machines (the wce campaign), the ledger records the confound.

## 5. Protocol guarantees

Strict-inductive temporal splits, as-of feature computation, LOCO/LOMO entity
isolation, and the alert-unit rules are enforced by the §9.1 leakage suite —
run standalone with `uv run pytest backend/tests -m leakage` and as a
dedicated CI step on every push. One YAML = one experiment: no published
number exists without a committed config, and the repo-hygiene test
`test_repro_map_matches_configs` fails CI if this document and
`configs/experiment/` ever disagree in either direction.
