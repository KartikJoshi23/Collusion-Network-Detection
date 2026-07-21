# Datasheet — Elliptic / Elliptic++ (D1, primary financial anchor)

*Per Gebru et al. (2021), abbreviated; §7 step 33. Facts verified in Week-1
EDA (notebooks 01–02) and the committed manifest.*

**Motivation.** Created by Elliptic (Weber et al. 2019) and extended by
Elmougy & Liu (KDD 2023) for Bitcoin AML research; used here as the primary
real-structure financial anchor (RQ1, RQ3).

**Composition.** 203,769 transaction nodes, 234,355 directed edges, 49
discrete time steps; 183-dim anonymized node features (incl. time step).
Labels: 4,545 illicit (~2.2%) / 42,019 licit / rest unknown. The ++ actors
dataset adds wallet-level tables (AddrAddr/AddrTx/TxAddr), used for the
actor-graph view.

**Collection & preprocessing.** Features are anonymized aggregates computed
by the original authors; no re-identification is possible or attempted. Our
adapter (`elliptic_pp_to_ir`) maps CSVs to the graph IR unchanged; unknowns
keep message-passing participation but never contribute loss.

**Uses.** Supervised GNN training/eval under strict-inductive temporal splits
(train ≤34 / test 35–49); unsupervised arms; explanation bundles (structural/
temporal evidence only — no amounts exist); actor-graph triage view.
**Caveat:** a documented distribution shift at time step 43 (dark-market
shutdown) makes validation-based model selection unreliable — measured
repeatedly in this project; per-step metrics are always reported.

**Distribution & license.** No explicit license; released for research, cite
arXiv:2306.06108 (++) / arXiv:1908.02591 (base). Raw data is never
redistributed here — `scripts/download_data.py` fetches from the canonical
sources; checksums in `data/manifests/elliptic_pp.json`.

**Maintenance.** Upstream is static; our manifest pins byte-exact checksums.
