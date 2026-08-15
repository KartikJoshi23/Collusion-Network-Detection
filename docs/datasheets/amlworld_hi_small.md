# Datasheet — IBM AMLworld HI-Small (D2, synthetic scale + ground truth)

*Per Gebru et al. (2021), abbreviated; §7 step 33. Facts verified in Week-1
EDA (notebook 05).*

**Motivation.** Synthetic AML benchmark (Altman et al., NeurIPS 2023) with
complete laundering ground truth — the only dataset here with known pattern
types, so it calibrates the motif injector and anchors the held-out-pattern
transfer study.

**Composition.** 5,078,345 transactions, 515,080 accounts, 5,177 laundering
(0.1019%); true amounts, 7 payment formats, 15+ currencies; dates 2022-09-01
→ 2022-09-18. All eight ground-truth pattern types confirmed present (CYCLE,
GATHER-SCATTER, BIPARTITE, FAN-OUT, SCATTER-GATHER, STACK, RANDOM, FAN-IN).

**Collection.** Fully synthetic (agent-based generator); no real persons or
institutions. **Known trap (measured):** 1,108 transactions dated after
Sep 10 are 59.1% laundering (~580× base rate) — the temporal splitter fences
the post-window tail explicitly.

**Uses.** Injector calibration; PNA/GIN+EU Multi-GNN parity runs; amount-level
evidence narratives. GPU-gated work (NeighborLoader minibatching) is pending —
this dataset is not part of any published headline number yet.

**Distribution & license.** CDLA-Sharing-1.0 (verified via Kaggle metadata).
Requires per-machine Kaggle credentials; never redistributed here; checksums
in `data/manifests/amlworld_hi_small.json`.

**Maintenance.** Kaggle-hosted; the accounts metadata file added upstream
2025-07 is included in the manifest.
