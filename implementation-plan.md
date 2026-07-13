# CollusionGraph — Implementation Plan

## Detecting Collusion Networks: An Explainable, Imbalance-Robust Graph-Learning Framework for Illicit-Finance and Bid-Rigging Integrity Screening

**Document status:** Implementation plan **v3.0 (development-ready)** — derived from and cross-verified against `Collusion-Network-Detection.md` (the single source of truth), augmented with independent verification research conducted July 2026, re-audited end-to-end. v3.0 integrates the existing **Gen-AI Chatbot** codebase as the **Investigator Copilot** (§4.6, with its cleanup manifest), and pairs with the two-prompt master/collaborator workflow in `handoff-prompt.md`. All changes are logged in Appendix C.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Two-Phase Strategy](#2-two-phase-strategy)
3. [System Architecture](#3-system-architecture)
4. [Technical Stack — Backend & ML](#4-technical-stack--backend--ml)
5. [Technical Stack — Frontend](#5-technical-stack--frontend)
6. [MVP Feature Scope](#6-mvp-feature-scope)
7. [Detailed Build Roadmap](#7-detailed-build-roadmap)
8. [File & Folder Structure](#8-file--folder-structure)
9. [Testing Strategy](#9-testing-strategy)
10. [Path to Publication](#10-path-to-publication)
11. [Risks, Assumptions & Mitigations](#11-risks-assumptions--mitigations)
12. [References](#12-references)
13. [Appendix A — Deviations & Upgrades vs. the Problem Statement](#appendix-a--deviations--upgrades-vs-the-problem-statement)
14. [Appendix B — Traceability Matrix](#appendix-b--traceability-matrix)
15. [Appendix C — v1.0 → v2.0 Audit Changelog](#appendix-c--v10--v20-audit-changelog)

---

## 1. Project Overview

### 1.1 The Problem (restated)

Money laundering in a bank/blockchain ledger and bid rigging in a procurement ledger are the same crime in two costumes: a small group of parties that should act independently instead coordinates, and the evidence lives in the **shape of the network**, never in any single record. Every individual transaction or tender is deliberately kept clean; the illegality — including its terror-financing and sanctions-evasion variants on the financial side — is only visible one level up, in the topology of money flows or of co-bidding.

Current defenses fail identically in both domains:

- **Record-level blindness** — rules and tabular ML score one transaction/tender at a time; collusion is a network property.
- **Threshold gaming** — adversaries structure activity below every static threshold.
- **False-positive overload** — 90–95% of rule-based AML alerts are false (PwC; Lannoo & Parlour 2021), and procurement auditors review tenders by hand on tiny samples.
- **Weak explainability** — a score without a verifiable rationale cannot support an STR filing or survive an audit challenge.
- **Poor generalization** — models trained on one market or typology transfer badly (documented cross-country accuracy drops in the cartel literature; instability across typologies in AML).

The reduction, verbatim from the problem statement:

> **Anomalous-subgraph detection with explanations, on heterogeneous temporal graphs, under a low-false-positive (fixed alert budget) constraint, in a label-scarce environment.**

### 1.2 The Contribution

A single **imbalance-robust, explainable, transfer-capable graph collusion detector**, demonstrated on both illicit-finance networks (Elliptic++, IBM AMLworld) and bid-rigging networks (García Rodríguez multi-country, Mendeley EU cartel, OCDS), with one shared stack (graph construction → detection → explanation → fixed-budget evaluation), plus the **first empirical study of cross-domain transfer of "collusion structure" representations** between the two domains.

### 1.3 Research Questions (verbatim scope, operationalized)

| RQ | Question | Operationalization in this plan |
|---|---|---|
| **RQ1** | Do GNNs + unsupervised graph anomaly detection beat rule-based and tabular baselines on precision at fixed alert budgets? | Precision@100 / Precision@top-5% vs. rules engine, XGBoost/LightGBM tabular, and tabular+graph-features baselines on Elliptic++ and cartel data (§4.5) |
| **RQ2** | Do collusion fingerprints from labeled cases + synthetic injection transfer to unseen markets/typologies at controlled flag rates? | Leave-one-market-out (LOMO) and leave-one-country-out (LOCO) transfer matrices; synthetic motif-injection recovery experiments (§4.4, §10.2) |
| **RQ3** | Do subgraph explanations map to practitioner red-flag vocabularies and get judged verifiable/useful? | PyG Explainer subgraph attributions → motif matcher → red-flag mapping (FATF/OECD vocabularies); practitioner rubric study (§4.4, §10.3) |
| **RQ4** | Does one shared stack serve both domains, and does representation learned in one domain give signal in the other? | Single codebase with two thin adapters; frozen-encoder linear probes + fine-tuning label-efficiency curves across domains (§4.4) |

### 1.4 Success Criteria

**MVP success (Phase 1):**
1. GNN+anomaly ensemble trained on Elliptic++ with imbalance handling flags an illicit subgraph with a complete explanation bundle (motif, evidence, time window, red-flag mapping).
2. Same stack trained on cartel data demonstrates cross-country transfer and flags a cartel subgraph with screen-based explanations (rotation sequence, co-bidding clique where bid data exists, price anomaly, shared-ownership link where available).
3. One cross-domain transfer probe executed and reported honestly, even if the result is partial or negative.
4. A single screening dashboard ranks cases at a fixed alert budget with the explanation attached to each flag.
5. Precision@budget of the graph ensemble materially exceeds rule-based and tabular baselines on at least the financial arm (the primary labeled anchor).

**Publication success (Phase 2):**
- Full ablation suite, multi-seed results with confidence intervals, complete transfer matrices, explanation-quality study, leakage-safe evaluation protocol, reproducibility package (incl. model card + dataset datasheets), and a submitted manuscript to ACM ICAIF or a KDD graph-anomaly workshop (procurement-led alternates: EPJ Data Science, ACM DGov; scale alternate: IEEE Big Data).

### 1.5 Non-Goals (scope boundaries, verbatim from source)

Out of scope: any determination of legal guilt; processing of personal or classified UAE data; real-time production deployment inside a bank or ministry (target maturity TRL 3–4); investigation case management beyond alert export. The system is a **risk-screening and triage instrument that ranks cases for human investigation — not an accusation engine**. This constraint governs the ethics language of every output, every UI label, and every line of the paper.

---

## 2. Two-Phase Strategy

### Phase 1 — Working Prototype / MVP (target: ~8 working weeks + built-in slack, §7)

The minimum system that demonstrably solves the core problem end to end:

- **P1.1 Data spine.** Two adapters (financial, procurement) producing one unified heterogeneous temporal graph schema; Elliptic++ and Mendeley EU cartel as the labeled anchors; IBM AMLworld HI-Small for synthetic-pattern validation; García Rodríguez data integrated if the supplement is retrievable (fallback path defined in §11). Procurement graphs are **award-network-first** (constructible from award data alone), with co-bid edges as enrichment where losing-bidder data exists (§4.3 D4).
- **P1.2 Detection core.** Supervised GNN family (GraphSAGE, GATv2, R-GCN) + unsupervised anomaly arm (graph autoencoder / DOMINANT via PyGOD) + calibrated rank-fusion ensemble producing deduplicated subgraph/community-level alerts (§4.5).
- **P1.3 Imbalance handling.** Focal loss, class weighting, stratified neighbor sampling; synthetic motif injection covering **all five rows of the problem statement's motif table** with known ground truth.
- **P1.4 Explanation bundle.** PyG `Explainer` (GNNExplainer algorithm) + GATv2 attention + rule-based motif matcher → red-flag vocabulary mapping. Every surfaced alert ships with its explanation; an unexplained flag is a non-deliverable.
- **P1.5 Evaluation harness.** Precision@k, AUC-PR, FPR at operational budgets under a precisely defined alert unit (hit rule + overlap deduplication, §4.5); one LOCO transfer split; one cross-domain probe — all leakage-safe (strict-inductive temporal splits).
- **P1.6 Screening dashboard.** React + WebGL dashboard: ranked alert queue at a fixed budget, interactive subgraph explorer, explanation panel, metrics view, AML↔procurement domain toggle, per-domain dataset selector.

**Phase 1 exit criterion:** a stranger can clone the repo, run one documented command (`poe demo` / `docker compose up`), open the dashboard, and walk from a ranked alert to its highlighted subgraph and red-flag explanation in both domains.

### Phase 2 — MVP → Publication-Ready (target: ~8–9 additional weeks)

- **P2.1 Model depth.** Line-graph views for directed money flow (LineMVGNN-inspired); PNA/GIN+EU reference baselines from IBM Multi-GNN; PGExplainer for amortized explanation at queue scale; heterogeneous experiments using Elliptic++ actor (wallet) graphs; *(stretch)* a temporal-GNN variant (TGN/TGAT) to test whether continuous-time modelling beats snapshot + temporal-encoding.
- **P2.2 Investigator Copilot.** Port the existing Gen-AI Chatbot codebase into the console as the conversational investigator layer (§4.6): a LangGraph multi-agent pipeline (SQL agent over the DuckDB artifact store, RAG agent over the red-flag/methodology corpus, critic with grounding + numeric-sanity gates) surfaced as a Copilot dock in the frontend. This **subsumes the earlier "LLM narrative layer"** — the Copilot's grounded answers include alert narratives — and directly implements the EU AI Act human-oversight story.
- **P2.3 Transfer science.** Full LOMO/LOCO transfer matrices across all procurement markets; cross-domain study with frozen probes, fine-tuning curves, and (stretch) adversarial/statistical domain adaptation (DANN/CORAL).
- **P2.4 Rigor.** Multi-seed runs (≥5 seeds), bootstrapped confidence intervals, significance testing, ablations over every component (imbalance strategy, ensemble members, explainer, feature families, temporal encoding, dedup threshold), sensitivity to budget k and to the community hit rule.
- **P2.5 Explanation study.** Structured practitioner rubric (verifiability, red-flag alignment, usefulness) with domain-knowledgeable raters; explanation fidelity metrics (fidelity+/fidelity−, characterization score) as objective complements; if the Copilot ships, a bundle-only vs. bundle+Copilot comparison arm.
- **P2.6 Scale & robustness.** IBM AMLworld Medium; OCDS bulk ingestion (publisher chosen for bid-level data quality) with synthetic injection for the unsupervised regime; robustness to label noise.
- **P2.7 Paper & artifacts.** Writing, figures from the dashboard, model card + dataset datasheets, reproducibility package, venue-formatted submission.

---

## 3. System Architecture

### 3.1 High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            DATA LAYER                                    │
│                                                                          │
│  Raw sources (downloaded once, checksummed + license-recorded,           │
│  never edited):                                                          │
│   • Elliptic++ (GitHub git-disl)      • Mendeley EU cartel (f3y4nrn3s6)  │
│   • Elliptic base (PyG built-in)      • García Rodríguez supplement      │
│   • IBM AMLworld (Kaggle)             • OCDS bulk (data registry)        │
│                    │                              │                      │
│         ┌──────────▼──────────┐        ┌──────────▼──────────┐           │
│         │  FINANCIAL ADAPTER  │        │ PROCUREMENT ADAPTER │           │
│         │ accounts/tx nodes,  │        │ firms/tenders/bids/ │           │
│         │ directed timestamped│        │ lots + buyers;      │           │
│         │ attributed edges,   │        │ award edges (core), │           │
│         │ entity-link edges   │        │ co-bid + ownership  │           │
│         │                     │        │ edges (enrichment)  │           │
│         └──────────┬──────────┘        └──────────┬──────────┘           │
│                    └───────────┬─────────────────┘                       │
│                                ▼                                         │
│              UNIFIED GRAPH SCHEMA (CollusionGraph IR)                    │
│         Parquet node/edge tables + DuckDB catalog + PyG HeteroData        │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          ML BACKEND (offline)                            │
│                                                                          │
│  Feature engineering ─► Synthetic motif injector ─► Splitters            │
│  (structural, temporal,   (all 5 motif-table rows,   (strict-inductive   │
│   statistical screens)     both domain variants)      temporal / LOCO /  │
│                                 │                     LOMO)              │
│         ┌───────────────────────┼───────────────────────┐                │
│         ▼                       ▼                       ▼                │
│  SUPERVISED GNNs         UNSUPERVISED ARM         BASELINES              │
│  GraphSAGE / GATv2 /     GAE + DOMINANT           rules engine,          │
│  R-GCN (+ line-graph,    (PyGOD, on homogeneous   XGBoost tabular,       │
│  PNA/GIN, TGN in Ph. 2)  projections), structural tabular+graph-feats,   │
│                          z-score floor            screens-only           │
│         └───────────────────────┬───────────────────────┘                │
│                                 ▼                                        │
│              CALIBRATED SCORE FUSION & COMMUNITY ROLL-UP                 │
│     (isotonic-calibrated rank fusion ─► subgraph alerts ─► overlap        │
│      deduplication (NMS) ─► ranked alert queue)                           │
│                                 ▼                                        │
│                       EXPLANATION LAYER                                  │
│    PyG Explainer (GNNExplainer/PGExplainer) + GATv2 attention            │
│    ─► minimal responsible subgraph ─► motif matcher ─► red-flag map      │
│                                 ▼                                        │
│               SCORED ARTIFACT STORE  (Parquet + DuckDB + JSON)           │
│      alerts.parquet · explanations/ · metrics.json · model registry      │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        API LAYER — FastAPI                               │
│   REST: /domains /datasets /alerts?budget=k /alerts/{id} /subgraph/{id}  │
│         /explanations/{id} /metrics /transfer-matrix /motifs             │
│   Serves precomputed artifacts (no GPU in the request path for MVP)      │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    FRONTEND — React + WebGL console                      │
│   Alert Queue (budget slider) · Graph Explorer (Sigma.js WebGL)          │
│   Case Detail w/ Explanation Bundle · Metrics Lab · Domain Toggle        │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Component Separation & Contracts

| Component | Responsibility | Contract with neighbors |
|---|---|---|
| **Data adapters** | Parse raw datasets into the unified schema; the *only* domain-specific code besides red-flag vocabularies | Emit `nodes.parquet`, `edges.parquet`, `labels.parquet` conforming to the CollusionGraph IR (§4.2) |
| **Graph store** | Versioned Parquet tables + DuckDB catalog; builders that materialize PyG `Data`/`HeteroData` objects | Deterministic graph builds keyed by config hash |
| **Training pipeline** | Config-driven experiments (YAML/Hydra); training, checkpointing, scoring | Writes to model registry + scored-artifact store; logs to W&B (offline mode supported) |
| **Explanation service** | Batch explanation of top-k alerts post-scoring | Writes one JSON explanation bundle per alert (schema in §4.4) |
| **Evaluation harness** | All metrics, all splits, all transfer matrices; the single source of truth for numbers in the paper | Writes `metrics.json` + plot-ready CSVs |
| **API layer** | Read-only serving of precomputed artifacts; pagination, subgraph windowing | OpenAPI-documented REST; JSON responses sized for the frontend |
| **Frontend** | Investigator-facing screening console | Consumes REST only; zero direct data access |
| **Copilot service (Phase 2)** | Conversational investigator layer: LangGraph agent pipeline answering questions over the alert store (SQL), the red-flag/methodology corpus (RAG), and explanation bundles (§4.6) | Mounted in the same FastAPI app at `/api/v1/copilot` (SSE streaming); **read-only** access to the artifact store and corpus; never writes |

**The alert is the system's central artifact.** Its schema (`alerts.parquet`):

```
alert_id · domain · dataset · model_run_id · rank · risk_score (calibrated) ·
community_id · member_node_ids · anchor_subgraph (node/edge id lists) ·
time_window (start, end) · motif_type · n_members · overlap_group ·
explanation_ref · created_at · caveats (fixed screening-only string)
```

**Key architectural decision:** inference is **batch/offline**; the API serves precomputed artifacts. This keeps the demo robust (no GPU needed to run the dashboard), keeps evaluation reproducible, and matches the real operational cadence of AML/audit screening (daily/weekly batch, not per-request). A `collusiongraph score --rescore` CLI regenerates artifacts when models change.

---

## 4. Technical Stack — Backend & ML

### 4.1 Core Stack

| Layer | Choice | Rationale |
|---|---|---|
| Language | Python 3.11+ | PyG/PyGOD ecosystem compatibility |
| DL framework | PyTorch 2.x | Standard |
| Graph learning | **PyTorch Geometric ≥ 2.6** — *without* the optional compiled extensions (torch-scatter/sparse), which modern PyG no longer requires | Full model zoo + `NeighborLoader` + `HeteroData` + `torch_geometric.explain`; avoiding compiled extensions keeps the **Windows dev environment** friction-free |
| Unsupervised GAD | **PyGOD** | 10+ graph outlier detectors (DOMINANT, GAE-based, GUIDE…) on top of PyG with a PyOD-style API. Note: PyGOD detectors target homogeneous attributed graphs — the unsupervised arm runs on per-edge-type homogeneous projections of the IR (§4.4) |
| Tabular baselines | scikit-learn, XGBoost, LightGBM | RQ1 requires strong non-graph baselines |
| Classical graph ops | NetworkX (+ graphology-compatible exports) | Cycle/star/clique motif detection for features and the explanation motif matcher; Leiden via `igraph`/`graspologic` |
| Data engineering | pandas + Polars, PyArrow/Parquet, DuckDB | Fast columnar ETL; DuckDB gives SQL over Parquet for the API layer with zero server |
| Config & experiments | Hydra (or plain YAML + thin loader), Weights & Biases with offline fallback | Every experiment reproducible from one config file |
| Serving | FastAPI + Uvicorn + Pydantic v2 | OpenAPI docs for free; Pydantic schemas shared with explanation bundles |
| Task runner | **poethepoet** (`poe data`, `poe train`, `poe demo`) declared in `pyproject.toml` | **Cross-platform — works identically in PowerShell and bash** (primary dev machine is Windows 11); a thin optional Makefile may alias the same tasks for *nix CI |
| Environment | `uv` + pinned lockfile; optional Dockerfile/compose for the demo build | Reproducibility |
| Hardware | Single consumer GPU, or Colab/Kaggle GPU; CPU fallback works at Elliptic++ scale | Problem statement: no exotic hardware — confirmed feasible. Rough budget: Elliptic++ GNN ≈ minutes/epoch on GPU (tens of minutes CPU); AMLworld HI-Small (~5M tx) needs `NeighborLoader` minibatching and a GPU session; Medium (~30M) is a Phase-2, cloud-GPU job; Large (~180M) is declared out of scope |

### 4.2 Unified Graph Schema (CollusionGraph IR)

Both adapters emit the same intermediate representation, so everything downstream is domain-agnostic:

```
nodes.parquet:   node_id · node_type · domain · time_first_seen · feature vector (fixed template) · raw_attrs (JSON)
edges.parquet:   src · dst · edge_type · timestamp · amount/price · directed flag · raw_attrs (JSON)
labels.parquet:  node_id (or subgraph_id) · label ∈ {illicit, licit, unknown} · label_source · confidence
communities.parquet: community_id · member node_ids · detection method
alerts.parquet:  (schema in §3.2)
```

**Node/edge types by adapter:**

| | Financial adapter | Procurement adapter |
|---|---|---|
| Node types | `account`/`address`, `transaction` (Elliptic++ is a tx–tx graph; the actor dataset adds wallets) | `firm`, `tender`, `bid`, `lot`, `buyer` |
| Edge types | `pays` (directed, timestamped, amount), `owned_by`/`linked_to` (entity linkage where available) | **Core (award-derived, always available):** `awarded` (tender→firm), `buys_from` (buyer→tender). **Enrichment (where data exists):** `bids_on` (firm→tender, price, timestamp), `co_bid` (firm–firm projection), `linked_to` (shared owners/directors/addresses) |
| Labels | tx-level illicit/licit/unknown (Elliptic++: 4,545 illicit ≈ 2%, 42,019 licit ≈ 21%, rest unknown); AMLworld: full ground truth incl. pattern type | contract/firm-level cartel participation (Mendeley: verified cartel cases across 7 countries; García Rodríguez: collusive vs. competitive auctions per market) |

Two schema rules added by the audit:

1. **Award-network-first (procurement).** Losing-bidder identities and prices are *not* systematically recorded across the Mendeley countries (the IJIO companion paper flags this explicitly). Therefore every procurement pipeline component must function on the award-derived core graph alone — winner-rotation, market-share, and buyer-concentration signals need only awards — while co-bid cliques and bid-price screens activate as enrichment for country-years where bid data exists. Which countries have which coverage is a Week-1 EDA deliverable.
2. **Shared structural feature template** (degree in/out, motif participation counts, temporal burstiness, clustering coefficient, k-core index, community-relative statistics), **z-scored within each graph** so cross-graph and cross-domain comparisons are not dominated by trivial scale differences. This template is what makes the RQ4 cross-domain probe technically possible despite disjoint raw feature spaces — domain-specific raw features feed domain-specific heads, while the transfer study operates on the shared structural channel.

### 4.3 Datasets — Loading, Preprocessing, Splits

Every dataset named in the problem statement is mapped below. All are public and near-zero-cost; none involves classified or personal UAE data. **Week-1 tasks for every dataset: checksum, record the license in `data/manifests/`, and verify prevalence/coverage numbers via EDA.**

#### D1. Elliptic / Elliptic++ (primary financial anchor)

- **Contents (verified against the repo and paper):** 203,769 transaction nodes, 234,355 directed edges, 49 time steps. Each transaction carries **183 features: the 166 base-Elliptic features (93–94 local + 72 one-hop aggregates — the local block includes interpretable fields such as time step, number of inputs/outputs, transaction fee, and output volume) plus 17 augmented features added by Elliptic++ for deanonymized transactions.** Labels: 4,545 illicit (~2%), 42,019 licit (~21%), remainder unknown. The Elliptic++ extension (github.com/git-disl/EllipticPlusPlus, arXiv:2306.06108) adds ~822k wallet addresses with 56 named features and 1.27M+ temporal interactions, enabling four graph views (tx–tx, addr–addr, addr–tx, user entity).
- **Loading:** base Elliptic via PyG `EllipticBitcoinDataset`; Elliptic++ CSVs from GitHub → financial adapter → IR.
- **Unknown-label policy:** loss is computed on labeled nodes only; **unknown nodes participate fully in message passing** (they carry the network structure that defines the crime); the unsupervised arm scores them, and they may appear inside alert subgraphs as context. This policy is stated in the paper's protocol section.
- **Split (upgraded protocol):** temporal split, train on time steps 1–34, test on 35–49 (the community convention) — enforced **strict-inductively**: training-time message passing confined to the subgraph induced by train-period nodes. Recent work (arXiv:2604.19514) shows a paired controlled gap of ~39.5 F1 points attributable to training-time exposure to test-period adjacency; we adopt the strict protocol so our numbers are leakage-safe, report **per-time-step metrics**, and discuss the known distribution shift at time step 43 (dark-market shutdown) explicitly.
- **Explanation evidence caveat:** most of the 166 base features are anonymized; explanation bundles on Elliptic therefore lead with **structural + temporal evidence** (motif, time steps, degrees) plus whichever interpretable fields exist (fees, output volume, counts). Full amount-level evidence narratives are demonstrated on AMLworld (true amounts) and procurement data (real prices). This is stated honestly in the UI and the paper.
- **Role:** MVP item 1; RQ1 primary; RQ3 financial explanations; one side of RQ4.

#### D2. IBM AMLworld (scale + synthetic ground truth)

- **Contents (verified):** six synthetic datasets (HI/LI × small/medium/large; ~5M / ~30M / ~180M transactions) with complete ground truth for **eight laundering patterns** (fan-in, fan-out, cycle, scatter-gather, gather-scatter, simple bipartite, stack, random); Altman et al., NeurIPS 2023 Datasets & Benchmarks (arXiv:2306.16424); Kaggle `ealtman2019/ibm-transactions-for-anti-money-laundering-aml`.
- **Loading:** Kaggle download (API key required — documented in `scripts/download_data.py`) → financial adapter (accounts as nodes, transactions as edges — an account-graph, which the adapter normalizes into the IR).
- **Usage:** **HI-Small** in MVP for (a) validating that the detector recovers known injected patterns (calibrates the synthetic-injection methodology), (b) controllable-imbalance experiments, (c) amount-level explanation demos; **Medium** in Phase 2 for scale claims; Large explicitly out of scope.
- **Reference baselines:** IBM's official **Multi-GNN** repo (github.com/IBM/Multi-GNN — GIN, GAT, PNA, R-GCN with edge updates) is the published baseline suite for this data; we reproduce its PNA configuration in Phase 2 as an external reference point. Its finding that **bi-directional multi-edge aggregation materially helps directed money-flow graphs** (arXiv:2412.00241) directly informs our directionality handling (§4.4).
- **Role:** RQ2 synthetic-injection arm; imbalance-controlled ablations; scale story.

#### D3. García Rodríguez et al. 2022 multi-country collusion dataset (procurement cross-market spine)

- **Contents:** collusive/competitive auction data from Brazil, Italy (Turin road construction 2000–2003), Japan (Okinawa building/civil engineering 2003–2007), Switzerland (two regions), and the United States; supplement to *Automation in Construction* 133:104047 (ScienceDirect S0926580521004982, supplement item ec0010). The same data family used by Gomes et al. (arXiv:2410.07091) and Imhof/Viklund/Huber (arXiv:2507.12369), making our cross-market numbers directly comparable to both papers. Unlike Mendeley, these market datasets **do include losing bids** (they were built for screen research), so full co-bid graphs and price screens apply here.
- **Loading:** download supplement (**Week-1 task — de-risk immediately**); procurement adapter builds per-market tender–firm bipartite graphs with bid-price edge attributes.
- **Split:** LOMO (leave-one-market-out) and LOCO (leave-one-country-out) — mirroring Imhof et al.'s 13-market/7-country transfer design (their best config: ~91% cross-market on 8 markets; ~84% average across 12).
- **Risk & fallback:** if the supplement proves unavailable → §11 R2.

#### D4. Mendeley EU cartel dataset (primary labeled procurement anchor)

- **Contents (verified):** contract-level procurement data with verified cartel cases (problem statement: 73 confirmed cartels, 15,000+ cartel-member contracts — **counts to be confirmed in Week-1 EDA**) across Bulgaria, France, Hungary, Latvia, Portugal, Spain, Sweden, 2004–2021, harmonized from opentender.eu by Fazekas, Wachs, Tóth & Abdou; Mendeley Data DOI 10.17632/f3y4nrn3s6.2 (v2, August 2025); companion paper in *IJIO* (S0167718725000943). Fields include tender/lot IDs, anonymized buyer/bidder IDs, 2-digit CPV codes, and **precomputed cartel-screen variables** used in the paper.
- **Critical caveat (verified):** the companion paper itself notes that losing-bidder prices are **not collected systematically across these countries**. Consequences built into this plan: (a) the award-network-first schema rule (§4.2); (b) screen features are taken from the dataset's own precomputed screen variables where raw bids are absent; (c) co-bid enrichment activates only for country-years with bidder coverage (mapped in Week-1 EDA); (d) overall cartel prevalence is measured, not assumed.
- **Split:** LOCO across the 7 countries; within-country temporal splits for the single-market setting.
- **Role:** MVP item 2; RQ1 procurement arm; RQ2 cross-country transfer; RQ3 procurement explanations; other side of RQ4.

#### D5. OCDS bulk data (unlabeled scale + deployment path)

- **Contents (verified):** Open Contracting Data Standard releases from 50+ governments via data.open-contracting.org (includes opentender.eu-sourced EU publications).
- **Publisher selection criterion (added by audit):** choose one or two publishers that populate the OCDS `bids` extension (losing-bidder data), since co-bid structure is where injected cartel motifs live; publishers with award-only data remain usable for the award-network signals. Full registry ingestion is out of scope.
- **Usage:** Phase 2 — unlabeled graphs for (a) synthetic cartel-motif injection with known ground truth (RQ2), (b) unsupervised-arm stress testing, (c) the documented path to a future UAE-portfolio deployment via OCDS-standard feeds (the product story).

### 4.4 Model & Method Design

#### Supervised GNN family

| Model | Why | Notes |
|---|---|---|
| **GraphSAGE** | Inductive workhorse; neighbor sampling scales to Elliptic++/AMLworld | MVP; `NeighborLoader` minibatching |
| **GATv2** | Attention weights double as an interpretability signal | **Upgrade over the problem statement's GAT:** GATv2 (Brody et al., ICLR 2022) fixes GAT's static-attention limitation at identical cost; plain GAT kept as an ablation |
| **R-GCN** | Relational/heterogeneous edges (pays vs. linked_to; awarded vs. bids_on vs. co_bid) | MVP for procurement (inherently heterogeneous); mirrors Gomes et al. |
| **Line-graph view** | Directed money-flow modelling à la LineMVGNN (edge→node duality captures flow-through patterns) | Phase 2; auxiliary view whose embeddings concatenate into the main model |
| **PNA / GIN+EU** | IBM Multi-GNN's strongest published configurations on AMLworld | Phase 2 reference baselines for external comparability |
| **TGN/TGAT** *(stretch)* | Continuous-time temporal message passing | Phase 2 optional: tests whether true temporal GNNs beat snapshot + temporal encodings; cut first under schedule pressure |

**Directionality handling (added by audit):** money flow and awards are directed, and direction is signal (fan-in vs. fan-out are different crimes). All message-passing models receive **both edge directions with a direction flag** (forward/reverse relation types in R-GCN; direction-encoded edge features in SAGE/GATv2), following the bi-directional multi-edge aggregation evidence from the Multi-GNN line of work (arXiv:2412.00241). Motif features and the motif matcher operate on the original directed graph.

All supervised models output node-level logits; **subgraph/community scores** are produced by a roll-up layer: community detection (Leiden, on the undirected weighted projection appropriate to each domain — money-flow graph / co-bid-or-award projection) → community score = budget-aware aggregation (max + top-p mean) of calibrated member scores + community-level anomaly features. The system ranks *communities and subgraphs*, not just nodes — a core requirement of the problem statement.

#### Unsupervised anomaly arm

- **Graph autoencoder** (structure + attribute reconstruction error) and **DOMINANT** via PyGOD as primary detectors, run on **homogeneous projections** per edge type (PyGOD's supported regime); a purely structural scorer (motif-count z-scores against degree-preserving null models) as a transparent floor.
- **Evaluation policy (added by audit):** the unsupervised arm is validated on (a) the labeled subsets it never trained on, and (b) synthetic-injection recovery — reported separately from the supervised results so its standalone value is measurable (it is also ablation B5).

#### Ensemble

- **Rank fusion** over supervised GNN score, unsupervised anomaly score, and statistical-screen score — with **isotonic calibration** of each member on validation folds before fusion, so fused scores are comparable and the UI's risk scores are probabilistically meaningful. Members remain individually reportable for ablations.

#### Class-imbalance handling (RQ1's hard constraint)

1. **Focal loss** (γ tuned on validation AUC-PR) vs. class-weighted cross-entropy — ablated head-to-head.
2. **Stratified neighbor sampling** — minority-enriched minibatches via weighted samplers (leakage-safe: sampling within the train subgraph only).
3. **Graph-aware oversampling** — GraphSMOTE-style synthetic minority nodes considered but deprioritized (synthetic nodes distort topology); the preferred augmentation is synthetic motif injection, which creates *whole labeled subgraphs* matching the actual detection target.
4. **Synthetic motif injection — full coverage of the problem statement's motif table (audit fix):**

   | Motif-table row | Financial generator | Procurement generator |
   |---|---|---|
   | Circular coordination | laundering cycle (funds return via k intermediaries, ≤T window) | bid-rotation sequence (win passed around n firms) |
   | Convergent funneling | smurfing fan-in (m sub-threshold deposits → one target) | cover-bid cluster (losing bids tightly above pre-agreed winner) |
   | Divergent dispersal | layering fan-out / scatter-gather (calibrated vs. AMLworld patterns) | market-allocation partition (firms split regions/CPV categories) |
   | Hidden common control | shell-chain: accounts joined by injected `linked_to` clique (shared agent/owner) | "rival" firms joined by injected `linked_to` clique (shared директор/address analog) |
   | Coordinated clustering | pass-through chain (near-zero retention, abnormally short holding times) | near-clique of co-bidders with clustered prices + sequential timestamps |

   Injection parameters (size, amounts, temporal spread) randomized within realistic ranges; the financial generators are **calibrated against AMLworld's eight ground-truth patterns** (a generator is accepted when the detector's recovery behavior on injected vs. native AMLworld patterns matches); procurement generators follow the OECD red-flag catalogue. Injected ground truth enables controlled recall/precision measurement — directly targeting the instability-under-imbalance failure documented by Lawal et al. (2025).
5. **Threshold-free reporting** — AUC-PR + Precision@k everywhere; global accuracy never headlines (meaningless at 2% prevalence; note AUC-PR's random baseline equals prevalence, which is how we contextualize all AUC-PR numbers).

#### Explainability layer (RQ3)

**Upgrade over the problem statement:** we use PyTorch Geometric's first-class **`torch_geometric.explain` framework** — the `Explainer` API with `GNNExplainer` (MVP) and `PGExplainer` (Phase 2, amortized: trains once, then explains the whole queue cheaply — GNNExplainer's per-alert optimization at ~seconds-to-minutes × top-k is affordable for k ≤ 200, which bounds the MVP budget). `HeteroExplanation` covers R-GCN; built-in **fidelity metrics** (fidelity+/−) provide objective explanation evaluation.

**Scope honesty (added by audit):** the explainer attributes the **supervised member's** prediction; the motif matcher and screens explain the structural/statistical members. The bundle labels which evidence comes from which source — no false implication that one method explains the fused score.

Every alert's **explanation bundle** (JSON, schema-validated):

```
{
  alert_id, domain, dataset, rank, risk_score, budget_position,
  minimal_subgraph: {nodes[], edges[]},            ← Explainer masks, thresholded
  attention_summary,                               ← GATv2 attention corroboration
  motif: {type: cycle|fan_in|fan_out|common_control|pass_through|rotation|cover_bid|partition|clique,
          params},
  evidence: {amounts?, fees?, time_window, degrees}            ← financial
          | {rotation_sequence, price_stats?, co_bid_history?, shared_links?},  ← procurement
          (fields optional per dataset coverage — see D1/D4 caveats)
  evidence_sources: {learned: [...], structural: [...], screen: [...]},
  red_flags: [{framework: FATF|OECD, indicator_id, indicator_text, matched_because}],
  fidelity: {fidelity_plus, fidelity_minus},
  caveats: "screening signal only — no determination of guilt"
}
```

The **motif matcher** is deliberately rule-based (NetworkX cycle/star/clique detection over the explainer-selected subgraph + statistical screens over its attributes): the learned model finds the region, the transparent rules name the pattern. The **red-flag mapping** tables are curated from FATF indicator lists (financial) and the OECD 2025 bid-rigging checklist (procurement) — the two vocabularies are the only other domain-specific artifacts besides the adapters, exactly as the problem statement's "70% shared stack" framing predicts.

#### LLM narrative layer — superseded by the Investigator Copilot (§4.6)

v2.1 planned a one-shot LLM step verbalizing each explanation bundle. v3.0 replaces it with something strictly stronger that already exists as working code: the ported Gen-AI Chatbot (§4.6), whose critic enforces the very guardrails this layer required (numbers validated against evidence, grounding mandatory, deterministic failure modes). The guardrail principles carry over unchanged: the LLM sees only structured evidence, every claim is checked against it, outputs are labeled AI-generated, and a bundle-only vs. bundle+Copilot practitioner-study arm measures the added value (arXiv:2506.14933; arXiv:2507.14785).

#### Feature engineering

- **Financial:** holding time, retention ratio, in/out-degree burstiness, amount round-number bias, velocity features, temporal encodings (time-step embeddings; sinusoidal time features on edges).
- **Procurement (screens as features, fusing the screen tradition with the network model):** coefficient of variation of bids, price spread, kurtosis, bid-difference and relative-distance statistics *(bid-dependent — enrichment tier)*; winner-rotation entropy, co-award frequency, market-share stability, buyer–supplier concentration *(award-derived — always available)*. Where the Mendeley data ships precomputed screens, those are used directly. Screens-only is reportable baseline B4.
- **Shared structural template:** degrees, motif counts, clustering, k-core, community-relative stats, temporal burstiness — z-scored per graph (§4.2) — the cross-domain transfer channel.

#### Transfer & domain adaptation (RQ2, RQ4)

- **Cross-market (procurement):** LOMO/LOCO with held-out-market Precision@k — the protocol of Imhof et al. and Gomes et al., giving published comparison numbers.
- **Cross-typology (finance):** train on a subset of AMLworld pattern types, test on held-out pattern types; Elliptic++→AMLworld probe.
- **Cross-domain (the novel study):** encoders trained on the shared structural channel in domain A; evaluated on domain B via (a) frozen-encoder + linear probe, (b) fine-tuning with label-efficiency curves (5%, 10%, 25%, 100% of target labels — does source pretraining beat from-scratch?). Phase 2 stretch: DANN/CORAL alignment on the structural channel. **Honest reporting is a design requirement:** a partial or negative result on a never-studied question is a publishable finding.

### 4.5 Evaluation Protocol (the paper's spine)

#### Alert unit, hit rule, and deduplication (added by audit — without these, subgraph-level Precision@k is ill-defined)

- **Alert unit:** a community/subgraph alert (§3.2 schema), not a bare node. Node-level rankings are additionally reported for comparability with prior work (relevant context: arXiv:2604.23494 shows transaction-level and actor-level queues materially disagree on Elliptic++ — we report both levels).
- **Hit rule (primary):** an alert counts as a true positive iff it contains ≥1 confirmed illicit node (financial) / ≥1 confirmed cartel contract or firm (procurement). **Sensitivity analysis** at stricter thresholds (≥10%, ≥25% of members confirmed) reported in Phase 2, since the lenient rule can flatter models that flag huge communities.
- **Deduplication:** overlapping alerts are suppressed by greedy non-maximum suppression — rank-descending, suppress any alert with Jaccard overlap > 0.5 (member sets) against an accepted alert; the threshold is itself ablated. Alert size is capped (n_members ≤ 100) so a single mega-community cannot absorb the budget.

#### Metrics

| Metric | Definition | Budgets |
|---|---|---|
| **Precision@k** | Precision within top-k deduplicated alerts | k = 50, 100, 200 (financial, per the statement's "top 100"); top 1%, 5%, 10% of tender queue (procurement, per "top 5%") |
| **AUC-PR** | Area under precision–recall curve (Saito & Rehmsmeier 2015); contextualized against the prevalence baseline | — |
| **FPR@budget / Recall@budget** | False-positive rate and captured illicit mass at each operational budget | Same budgets |
| **Transfer Precision@k** | Precision@k on held-out market / held-out domain | LOMO/LOCO matrices |
| **Explanation fidelity** | fidelity+/fidelity−, characterization score (PyG metrics) | Top-k alerts |
| **Explanation quality (human)** | Practitioner rubric: verifiability, red-flag alignment, actionability | Sampled alerts, both domains |

Protocol rules: strict-inductive temporal splits (no test-period adjacency at training time); as-of-timestamp feature computation; no random splits anywhere on temporal data; multi-seed (≥5) with bootstrapped 95% CIs in Phase 2 (paired bootstrap for model comparisons at fixed k); every number in the paper regenerable by the `eval/` harness from configs.

**Baselines for RQ1** (all evaluated identically, same tuning budget as our models): (B1) rules engine encoding classic thresholds/red-flag heuristics; (B2) XGBoost/LightGBM on tabular features; (B3) **XGB-Graph** — XGBoost over tabular + neighborhood-aggregated graph features, implemented per the **GADBench** protocol (Tang et al., NeurIPS 2023, arXiv:2306.12251): GADBench's central finding is that tree ensembles with simple neighborhood aggregation often *beat* specialized GNNs (average +12.9 AUPRC in the fully-supervised setting), so this is the yardstick the GNN stack must beat — and if it doesn't on some dataset, that is reported honestly, which reviewers who know GADBench will expect; (B4) statistical screens alone (procurement); (B5) unsupervised arm alone; (B6) published reference points (Multi-GNN PNA on AMLworld; Imhof/Gomes numbers on the shared procurement data).

### 4.6 Investigator Copilot — integrating the Gen-AI Chatbot

An existing, working multi-agent chatbot codebase (`Gen-AI Chatbot/`, currently configured for a fictional company's HR/finance data) is folded into CollusionGraph as the **Investigator Copilot**: the conversational layer of the screening console. The integration is natural, not forced, because the two systems already share their load-bearing joints:

| Chatbot capability (as built) | CollusionGraph counterpart it lands on |
|---|---|
| SQL agent: bounded tool-calling loop over **DuckDB** (list/describe/sample/run) | The artifact store is **already DuckDB + Parquet** (§3.2, §4.1) — the SQL agent points at `alerts`, `communities`, `metrics` views with zero engine change |
| RAG agent: hybrid BM25 + dense retrieval with RRF + reranker over a PDF corpus, with per-chunk citations | The red-flag knowledge base the plan already curates: FATF indicator lists, OECD 2025 bid-rigging checklist, methodology docs, dataset datasheets, model card (`data/corpus/`) |
| Critic with deterministic **grounding gate** (policy terms ⇒ must cite corpus) and **numeric-sanity gate** (every claimed number must appear in SQL evidence) | Exactly the guardrails §4.4's narrative layer mandated — the chatbot already implements them in code |
| Clarification loop + read-back confirmation (human-in-the-loop interrupts) | The EU AI Act human-oversight story (§10.6): the investigator interrogates, confirms, and overrides |
| Evidence panel, trace timeline, confidence badge (React 19 + Tailwind v4 + Vite) | Same frontend family as the console (§5.1); components restyle onto the design tokens and dock beside the Graph Explorer |

**What the Copilot answers:** "Why is alert #37 ranked above #12?" · "Which top-50 alerts involve cycle motifs touching more than 8 accounts?" · "What does the OECD checklist say about cover bidding, and which flagged tenders match it?" · "Summarize the evidence bundle for this community in plain language." Every answer cites its evidence (SQL rows and/or corpus chunk IDs) and carries the screening-only caveat.

#### Agent-by-agent disposition

| Agent (as built) | Disposition | Change |
|---|---|---|
| router, intent_classifier, planner, hybrid_executor, synthesiser, finaliser | **Keep** | Prompt persona re-write only (investigator copilot, both domains) |
| sql_agent | **Keep, retarget** | `schema.yaml` swapped for the CollusionGraph artifact-store schema; few-shot goldens replaced; read-only SQL enforced (SELECT-only allowlist) |
| rag_agent | **Keep, retarget** | Corpus swapped to `data/corpus/` (red-flag + methodology docs); citation format unchanged |
| **NEW: alert_tools** | **Add** | Tools the loops can call beyond raw SQL: `get_alert(id)`, `get_explanation(id)`, `get_subgraph(id)`, `list_alerts(domain, budget)`, `get_metrics(run)` — thin readers over the artifact store and explanation-bundle JSON |
| critic | **Keep, re-lexicon** | `POLICY_LEXICON` → `RED_FLAG_LEXICON` (smurfing, structuring, layering, fan-in, cycle, bid rotation, cover bidding, market allocation, shell company, beneficial owner, …); both deterministic gates kept verbatim |
| cross_validator, arbiter, completeness_checker | **Keep, gate by config** | Full validation stack for complex questions; a **fast-path config** skips them for simple lookups (the as-built pipeline takes 20s–10min — unacceptable as a default for a console; the conditional edges already exist) |
| clarification, readback | **Keep** | Readback reserved for multi-part analytical questions |
| **NEW: guilt-language guard** | **Add (in finaliser)** | Deterministic post-check: outputs never assert guilt or accusation; flagged phrasings are rewritten to "flagged pattern consistent with …" and every response appends the screening-only caveat — §1.5 enforced in code, not just prose |

#### Infrastructure simplification (verified against the code)

- **Qdrant → embedded dense store.** The corpus is tiny (~50–300 chunks); BM25 is already in-memory, and the retriever already caches all payloads in memory. Dense search moves to an in-process numpy/`sentence-transformers` index; Qdrant, and its docker service, are dropped.
- **Redis: dropped.** The orchestrator uses LangGraph's in-memory checkpointer; Redis was aspirational ("Phase 8") and never wired in.
- **Langfuse + Postgres: optional, off by default.** The code already falls back cleanly to the plain OpenAI client.
- Net effect: the Copilot adds **zero required docker services** — it mounts into the existing FastAPI app at `/api/v1/copilot` (SSE). The **SSE CRLF parser fix** documented in the chatbot's `FIX_FRONTEND.md` is mandatory in the ported client (the fixed `api.ts` is the port source).
- **LLM config:** provider/model via env per machine; a cheaper model may be configured for validator agents (`COPILOT_VALIDATOR_MODEL`) to cut cost/latency; each developer uses their own key (never committed).

#### Cleanup manifest (execute in Week 1 — Phase 0, before the repo is initialized)

| Category | Items | Action |
|---|---|---|
| **Port (source of the Copilot)** | `backend/app/graph/` (orchestrator, state, all agents, prompts as templates), `backend/app/retrieval/`, `backend/app/tools/`, `backend/app/data/` ingestion machinery (pdf_chunker, pdf_ingestion, embeddings, duckdb_loader as template), `backend/app/api/chat.py` (SSE), `llm.py`, `config.py`, `eval/run_goldens.py` (harness only), `frontend/src/components/` (all seven), fixed `api.ts` from `FIX_FRONTEND.md` | Copy into `reference/genai-chatbot/` now; port into `backend/copilot/` + `frontend/src/views/copilot/` in Phase 2 Week 11 |
| **Replace (TechNova domain assets)** | `schema.yaml`, `facts.yaml` / `facts_curated.yaml` / `facts_auto.yaml` (218 KB), `eval/goldens.json`, `POLICY_LEXICON`, all prompt personas | Rebuild for CollusionGraph (artifact-store schema, red-flag facts, 20–30 investigator goldens, red-flag lexicon) |
| **Delete (TechNova data & outputs — no value to this project)** | `Structured data/` (15 xlsx), `Unstructured data/` (15 TechNova PDFs), `TechNova_Data.zip`, `data/db/technova.duckdb` (7.9 MB binary), `query_results/` (~1 MB stale JSON), `eval_20_output.log`, `r1.txt`/`r2.txt`/`r3.txt`, all root one-off scripts (`run_q1.py`, `run_q5.py`, `run_ipo_query.py`, `run_audit_ipo_query.py`, `run_oncall_burnout_query.py`, `run_sales_pipeline_query.py`, `run_spof_query.py`, `run_test_queries.py`, `run_timed_demo.py`, `run_eval_20.py`, `verify_spof.py`), `generate_extra_excels.py`, `generate_extra_pdfs.py`, `__pycache__/`, `frontend/node_modules/`, nested duplicate `.claude/` settings | Delete; none of it enters the new repository |
| **Keep as reference only (not shipped)** | `docs/agent_communication.html`, `docs/architecture.html` (agent-design documentation), `FIX_FRONTEND.md`, `docker-compose.yml` (as pattern) | Move to `reference/genai-chatbot/docs/` |
| **Security (do immediately)** | The chatbot's `.env` contains a **live OpenAI API key** | **Rotate/revoke the key now**; `.env` never enters the repository; each machine keeps its own `.env` from `.env.example` (see R18) |

#### Evaluation & research value

The Copilot is product and RQ3 infrastructure, not a new research question. Its quality gate: the repurposed goldens harness runs 20–30 investigator questions with expected SQL shapes / expected corpus sources; release requires ≥90% of goldens grounded (citations resolve, numbers match evidence) with zero guilt-language violations. If it ships, the practitioner study (§10.3) gains a third arm (bundle-only vs. bundle+Copilot), and the paper gains a systems subsection on grounded conversational oversight — directly supporting the EU AI Act positioning (§10.6). Cut order: the Copilot is cut before any detection-stack item; within it, cross-validation depth and readback are cut before the SQL/RAG core.

---

## 5. Technical Stack — Frontend

### 5.1 Stack

| Concern | Choice | Rationale |
|---|---|---|
| Framework | **React 18+ with TypeScript, Vite** | Per requirements; Vite for fast DX |
| Styling | **Tailwind CSS v4** + CSS custom-property design tokens | Systematic dark-theme design language (deliberately dark-only — an investigator console, not a marketing site) |
| UI primitives | Radix UI (headless) + custom components | Accessible, unstyled — full visual control |
| Graph rendering | **Sigma.js v3 + graphology via `@react-sigma/core`** (WebGL); ForceAtlas2 layouts precomputed server-side for determinism | The strongest WebGL choice for large interactive network views; handles Elliptic++ scale via ego-network windowing |
| Full-dataset overview | **Cosmograph** (GPU force layout) — optional showpiece | Renders hundreds of thousands of nodes/edges for the "whole ledger" hero view |
| 3D flourish | `react-force-graph-3d` (Three.js) — optional, one view only | Immersive demo moment; never the workhorse |
| UI animation | **Motion** (motion.dev — the library formerly published as Framer Motion) | Enter/exit, layout animations, micro-interactions |
| Timeline/scroll animation | **GSAP** (fully free since April 2025, incl. formerly-paid plugins: ScrollTrigger, SplitText, DrawSVG) | Landing/story sequences, SVG motif schematics drawing themselves, timeline scrubbing |
| Charts | **visx** (or D3 directly) for PR curves, precision@k curves, transfer-matrix heatmap; sparklines hand-rolled SVG; **all charts export SVG/PNG** (they double as paper figures) | Publication-quality, fully styleable |
| Data fetching | TanStack Query | Caching, loading/error/empty states as first-class UI |
| Client state | Zustand | Budget k, domain, dataset, selection, graph camera |
| Tables | TanStack Table | Alert-queue virtualization |

### 5.2 Visual Design Language

**Concept: "Intelligence console"** — a dark, precise, investigator-grade environment that looks like a national-security analytics product, not a student dashboard.

- **Palette:** near-black blue-graphite base (`#0A0E17` family); cool neutral text; a restrained signal system — cyan/teal for licit/benign, amber for medium risk, hot coral/red reserved exclusively for flagged subgraphs; a violet accent for the procurement domain vs. teal for financial, so the domain toggle recolors the console subtly.
- **Typography:** Inter (or Geist) for UI; **JetBrains Mono for all numerals, IDs, hashes, amounts** — tabular numbers everywhere data appears.
- **Depth & texture:** subtle grain on panels, 1px hairline borders, soft glass panels (restrained), glow reserved for risk highlights on the graph.
- **Motion principles:** animation communicates state, never decorates idly. Graph transitions (zoom-to-subgraph, neighbor expansion) are eased camera moves (Sigma camera API + GSAP timelines); list/panel transitions via Motion layout animations; numbers count up on first paint; risk pulses slow and subdued. Every data surface has designed loading, error, and empty states.
- **Every screen carries the ethics line** in the footer: *"Screening and triage signals only — no determination of guilt."* (a scope-boundary requirement, not a stylistic choice).

### 5.3 Key Views

1. **Overview / Command deck.** KPI band (graph size, alert budget k, precision@k of current model, alerts pending) with count-up numerals; a Cosmograph/Sigma mini-map of the full network with flagged communities glowing; **domain toggle** (financial ⇄ procurement) and **dataset selector** within each domain (Elliptic++ / AMLworld; Mendeley / García Rodríguez).
2. **Alert Queue.** The core operational surface: virtualized ranked table of top-k deduplicated alerts at a user-adjustable **budget slider** (k = 25…500, or top-% for tenders); each row shows calibrated risk score, motif chip (cycle / fan-in / rotation / cover-bid / common-control…), community size, red-flag count, temporal-activity sparkline. Adjusting the budget animates the precision@k readout — making the paper's central metric *tangible*.
3. **Graph Explorer.** Sigma.js WebGL canvas centered on a flagged subgraph's ego-network: risk-colored nodes, directed edges with amount-scaled width, **motif highlighting** (the explainer-selected minimal subgraph at full opacity while context dims), temporal playback scrubber (GSAP timeline) replaying the money flow / award sequence, neighbor expansion on click, community hulls.
4. **Case Detail / Explanation panel.** The RQ3 surface, docked beside the explorer: the explanation bundle rendered as an evidence dossier — detected motif with an animated SVG schematic (GSAP DrawSVG), evidence fields adapted to dataset coverage (amounts/fees where available, structural evidence otherwise — per §4.3 D1), red-flag cards citing FATF/OECD indicator text with per-source evidence labels, fidelity scores, and an **export button** (JSON alert export — the one case-management touchpoint in scope).
5. **Model Lab / Metrics.** PR curves per model/ensemble, precision@k-vs-k curves with budget markers, **transfer matrix heatmap** (train-market × test-market; cross-domain probe cells highlighted), imbalance-ablation small multiples — all exportable as SVG/PNG. This is the figure factory for the paper.
6. **About / Methodology.** Scroll-driven explainer (GSAP ScrollTrigger) of the two-ledgers-one-structure thesis with the motif table animated — doubles as the demo-day narrative opener.
7. **Copilot dock (Phase 2).** A collapsible right-hand panel available on every view: the ported chat interface (message bubbles, clarification chips, read-back card, live agent-trace timeline, confidence badge, evidence panel) restyled onto the console's design tokens. Context-aware: opened from an alert, the Copilot is seeded with that alert's ID so "explain this" resolves without retyping. Evidence citations in Copilot answers deep-link into the Graph Explorer and corpus viewer. Every Copilot response renders the AI-generated label and the screening-only caveat (§4.6).

### 5.4 Frontend–Backend Connection

- REST over HTTP from FastAPI (`/api/v1/...`), OpenAPI schema → generated TypeScript client (`openapi-typescript`), so API and UI types never drift.
- Subgraph payloads are windowed server-side (ego-network radius + node cap ~2–5k with precomputed layout coordinates) — the browser never receives the full graph; the Cosmograph overview uses a pre-exported downsampled layout file (static JSON/Arrow) computed offline.
- Vite dev proxy in development; single `docker compose up` (API + static frontend) for the demo build, with a non-Docker `poe demo` path for the Windows dev machine.

---

## 6. MVP Feature Scope

### 6.1 Included (maps 1:1 to the problem statement's MVP definition §13)

**ML/backend:**
- Financial adapter (Elliptic++ tx graph; AMLworld HI-Small) and procurement adapter (Mendeley award-first; García Rodríguez if retrievable) → unified IR with license-recorded manifests.
- GraphSAGE + GATv2 (+ R-GCN on procurement) with bidirectional message passing, focal loss/class weighting, stratified sampling; strict-inductive temporal split on Elliptic++ with leakage tests in CI.
- Unsupervised arm: DOMINANT + GAE (PyGOD, homogeneous projections); isotonic-calibrated rank-fusion ensemble; community roll-up; NMS deduplication; alert store.
- Synthetic motif injector v1 covering all five motif-table rows (both domain variants), validated against AMLworld ground-truth patterns.
- PyG Explainer (GNNExplainer) bundles for every surfaced alert (k ≤ 200) + motif matcher + FATF/OECD red-flag mapping with per-source evidence labels.
- Evaluation harness: Precision@k, AUC-PR, FPR/Recall@budget under the defined alert unit; baselines B1–B4; **one LOCO procurement transfer split**; **one cross-domain frozen-probe experiment** (both directions; honest reporting).
- FastAPI serving precomputed artifacts.

**Frontend:**
- Views 1–5 (§5.3) in the full design language; view 6 (methodology scroll-story) at reduced polish if time-boxed.
- Domain toggle, dataset selector, budget slider, motif highlighting, explanation dossier, JSON alert export, designed loading/error/empty states.

### 6.2 Explicitly Excluded from MVP

- OCDS bulk ingestion (Phase 2); AMLworld Medium (Phase 2); AMLworld Large (out of scope entirely).
- **Investigator Copilot (Phase 2, Week 11)** — the Gen-AI Chatbot port (§4.6) waits until the artifact store it queries exists and is stable; only the Week-1 cleanup/archival of its source happens before then.
- Line-graph views, PNA/GIN+EU reference reproductions, PGExplainer, TGN, hit-rule/dedup sensitivity ablations (Phase 2).
- Full LOMO/LOCO matrices, multi-seed CIs, DANN/CORAL adaptation, practitioner study (Phase 2).
- Authentication, multi-user, roles; real-time/streaming scoring; model training triggered from the UI; PDF export (JSON only in MVP); case-management workflow beyond alert export; any UAE institutional data; production hardening (target is TRL 3–4 validated prototype).
- 3D graph view and Cosmograph hero (optional garnish — first items cut under schedule pressure).

---

## 7. Detailed Build Roadmap

Assumes a solo builder at capstone intensity on a Windows 11 dev machine (cloud GPU via Colab/Kaggle as needed). Weeks are working-week-sized units; dependencies are strictly ordered within a phase. **Slack policy: each phase carries ~10% unallocated buffer; the cut order under pressure is fixed (3D/Cosmograph → methodology page → TGN → AMLworld Medium).**

### Milestone summary

| Milestone | Week | Definition of done |
|---|---|---|
| M0 | 1 | All datasets downloaded, checksummed, licensed, EDA'd; environment reproducible |
| M1 | 3 | Baseline scoreboard (B1–B3) exists on both anchors |
| M2 | 4 | GNNs beat baselines on Precision@100 (Elliptic++), or gap understood & documented |
| M3 | 5 | Ensemble + injection-recovery report |
| M4 | 6 | Every top-k alert on both domains carries a validated explanation bundle |
| M5 | 8 | **MVP exit criterion:** clone → one command → dashboard → alert → explained subgraph, both domains |
| MC | 11 | Copilot ported, grounded on the artifact store + corpus, goldens gate passed (§4.6) |
| M6 | 13 | All Phase-2 experiments complete, multi-seed, CI'd |
| M7 | 14 | Practitioner study + full ablation grid complete |
| M8 | 17 | Paper submitted; reproducibility package archived (Zenodo DOI) |

### Phase 0 — Foundations (Week 1)

1. Repo scaffold (monorepo per §8); Python env (`uv`) with pinned PyTorch/PyG (no compiled extensions)/PyGOD; poethepoet task definitions; verify GPU/Colab path; pre-commit (ruff, black, mypy); CI skeleton (GitHub Actions: lint + unit tests + frontend build).
2. **Dataset acquisition sprint — de-risk immediately:** download, checksum, and **record licenses** for Elliptic++ (GitHub), Elliptic (PyG), AMLworld HI-Small (Kaggle, API key), Mendeley f3y4nrn3s6/2; **attempt García Rodríguez supplement (ec0010) now** — if blocked, trigger fallback R2 (§11) this week, not in Week 6.
3. EDA notebooks per dataset: schema, label prevalence, temporal coverage; confirm Elliptic++ counts (183 features; 4,545/42,019 labels; 49 steps), measure Mendeley cartel prevalence and cartel-case counts, and **map losing-bidder coverage by country-year** (drives the co-bid enrichment tier).
4. **Gen-AI Chatbot triage:** execute the §4.6 cleanup manifest — copy the port-source code and reference docs into `reference/genai-chatbot/`, delete all TechNova data/results/one-off scripts, **rotate the live OpenAI key found in its `.env`**, and confirm `.env` patterns are gitignored before the first commit. **Milestone M0.**

### Phase 1 — MVP

**Week 2 — Data spine.**
4. Implement CollusionGraph IR (Parquet schemas + Pydantic models + DuckDB catalog + alert schema).
5. Financial adapter: Elliptic++ → IR; AMLworld HI-Small → IR. Golden-file tests on tiny fixtures.
6. Procurement adapter: Mendeley → IR (award-first graph + co-bid enrichment where covered + cartel labels); García Rodríguez → IR if available.
7. Strict-inductive temporal splitter + LOCO splitter, with **leakage assertion tests in CI** (no test-period edge reachable at train time; as-of-timestamp feature computation).

**Week 3 — Features, baselines, and the metric harness (baselines before GNNs — RQ1 needs the yardstick first).**
8. Shared structural feature template (per-graph z-scoring) + domain feature packs (screens incl. award-derived tier, burstiness, etc.).
9. Evaluation harness: alert unit + hit rule + NMS dedup; Precision@k, AUC-PR, FPR/Recall@budget; plots; config-driven runs logged to W&B (offline mode ok).
10. Baselines B1 (rules), B2 (XGBoost tabular), B3 (XGBoost + graph features), B4 (screens-only, procurement) on Elliptic++ and Mendeley. **Milestone M1.**

**Week 4 — Supervised GNN core.**
11. GraphSAGE + GATv2 with `NeighborLoader`, bidirectional edges + direction flags, focal loss vs. class weights, early stopping on val AUC-PR; Elliptic++ first (unknown-label policy per §4.3 D1).
12. R-GCN on the heterogeneous procurement graph (forward/reverse relations).
13. Leiden communities + roll-up + calibration + NMS → first end-to-end alert queue. **Milestone M2.**

**Week 5 — Unsupervised arm, ensemble, injection.**
14. PyGOD DOMINANT + GAE on homogeneous projections of both domains; structural z-score floor.
15. Isotonic calibration per member + rank-fusion ensemble on validation folds.
16. Synthetic motif injector v1 — all five motif-table rows, both domain variants; validate recovery on AMLworld's labeled patterns (recall of injected motifs at budget). **Milestone M3.**

**Week 6 — Explanations.**
17. PyG `Explainer` + GNNExplainer over top-k alerts; thresholded minimal subgraphs; fidelity metrics; HeteroExplanation validated on an R-GCN fixture first (de-risks R12).
18. Motif matcher (directed cycle/star/clique + screens) + curated FATF/OECD red-flag mapping tables + per-source evidence labels.
19. Explanation-bundle JSON schema + batch writer, with per-dataset evidence-field adaptation (D1 caveat). **Milestone M4.**

**Week 7 — Transfer probes + API.**
20. One LOCO split on procurement (train 6 countries → test 1); Precision@k reported.
21. Cross-domain frozen-encoder probe on the shared structural channel (both directions).
22. FastAPI: `/domains`, `/datasets`, `/alerts`, `/alerts/{id}`, `/subgraph/{id}`, `/explanations/{id}`, `/metrics`, `/transfer-matrix`; artifact-store wiring; server-side ego-network windowing with precomputed layouts; OpenAPI → TS client.

**Week 8 — Dashboard.**
23. Frontend scaffold (Vite/TS/Tailwind/tokens); layout shell + domain toggle + dataset selector; loading/error/empty states.
24. Alert Queue (virtualized, budget slider) → Graph Explorer (Sigma.js ego-networks, motif highlighting, temporal scrubber) → Case Detail dossier → Model Lab charts (with SVG/PNG export).
25. Polish pass (Motion micro-interactions, GSAP motif schematics), demo script, `poe demo` + docker-compose. **Milestone M5 = MVP exit criterion.**

**⛔ Stop point: MVP review with stakeholder (you) before Phase 2 development.**

### Phase 2 — Publication-Ready

**Weeks 9–10 — Model depth & scale.**
26. Line-graph auxiliary view; PNA and GIN+EU reference configs (Multi-GNN parity check on AMLworld HI-Small); AMLworld Medium run (cloud GPU); Elliptic++ actor-graph heterogeneous experiment; *(stretch)* TGN variant.
27. PGExplainer trained for amortized queue-scale explanation; explainer ablation (GNNExplainer vs. PGExplainer vs. attention-only) on fidelity. Ethics-review requirements for the practitioner study checked now (lead time).

**Week 11 — Investigator Copilot integration (§4.6).**
27a. Port the archived chatbot backend into `backend/copilot/`: retarget the SQL agent to read-only views over the artifact store (new `schema.yaml`, SELECT-only allowlist); swap the RAG corpus to `data/corpus/` (FATF/OECD/methodology docs, license-checked); add `alert_tools`; replace `POLICY_LEXICON` with the red-flag lexicon; add the guilt-language guard + caveat suffix in the finaliser; drop Qdrant/Redis/Langfuse per §4.6 (embedded dense store); mount at `/api/v1/copilot`.
27b. Port the frontend components into the Copilot dock (view 7, §5.3) with the SSE CRLF parser fix; restyle onto design tokens; wire context-seeding from alerts and citation deep-links.
27c. Rebuild `goldens.json` with 20–30 investigator questions; run the goldens gate (≥90% grounded, zero guilt-language violations); wire the goldens run into CI as a manually-triggered job (needs an API key). **Milestone MC.**

**Weeks 12–13 — Transfer science & rigor.**
28. Full LOMO/LOCO matrices (all procurement markets); cross-typology AMLworld held-out-pattern study; cross-domain fine-tuning label-efficiency curves; (stretch) CORAL/DANN on the structural channel.
29. Multi-seed (≥5) reruns of all headline experiments; bootstrapped CIs; paired-bootstrap significance tests; budget-sensitivity curves; hit-rule and NMS-threshold sensitivity; label-noise robustness check on Elliptic++.
30. OCDS publisher ingestion (bid-data publisher preferred) + synthetic injection at scale for the unsupervised regime. **Milestone M6.**

**Week 14 — Explanation study & ablations.**
31. Practitioner rubric study (§10.3), including the bundle-only vs. bundle+Copilot arm if MC passed.
32. Component ablations: −unsupervised arm, −screens-as-features, −focal loss, −injection, −temporal encodings, −bidirectional edges. **Milestone M7.**

**Weeks 15–17 — Paper & artifacts.**
33. Figures from the Model Lab; tables from the harness; model card + dataset datasheets; writing (§10.4); internal red-team review against the evaluation-protocol checklist; reproducibility package (configs, seeds, download scripts, frozen environment); submit to primary venue; archive code with a Zenodo DOI. **Milestone M8.**

### Collaboration & Handoff Workflow (multi-developer via GitHub)

Development is shared across collaborators through GitHub; continuity between sessions and developers is a designed artifact, not an accident:

- **Branching:** trunk-based — `main` is always green and demoable; all work happens on short-lived feature branches (`feat/<area>-<slug>`, `fix/…`, `docs/…`) merged via pull request. PRs require green CI (lint + unit + leakage tests + frontend build) and a description stating which milestone (M0–M8) the change advances, test status, and known gaps.
- **Commits:** conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:` + scope), small logical units.
- **`PROGRESS.md` ledger (repo root)** — the single running record of: (a) current milestone position, (b) **Completed** (dated, with commit refs), (c) **In-flight** (exactly what is unfinished and where), (d) **Next actions** (ordered, concrete, self-contained — executable by the next developer without a conversation), (e) **Decision log** (every deviation from this plan, with rationale), (f) **Known issues**. Updating it is a required pre-push step, enforced as a PR checklist item.
- **`handoff-prompt.md` (repo root)** — a reusable, stage-agnostic prompt that any developer (or AI coding session) runs at the start of a session. It forces an orient → verify → plan → build → hand-off loop that derives project state from the repository itself (git log, tree vs. §8 layout, test run, `PROGRESS.md`) rather than trusting anyone's memory, then requires the ledger update before pushing. Both files are committed in the repo scaffold (Week 1, step 1).
- **The plan documents govern:** `implementation-plan.md` is the authority for architecture and protocol decisions; changing a settled decision requires a Decision-log entry, never a silent divergence.

---

## 8. File & Folder Structure

```
collusiongraph/
├── README.md                        # quickstart, demo instructions, ethics statement
├── pyproject.toml                   # uv-managed; pinned deps; poethepoet tasks
│                                    #   (poe data / train / score / explain / eval / demo)
├── Makefile                         # optional thin aliases of poe tasks for *nix CI
├── docker-compose.yml               # api + frontend demo build
├── LICENSE                          # Apache-2.0 (code); dataset licenses live in manifests
├── .github/workflows/ci.yml         # lint, typecheck, unit + leakage tests, frontend build
├── Collusion-Network-Detection.md   # the problem statement (source of truth)
├── implementation-plan.md           # this document
├── PROGRESS.md                      # running dev ledger: milestone status, completed/in-flight,
│                                    #   next actions, decision log — updated on every push (§7)
├── handoff-prompt.md                # reusable session prompt for any developer/AI joining mid-stream
│
├── configs/                         # Hydra/YAML — one file = one reproducible experiment
│   ├── data/        (elliptic_pp.yaml, amlworld_hi_small.yaml, mendeley_eu.yaml,
│   │                 garcia_rodriguez.yaml, ocds_<publisher>.yaml)
│   ├── model/       (graphsage.yaml, gatv2.yaml, rgcn.yaml, dominant.yaml,
│   │                 ensemble.yaml, pna.yaml, line_graph.yaml, tgn.yaml)
│   ├── train/       (imbalance ablation variants, seeds)
│   ├── eval/        (budgets.yaml, alert_unit.yaml, transfer_lomo.yaml, cross_domain.yaml)
│   └── experiment/  (named end-to-end experiment compositions)
│
├── data/                            # gitignored except manifests
│   ├── raw/         (elliptic_pp/, amlworld/, mendeley_eu/, garcia_rodriguez/, ocds/)
│   ├── corpus/      (Copilot RAG corpus: FATF indicators, OECD 2025 checklist excerpts
│   │                 [license-checked], methodology docs, datasheets — committed, small)
│   ├── manifests/   (checksums + source URLs + download dates + LICENSES — committed)
│   ├── interim/     (adapter outputs: IR parquet per dataset)
│   └── processed/   (materialized PyG datasets, split indices, injected variants,
│                     precomputed layouts)
│
├── backend/
│   ├── collusiongraph/              # the Python package
│   │   ├── schema/                  # IR: pydantic models, parquet schemas, duckdb catalog,
│   │   │                            #   alert schema
│   │   ├── adapters/                # financial.py, procurement.py, ocds.py, registry.py
│   │   ├── features/                # structural.py (shared template, per-graph z-scoring),
│   │   │                            #   financial.py, screens.py (award-tier + bid-tier)
│   │   ├── injection/               # generators/ (cycle, fan_in, fan_out, scatter_gather,
│   │   │                            #   common_control, pass_through, rotation, cover_bid,
│   │   │                            #   partition, coordinated_cluster) + calibration.py
│   │   ├── splits/                  # temporal_strict.py, loco.py, lomo.py, leakage_checks.py
│   │   ├── models/                  # sage.py, gatv2.py, rgcn.py, line_graph.py, pna.py,
│   │   │                            #   tgn.py, unsupervised.py (PyGOD wrappers),
│   │   │                            #   ensemble.py (isotonic + rank fusion), rollup.py,
│   │   │                            #   dedup.py (NMS)
│   │   ├── training/                # loops, losses (focal), samplers, checkpoints, wandb hooks
│   │   ├── explain/                 # explainer_runner.py (PyG Explainer), motif_matcher.py,
│   │   │                            #   redflags/ (fatf.yaml, oecd.yaml), bundles.py, fidelity.py
│   │   ├── eval/                    # metrics.py (P@k, AUC-PR, FPR@budget), alert_unit.py,
│   │   │                            #   transfer.py, bootstrap.py, report.py
│   │   ├── artifacts/               # alert store, model registry, export
│   │   └── cli.py                   # collusiongraph {ingest,train,score,explain,eval,serve}
│   ├── copilot/                     # Phase 2 — ported Gen-AI Chatbot (§4.6): graph/ (orchestrator,
│   │                                #   state, agents incl. alert_tools + guilt-language guard),
│   │                                #   retrieval/ (embedded dense + BM25), tools/, schema.yaml,
│   │                                #   redflag lexicon, goldens.json + goldens harness
│   ├── api/                         # FastAPI app: routers/ (alerts, subgraph, explanations,
│   │                                #   metrics, domains, datasets, transfer, copilot [SSE]),
│   │                                #   services/, schemas/
│   └── tests/                       # unit/ integration/ fixtures/ (tiny synthetic graphs)
│
├── frontend/
│   ├── src/
│   │   ├── app/                     # routes, layout shell, providers
│   │   ├── views/                   # overview/, alert-queue/, graph-explorer/,
│   │   │                            #   case-detail/, model-lab/, methodology/,
│   │   │                            #   copilot/ (Phase 2 dock — ported chat components)
│   │   ├── components/              # ui/ (design system incl. loading/error/empty states),
│   │   │                            #   graph/ (sigma wrappers, hulls, temporal scrubber),
│   │   │                            #   charts/ (visx + svg/png export), motifs/ (SVG schematics)
│   │   ├── state/                   # zustand stores (budget, domain, dataset, selection, camera)
│   │   ├── api/                     # generated TS client + TanStack Query hooks
│   │   ├── styles/                  # tokens.css, tailwind config, themes (financial/procurement)
│   │   └── lib/                     # formatters (amounts, hashes), motif metadata
│   ├── public/                      # pre-exported overview layout (arrow/json), fonts
│   └── tests/                       # vitest unit + playwright e2e
│
├── reference/                       # genai-chatbot/ — archived port source + design docs
│                                    #   (FIX_FRONTEND.md, agent HTML docs); reference only, not shipped
├── notebooks/                       # numbered, read-only after merge: 01_elliptic_eda.ipynb …
├── scripts/                         # download_data.py (incl. kaggle auth), export_overview_layout.py,
│                                    #   make_figures.py
├── eval_outputs/                    # metrics.json, tables/, figures/  (regenerable; gitignored)
├── paper/                           # main.tex, sections/, figures/, bib/, venue templates
└── docs/                            # architecture.md, api.md, red_flag_mappings.md,
                                     #   ethics_and_scope.md, model_card.md, datasheets/,
                                     #   demo_script.md, DATASETS.md
```

---

## 9. Testing Strategy

### 9.1 ML Correctness (the tests that protect the paper)

- **Leakage tests (highest priority).** CI-run assertions that (a) no test-period node/edge is reachable during training-time message passing under the strict-inductive split; (b) no feature is computed using future information (feature functions take an as-of timestamp); (c) LOCO/LOMO folds share no entities across train/test. The ~39.5-F1 leakage result on Elliptic (arXiv:2604.19514) shows exactly how a capstone gets invalidated.
- **Metric & alert-unit tests.** Precision@k / AUC-PR / FPR@budget validated against hand-computed values on toy score vectors and against scikit-learn where overlapping; **NMS dedup and hit-rule logic tested on constructed overlapping-alert fixtures** (e.g., two alerts sharing 60% members → exactly one survives).
- **Adapter golden files.** Tiny fixture inputs per dataset → committed expected IR outputs; Pydantic schema validation on every adapter run; procurement fixtures include an award-only country (no bid data) to prove the enrichment-tier degradation path.
- **Injection recovery tests.** Injector plants known motifs from all five motif-table rows into a fixture graph → the motif matcher must recover them with 100% recall (matcher and injector are independent implementations, so this cross-validates both).
- **Model sanity suite.** Overfit-single-batch test (loss → ~0), seed-determinism test, gradient-flow test, shape/dtype tests per model class, calibration monotonicity test (isotonic output ordering preserved).
- **Explanation invariants.** Every bundle: non-empty minimal subgraph ⊆ input graph; motif params consistent with subgraph; every red-flag citation resolves to a curated indicator; evidence fields match the dataset's declared coverage tier; fidelity+ ≥ fidelity− sanity check.

### 9.2 System Testing

- **Backend:** pytest unit coverage on schema/adapters/features/splits/metrics/dedup; integration test running the full pipeline (ingest → train 2 epochs → score → explain → eval) on a tiny synthetic dataset in CI (<5 min); API contract tests via FastAPI `TestClient` against the OpenAPI schema.
- **Frontend:** Vitest for stores/formatters/chart math; Playwright E2E for the demo-critical path (open queue → adjust budget → open alert → see highlighted subgraph → read explanation → export JSON); visual-regression screenshots on the four core views; axe-based accessibility checks (contrast on the dark theme, keyboard navigation of the queue).
- **Performance budgets:** graph explorer interactive at 5k rendered nodes (60fps camera ops on mid-range hardware); API subgraph endpoint p95 < 300ms from DuckDB/Parquet; dashboard cold load < 3s.
- **Platform check:** the full `poe demo` path is exercised on Windows (primary dev machine) and in Linux CI, so the demo never depends on a *nix-only toolchain.
- **Copilot (Phase 2):** goldens gate as the release test (20–30 investigator questions; ≥90% grounded — citations resolve, numbers appear in evidence; zero guilt-language violations); unit tests for the SELECT-only SQL allowlist, the red-flag grounding gate, the numeric-sanity gate on alert evidence, and the guilt-language guard (adversarial phrasings fixture); SSE contract test with CRLF framing; goldens run wired as a manually-triggered CI job (requires an API key secret).

### 9.3 Scientific Validation (Phase 2)

- Multi-seed reruns with CIs; budget-, hit-rule-, and NMS-threshold-sensitivity analyses; ablation-grid completeness checked against a manifest; an internal **red-team checklist** pass before submission (leakage, imbalance reporting, baseline fairness — same tuning budget for baselines, honest transfer reporting); reproduction-from-scratch of headline numbers on a clean clone following the README only.

---

## 10. Path to Publication

### 10.1 Positioning

Primary framing: *the first cross-domain study of collusion-structure transfer between illicit-finance and procurement-cartel networks, delivered by one imbalance-robust, explainable, budget-evaluated stack.* The merge is the moat (problem statement §12): even if either single-domain result is matched by concurrent work, the cross-domain study and single-stack demonstration are novel.

### 10.2 Required Experiments Beyond MVP

1. **Baseline table** (B1–B6) on both anchors at all budgets, multi-seed.
2. **Imbalance ablation:** focal vs. class weights vs. stratified sampling vs. injection, and combinations — directly answering the instability documented by Lawal et al. (2025).
3. **Component ablation:** full ensemble vs. −unsupervised, −screens, −temporal encodings, −line-graph, −bidirectional edges.
4. **Protocol sensitivity:** budget k, hit rule, NMS threshold; node-level vs. community-level queues (contextualized by the queue-granularity findings of arXiv:2604.23494).
5. **Transfer matrices:** LOMO/LOCO within procurement (comparable to Imhof et al.'s 91%/84% cross-market results and Gomes et al.'s OOD study); held-out-pattern within AMLworld; the cross-domain probe/fine-tune/label-efficiency suite in both directions.
6. **Explanation evaluation:** fidelity metrics + practitioner study (RQ3) with inter-rater agreement.
7. **Scale demonstration:** AMLworld Medium; OCDS injection study.
8. **Honest-limitations section:** Elliptic time-step-43 distribution shift; anonymized Elliptic features limiting evidence narratives; synthetic-data caveats (AMLworld); losing-bid coverage gaps in EU procurement data; label noise; cross-domain transfer magnitude whatever it is.

### 10.3 Practitioner Study Design (RQ3)

≥5 raters with AML-compliance or audit familiarity; ~20 alerts sampled across domains/strata; instrument: per-alert Likert ratings on verifiability ("could you confirm this from the evidence shown?"), red-flag alignment ("does the cited indicator match?"), and actionability ("would this justify escalation?"), plus free text; report means, agreement (Krippendorff's α), and qualitative themes. Ethics-review requirements checked in Week 9–10 (lightweight — no sensitive data — but capstone rules vary). **Recruitment fallback (R14):** if practitioner raters cannot be recruited, use rubric-trained graduate raters plus at least one domain expert, and report the substitution as a limitation.

### 10.4 Paper Skeleton

Abstract → Introduction (two ledgers, one structure) → Related work (graph anomaly detection: Ma et al. 2023; AML GNNs: Motie & Raahemi 2024, LineMVGNN, Lawal et al., ChronoWave-GNN — cited cautiously per its own ablation, Multi-GNN/AMLworld line incl. arXiv:2412.00241; evaluation-protocol critiques: arXiv:2604.19514, arXiv:2604.23494; cartel GNNs: Imhof et al., Gomes et al.; screens tradition: García Rodríguez, IJIO 2025; validation gap: EPJ mapping study 2025; graph-foundation-model transferability framing for RQ4: arXiv:2505.15116, arXiv:2503.09363; GADBench baseline discipline: arXiv:2306.12251; LLM-augmented explanation: arXiv:2506.14933, arXiv:2507.14785) → Unified problem & schema → Method (detection, imbalance, explanation) → Evaluation protocol (budget-first, leakage-safe, alert-unit-explicit) → Results (RQ1–RQ4) → Explanation study → Regulatory alignment & ethics (EU AI Act high-risk obligations, applicable 2 Aug 2026; CBUAE Art. 149; screening not accusation; TRL 3–4) → Reproducibility statement (incl. model card, datasheets).

### 10.5 Venues (reconciled with the problem statement)

| Venue | Fit | Notes |
|---|---|---|
| **ACM ICAIF** | Primary — merged paper led by the AML result | Annual cycle; check CFP ~mid-year |
| **KDD workshops** (anomaly/graph mining/fraud, e.g. MLF) | Primary alternate — natural home for the merged cross-domain framework | Shorter format, faster feedback |
| **EPJ Data Science** | If led by the procurement/computational-social-science angle | Journal — no deadline pressure; the 2025 mapping study is published there |
| **ACM DGov** | Governance/audit framing of the procurement arm | Journal |
| **IEEE Big Data** | Scale-oriented alternative | ~Aug/Sep deadline typically |

Strategy: target ICAIF or a KDD workshop first (conference-cycle feedback), with EPJ DS as the journal fallback that carries no deadline risk.

### 10.6 Frontier Positioning — why this framing is maximally relevant in July 2026

Four currents in the mid-2026 research and regulatory landscape, and how this project rides each:

1. **The EU AI Act's high-risk obligations become enforceable on 2 August 2026** — weeks after this project's start — and AI used for fraud detection and AML monitoring is explicitly in scope. Explainability, traceability, human oversight, and auditability shift from good practice to legal requirement (penalties up to €35M / 7% of turnover). This system's explanation bundles, fixed-budget human-in-the-loop triage, audit-ready alert export, and "screening not accusation" design are precisely the required properties — so the paper gains a **regulatory-alignment subsection** (EU AI Act Art. 6/Annex III + CBUAE Art. 149) that, to our knowledge, no prior AML-GNN or cartel-GNN paper has offered. This is the single strongest freshness hook available and costs almost nothing to add.
2. **Graph foundation models are the field's hottest open conversation** (KDD 2025 keynote-track surveys; transferability is their named central question). RQ4 — does collusion structure learned in one real-world domain transfer to another — is a direct, falsifiable case study of GFM-style substructure transferability on a socially consequential task. Framing RQ4 in GFM vocabulary (arXiv:2505.15116; arXiv:2503.09363) positions the paper inside that conversation regardless of whether the transfer result is positive or negative.
3. **GADBench discipline.** The benchmark community's sharpest critique of GAD papers is weak simple baselines. Building GADBench's strongest simple baseline (XGB-Graph) into RQ1 (§4.5 B3) inoculates the paper against its most predictable review objection.
4. **LLM-augmented explanation** is the emerging 2025–26 interpretability trend in financial crime analytics. The Investigator Copilot (§4.6) — a ported, already-working multi-agent system whose critic enforces evidence grounding and numeric sanity deterministically — engages this trend at a level beyond one-shot narration: investigators *interrogate* the system's evidence conversationally, with a measurable practitioner-study arm. Participation in the trend without dependence on it (the detection core stands alone).

---

## 11. Risks, Assumptions & Mitigations

| # | Risk | Likelihood / Impact | Mitigation |
|---|---|---|---|
| R1 | **Cross-domain transfer (RQ4) yields weak/no signal** | Medium / Low-as-framed | The problem statement pre-commits to honest reporting; a rigorous negative/partial result on a never-studied question is still novel. The paper stands on RQ1–RQ3 alone. |
| R2 | **García Rodríguez supplement (ec0010) not retrievable** | Medium / Medium | Attempted in Week 1, not Week 6. Fallbacks: Mendeley as sole labeled procurement anchor (sufficient for all RQs); per-market public sources cited by Gomes et al.; author contact. LOCO on Mendeley's 7 countries still yields a full cross-market study. |
| R3 | **Instability under imbalance** (the documented failure we target) | High / High if unmanaged | It is the research subject: the imbalance-ablation grid, injection with known ground truth, PR-based model selection, and multi-seed CIs measure and control it. |
| R4 | **Leakage invalidates results** | Medium / Fatal | Strict-inductive splits + CI-enforced leakage tests from Week 2 (§9.1); as-of-timestamp feature computation. |
| R5 | **Elliptic temporal distribution shift** (time step 43) | Certain / Medium | Per-time-step metrics; explicit discussion; it strengthens the budget-based framing (models compared under the same shift). |
| R6 | **Synthetic/anonymized data limits realism claims** — AMLworld is synthetic; Elliptic features are anonymized | Certain / Low-Medium | Use each dataset for what it is uniquely good for (AMLworld: ground-truth patterns, amounts, scale; Elliptic++: real-world structure); evidence narratives adapt per dataset (§4.3 D1); named explicitly in limitations. |
| R7 | **Explanation quality is subjective** | Medium / Medium | Pair human rubric with objective fidelity metrics; publish the rubric; report agreement. |
| R8 | **Compute limits** (single GPU) | Low / Medium | Elliptic++/Mendeley train on one GPU; NeighborLoader for AMLworld HI-Small; Medium via cloud GPU in Phase 2; Large out of scope. |
| R9 | **Frontend scope creep** eats ML time | Medium / Medium | Dashboard time-boxed to Week 8 with a fixed cut order; the Model Lab doubles as paper-figure tooling so frontend time repays paper time. |
| R10 | **Concurrent publication** on either single arm | Medium / Low | The merge is the moat (problem statement §12); monitor arXiv monthly (safe-graph index + new 2026 AML work such as BlazingAML and Tide). |
| R11 | **Ethics/positioning drift** — system read as an accusation engine | Low / High | Scope language hard-coded into UI footer, API `caveats` field, README, and paper; no per-person outputs; public/synthetic data only, consistent with §17 of the problem statement. |
| R12 | **PyG/PyGOD version friction** (hetero explainability edges) | Medium / Low | Pin versions Week 1; integration test in CI; HeteroExplanation validated on a fixture at the start of Week 6. |
| R13 | **Losing-bidder data gaps in EU procurement** (verified: not systematically collected across the Mendeley countries) | Certain / Medium | Award-network-first schema (§4.2); precomputed screens used where raw bids absent; co-bid enrichment tiered by country-year coverage (Week-1 EDA map); García Rodríguez markets (which include losing bids) carry the full bid-level analysis; OCDS publisher chosen for bid coverage. |
| R14 | **Practitioner raters hard to recruit** | Medium / Medium | Fallback: rubric-trained graduate raters + ≥1 domain expert; substitution reported as a limitation (§10.3). |
| R15 | **Dataset licensing constraints** on redistribution | Low / Low-Medium | Licenses recorded in `data/manifests/` in Week 1; the repo ships download scripts, never raw data; reproducibility package points to canonical sources. |
| R16 | **Copilot LLM cost & latency** — the as-built pipeline takes 20s–10min per query and every agent call is billed | Certain / Medium | Fast-path config (validation stack gated to complex questions — the conditional edges already exist); cheaper model for validator agents; goldens run is a manual CI job, not per-commit; per-developer API keys with spend limits. |
| R17 | **Copilot scope creep** — an already-working chatbot is seductive to polish while the research core waits | Medium / High | Copilot is locked to Phase 2 Week 11 with a hard cut order: it is cut before any detection-stack item; MVP (M0–M5) contains zero Copilot work beyond the Week-1 archival. |
| R18 | **Secret hygiene** — a live OpenAI key was found in the chatbot's `.env` | Certain (found) / High if leaked | Rotate/revoke the key in Week 1 before the repo is initialized; `.env` in `.gitignore` from the first commit + a pre-commit secret-scanning hook (gitleaks); each machine keeps its own key; keys never appear in `PROGRESS.md`, commits, or PRs. |

**Assumptions:** solo builder at capstone intensity on Windows 11, with one consumer GPU or free cloud GPU; all five datasets remain publicly available (problem statement §12 argues they are the standing standards); no UAE institutional data enters the project at any point; university capstone rules permit a lightweight-review practitioner rubric.

---

## 12. References

### From the problem statement — policy, mandate, threat assessment

1. INTERPOL, *Global Financial Fraud Threat Assessment* (2nd ed.), 16 March 2026 — global fraud risk "high"; "industrialization of fraud"; cites ~USD 442B 2025 loss estimate. https://www.interpol.int/en/News-and-Events/News/2026
2. US DOJ announcement, FBI–Dubai Police–China MPS operation (9 scam centres, 276 arrests, >USD 701M crypto restrained), 29 April 2026 — https://www.justice.gov ; secondary: *The Next Web*, https://thenextweb.com
3. CBUAE Federal Decree-Law No. 6 of 2025 (effective 16 Sep 2025), Article 149 — https://www.centralbank.ae
4. Tawazun Council procurement mandate (IDEX, Feb 2021) — *The National*: https://www.thenationalnews.com/business/aviation/tawazun-to-manage-procurement-process-of-uae-armed-forces-and-abu-dhabi-police-1.1172144 ; *Janes*; *Khaleej Times*; https://www.tawazun.ae
5. OECD, *Guidelines for Fighting Bid Rigging in Public Procurement (2025 Update)*, DOI 10.1787/cbe05a56-en — procurement ≈13% of GDP; bid-rigging elimination could cut prices 20%+. https://www.oecd.org/en/publications/2025/09/oecd-guidelines-for-fighting-bid-rigging-in-public-procurement-2025-update_127880ea/full-report.html
6. FATF, UAE removed from grey list, 23 February 2024 — https://www.fatf-gafi.org

### From the problem statement — financial-crime methods & datasets

7. Poon et al., "LineMVGNN: Anti-Money Laundering with Line-Graph-Assisted Multi-View Graph Neural Networks," *AI* (MDPI) 6(4):69, 2025 — https://www.mdpi.com/2673-2688/6/4/69
8. Lawal, Okolie & Obunadike, "An Explainable GNN Framework for AML in Cryptocurrency Transactions Using the Elliptic Dataset," *IJCNC*, 17 Dec 2025 — instability under imbalance despite class weighting/focal loss. https://www.ijcnc.com
9. Lin et al., "Detecting illicit transactions in bitcoin: a wavelet-temporal graph transformer approach," *Scientific Reports* 16:1548, 13 Jan 2026, DOI 10.1038/s41598-025-23901-3 — cited cautiously per its own ablation (~0.01 wavelet gain).
10. Elmougy & Liu, "Demystifying Fraudulent Transactions and Illicit Nodes in the Bitcoin Network for Financial Forensics" (Elliptic++), KDD 2023, arXiv:2306.06108 — https://github.com/git-disl/EllipticPlusPlus ; base Elliptic via PyG `EllipticBitcoinDataset` and Kaggle (ellipticco/elliptic-data-set).
11. Altman et al., "Realistic Synthetic Financial Transactions for AML Models" (IBM AMLworld), NeurIPS 2023 D&B, arXiv:2306.16424 — https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml

### From the problem statement — procurement methods & datasets

12. Imhof, Viklund & Huber, "Catching Bid-rigging Cartels with Graph Attention Neural Networks," arXiv:2507.12369 (2025) — 13 markets, 7 countries; ~91% best cross-market, ~84% avg across 12 markets. https://arxiv.org/abs/2507.12369
13. Gomes, Kueck, Mattes, Spindler & Zaytsev, "Collusion Detection with Graph Neural Networks," arXiv:2410.07091 (2024) — R-GCNs; zero-shot/OOD transfer study. https://arxiv.org/abs/2410.07091
14. "Detection of fraud in public procurement using data-driven methods: a systematic mapping study," *EPJ Data Science* (2025), DOI 10.1140/epjds/s13688-025-00569-3 — real-world-validation gap.
15. García Rodríguez et al., "Collusion detection in public procurement auctions with machine learning algorithms," *Automation in Construction* 133:104047 (2022) — https://www.sciencedirect.com/science/article/pii/S0926580521004982
16. Fazekas, Wachs, Tóth & Abdou, "Public procurement cartels: A large-sample testing of screens using machine learning," *IJIO* (2025) — https://www.sciencedirect.com/science/article/pii/S0167718725000943 ; dataset: Mendeley Data, DOI 10.17632/f3y4nrn3s6.2 — https://data.mendeley.com/datasets/f3y4nrn3s6/2 (source of the losing-bid-coverage caveat, §4.3 D4)
17. Open Contracting Data Standard — https://data.open-contracting.org ; https://standard.open-contracting.org

### From the problem statement — supporting

18. Ma et al., "A Comprehensive Survey on Graph Anomaly Detection with Deep Learning," *IEEE TKDE* 35(12), 2023, arXiv:2106.07178.
19. Motie & Raahemi, "Financial fraud detection using graph neural networks: A systematic review," *Expert Systems with Applications*, 2024 — https://www.sciencedirect.com/science/article/pii/S0957417423026970
20. "Graph neural networks for financial fraud detection: a review," *Frontiers of Computer Science*, 2024.
21. PwC (90–95% rule-based AML false positives); Lannoo & Parlour (2021), as cited in AAAI-2022 fraud work (arXiv:2112.07508).
22. Saito & Rehmsmeier (2015), "The precision-recall plot is more informative than the ROC plot…," *PLOS ONE*.
23. Curated index: safe-graph/graph-fraud-detection-papers — https://github.com/safe-graph/graph-fraud-detection-papers

### Additional sources consulted for this plan (verification research, July 2026)

24. IBM Multi-GNN — official AMLworld GNN baselines (GIN, GAT, PNA, R-GCN + edge updates) — https://github.com/IBM/Multi-GNN ; also IBM/Pattern-GNN — https://github.com/IBM/Pattern-GNN
25. Egressy et al. / IBM line, "Multigraph Message Passing with Bi-Directional Multi-Edge Aggregations," arXiv:2412.00241 — bidirectional aggregation on directed financial multigraphs (informs §4.4 directionality handling).
26. Liu et al., "PyGOD: A Python Library for Graph Outlier Detection," arXiv:2204.12095 — https://github.com/pygod-team/pygod (DOMINANT: Ding et al., SDM 2019).
27. PyTorch Geometric explainability framework (`torch_geometric.explain`: Explainer, GNNExplainer, PGExplainer, HeteroExplanation, fidelity metrics) — https://pytorch-geometric.readthedocs.io/en/latest/tutorial/explain.html
28. Ying et al., "GNNExplainer," NeurIPS 2019; Luo et al., "Parameterized Explainer for Graph Neural Network" (PGExplainer), NeurIPS 2020.
29. "When Graph Structure Becomes a Liability: A Critical Re-Evaluation of GNNs for Bitcoin Fraud Detection under Temporal Distribution Shift," arXiv:2604.19514 — strict-inductive protocol; ~39.5-F1 leakage gap; time-step-43 shift. https://arxiv.org/pdf/2604.19514
30. "Do Transaction-Level and Actor-Level AML Queues Agree? An Empirical Evaluation of Granularity Effects on the Elliptic++ Graph," arXiv:2604.23494 — queue-granularity disagreement (informs the alert-unit protocol, §4.5).
31. "Leakage Safe Graph Features for Interpretable Fraud Detection in Temporal Transaction Networks," arXiv:2603.06632 — as-of-time feature discipline.
32. Tide: "A Customisable Dataset Generator for Anti-Money Laundering Research," arXiv:2603.01863; "BlazingAML: High-Throughput AML via Multi-Stage Graph Mining," arXiv:2604.12241 — recent 2026 context for related work and injector benchmarking.
33. Brody, Alon & Yahav, "How Attentive are Graph Attention Networks?" (GATv2), ICLR 2022.
34. Hamilton, Ying & Leskovec, "Inductive Representation Learning on Large Graphs" (GraphSAGE), NeurIPS 2017; Veličković et al., "Graph Attention Networks," ICLR 2018; Schlichtkrull et al., "Modeling Relational Data with GCNs" (R-GCN), ESWC 2018; Corso et al., "Principal Neighbourhood Aggregation" (PNA), NeurIPS 2020; Rossi et al., "Temporal Graph Networks" (TGN), 2020.
35. Lin et al., "Focal Loss for Dense Object Detection," ICCV 2017; Zhao et al., "GraphSMOTE," WSDM 2021 (considered; injection preferred — §4.4).
36. Sigma.js — https://www.sigmajs.org/ ; @react-sigma — https://sim51.github.io/react-sigma/ ; Cosmograph — https://cosmograph.app/ ; Reagraph — https://reagraph.dev/
37. Motion (motion.dev, formerly Framer Motion) — https://motion.dev/ ; GSAP — fully free incl. all plugins since April 2025 (Webflow) — https://gsap.com/
38. Open Contracting Partnership, "How Open is Public Procurement Data in the EU?" (2023) — EU bidder-data coverage context — https://www.open-contracting.org/wp-content/uploads/2023/06/OCP2023-EU-OpenData.pdf
39. Tang et al., "GADBench: Revisiting and Benchmarking Supervised Graph Anomaly Detection," NeurIPS 2023 D&B, arXiv:2306.12251 — tree ensembles + neighborhood aggregation (XGB-Graph) as the mandatory strong simple baseline.
40. "Graph Foundation Models: A Comprehensive Survey," arXiv:2505.15116; "Towards Graph Foundation Models: A Transferability Perspective," arXiv:2503.09363; "Graph Foundation Models: Challenges, Methods, and Open Questions," KDD 2025 — the GFM transferability conversation RQ4 speaks to.
41. "Explain First, Trust Later: LLM-Augmented Explanations for Graph-Based Crypto Anomaly Detection," arXiv:2506.14933 — grounded LLM narration over graph anomaly evidence.
42. "Exploring the In-Context Learning Capabilities of LLMs for Money Laundering Detection in Financial Graphs," arXiv:2507.14785 — LLM red-flag reasoning over serialized k-hop neighborhoods.
43. Regulation (EU) 2024/1689 (EU AI Act) — high-risk obligations (Art. 6 / Annex III) applicable 2 August 2026; explainability, human oversight, auditability requirements for fraud/AML AI — https://artificialintelligenceact.eu/
44. LangGraph (agent orchestration used by the ported Copilot) — https://langchain-ai.github.io/langgraph/ ; sentence-transformers embedding/reranker models (nomic-embed-text-v1.5, bge-reranker-base) — https://sbert.net/

---

## Appendix A — Deviations & Upgrades vs. the Problem Statement

Per instruction, the plan overrides the source document where verification research found something more current or rigorous. All deviations are additive or protocol-strengthening; none removes a stated requirement.

| # | Problem statement says | This plan does | Why |
|---|---|---|---|
| A1 | "GNNExplainer" (standalone) | PyG `torch_geometric.explain` framework: Explainer API + GNNExplainer (MVP) + **PGExplainer** (Phase 2) + HeteroExplanation + built-in fidelity metrics | Current first-class API; PGExplainer amortizes explanation across the whole alert queue; fidelity metrics give RQ3 an objective leg |
| A2 | "GAT" | **GATv2** (plain GAT kept as ablation) | GATv2 fixes GAT's static-attention limitation at equal cost (Brody et al. 2022); attention-interpretability claim carries over |
| A3 | Temporal evaluation unspecified beyond budgets | **Strict-inductive temporal splits** with CI-enforced leakage tests + as-of-time feature discipline | 2026 re-evaluation work shows ~39.5-F1 inflation from train-time exposure to test-period adjacency on Elliptic |
| A4 | No AMLworld baseline named | Reproduce IBM **Multi-GNN** PNA/GIN+EU as external reference points (Phase 2); adopt its bidirectional-aggregation finding for all directed graphs | Official published baseline suite; anchors our numbers to the literature |
| A5 | "graph autoencoders / structural anomaly scoring" (unspecified) | **PyGOD** (DOMINANT + GAE) on homogeneous projections, plus a transparent structural z-score floor | Maintained, PyG-native, reviewable implementation beats bespoke code |
| A6 | "SMOTE-style graph-aware augmentation" | GraphSMOTE demoted to considered-alternative; **synthetic motif injection promoted to primary**, now covering all five motif-table rows in both domain variants | Synthetic minority *nodes* distort topology; injected labeled *subgraphs* match the actual detection target and calibrate against AMLworld's eight ground-truth patterns |
| A7 | "Framer Motion, GSAP, WebGL" (user requirement) | Motion (Framer Motion's current name), GSAP (now fully free incl. premium plugins), **Sigma.js v3 WebGL** workhorse + optional Cosmograph/3D | Library landscape as of 2025–2026 |
| A8 | Mendeley dataset described without authors or caveats | Attributed (Fazekas, Wachs, Tóth & Abdou; v2 Aug 2025); **losing-bid coverage gap identified and designed around** (award-network-first schema, tiered enrichment) | Verified via Mendeley record and the companion paper's own data-quality discussion |
| A9 | Elliptic++ "203,769 nodes … ~2% illicit" (features unstated) | Corrected/expanded: **183 tx features** (166 base, partially interpretable + 17 augmented), exact label counts (4,545 / 42,019), four graph views; actor graph scheduled for Phase-2 heterogeneity; evidence narratives adapted to anonymized features | Verified against the Elliptic++ repository and paper |
| A10 | (no platform guidance) | **Windows-first tooling:** poethepoet cross-platform tasks, PyG without compiled extensions, Docker optional | Primary dev machine is Windows 11; a *nix-only Make/CUDA-source toolchain would stall Week 1 |
| A11 | Subgraph-level evaluation implied but undefined | **Explicit alert-unit protocol:** community alerts with a hit rule (≥1 confirmed member; stricter thresholds as sensitivity), Jaccard-0.5 NMS dedup, member cap, dual node-level reporting | Without this, subgraph Precision@k is gameable/ill-defined; 2026 queue-granularity work (arXiv:2604.23494) shows granularity choices change conclusions |
| A12 | (not in problem statement) LLM narrative idea originated in v2.1 of this plan | **Investigator Copilot** (§4.6): the existing Gen-AI Chatbot codebase ported as the console's conversational layer, superseding the one-shot narrative layer | Working code already implementing the required guardrails (grounding + numeric-sanity gates) on the same database engine (DuckDB); stronger RQ3 and EU-AI-Act support at lower build cost than writing a narrative layer from scratch |

## Appendix B — Traceability Matrix

Every substantive element of `Collusion-Network-Detection.md` mapped to where this plan covers it:

| Problem-statement element (section) | Covered in plan |
|---|---|
| Thesis, motif table, shared-shape insight (§1) | §1.1; §4.4 — injector + motif matcher now implement **all five motif-table rows** literally |
| Plain-language framing & UAE significance (§2, §16) | §1.1, §10.1, R11; ethics line in UI (§5.2) |
| Classification: GNN techniques named (§3) | §4.4 (GraphSAGE/GATv2/R-GCN + anomaly + imbalance + transfer) |
| Mandates: INTERPOL, DOJ/Dubai op, CBUAE Art. 149, Tawazun, OECD (§4) | §12 refs 1–6; product path §4.3 D5 |
| Problem: layering, smurfing, rotation, cover bidding, alert floods, 2% prevalence (§5) | §1.1, §4.3, §4.4 features/injection |
| Missing capability (a)–(d): graph, subgraph detection, budget constraint, explanations (§5) | §3 architecture; §4.4; §4.5 (incl. explicit alert unit); explanation bundle §4.4 |
| Why systems fail — 5 failure modes (§6) | §1.1; baselines B1–B4 operationalize the failing approaches for RQ1 |
| Research gap: tooling/research/open problem; all 6 papers (§7) | §10.4 related work; refs 7–16; Appendix A comparisons |
| RQ1–RQ4 (§8) | §1.3 operationalization table; experiments §4.5, §10.2 |
| Technical approach: adapters, features/screens, detector ensemble, imbalance, explainability, transfer (§9) | §4.2–§4.4 (screens-as-features explicitly fused, with award/bid tiering) |
| Course alignment: GNNs, autoencoders, transfer learning, AI ethics (§9) | §4.4 (GNNs, GAE, transfer), R11 + §5.2 ethics |
| Datasets: Elliptic/Elliptic++, IBM AMLworld, García Rodríguez, Mendeley, OCDS (§10) | §4.3 D1–D5, each with loading/preprocessing/split/role/caveats |
| Evaluation: P@k, AUC-PR, FPR@budget, transfer metrics, explanation quality (§11) | §4.5 (verbatim mapping + budgets k=100 / top-5% + alert-unit protocol) |
| Defensibility arguments (§12) | §10.1, R10 |
| MVP definition items 1–4 (§13) | §1.4 MVP criteria 1–4; §6.1 scope |
| Publication targets: ICAIF, EPJ DS, DGov, IEEE Big Data, KDD workshops (§14) | §10.5 |
| Product potential: RegTech/GovTech, OCDS path (§15) | §4.3 D5, §10.1 |
| Scope boundaries: no guilt determination, no UAE personal/classified data, TRL 3–4, alert export only (§17) | §1.5, §6.2, R11, export button §5.3(4) |
| Scorecard & verification corrections (§18) | Reflected in refs 1, 5, 9 phrasing; confidence framing §10.1 |
| All reference links (§19) | §12 refs 1–23 (complete), plus new refs 24–44 |

## Appendix C — v1.0 → v2.0 Audit Changelog

Full re-audit conducted against the problem statement, the datasets' primary sources, and the plan's own internal consistency. **Errors fixed:**

1. **Elliptic++ feature count corrected:** 183 transaction features (166 base + 17 augmented), not 166; exact label counts added (4,545 illicit / 42,019 licit). *(§4.3 D1, A9)*
2. **LOMO/LOMO typo** in the experiment list → LOMO/LOCO. *(§10.2)*
3. **Windows incompatibility:** v1's Makefile-centric workflow replaced with cross-platform poethepoet tasks; PyG pinned without compiled extensions; Docker made optional. *(§4.1, §8, A10)*
4. **Motion rename date imprecision** removed (now referenced by its current identity, motion.dev). *(§5.1)*

**Gaps filled (each was silently load-bearing):**

5. **Alert-unit protocol** — subgraph Precision@k was undefined without a hit rule, overlap deduplication (Jaccard-0.5 NMS), and a member cap; all three added, with Phase-2 sensitivity analyses and dual node-level reporting motivated by 2026 queue-granularity findings. *(§4.5, A11)*
6. **Losing-bidder data gap** in EU procurement (verified against the Mendeley companion paper): award-network-first schema rule, tiered co-bid enrichment, use of the dataset's precomputed screens, OCDS publisher-selection criterion, new risk R13, Week-1 coverage-mapping task. *(§4.2, §4.3 D4/D5, §11)*
7. **Elliptic anonymized-feature caveat:** explanation evidence now adapts per dataset (structural/temporal evidence on Elliptic; full amount narratives on AMLworld/procurement); honestly surfaced in UI and limitations. *(§4.3 D1, §4.4)*
8. **Unknown-label policy** for Elliptic's ~77% unlabeled mass made explicit (loss on labeled only; full message-passing participation; unsupervised scoring). *(§4.3 D1)*
9. **Injector coverage completed:** v1 covered three of the five motif-table rows; added hidden-common-control (linked_to cliques) and coordinated-clustering/pass-through generators in both domain variants, with a coverage table. *(§4.4)*
10. **Directionality handling** specified (bidirectional message passing with direction flags; forward/reverse relations in R-GCN), grounded in the Multi-GNN line's bidirectional-aggregation evidence (arXiv:2412.00241). *(§4.4)*
11. **PyGOD homogeneous-projection constraint** stated, plus an explicit evaluation policy for the unsupervised arm. *(§4.1, §4.4)*
12. **Score calibration** (isotonic, per ensemble member) added so fused scores and UI risk values are meaningful. *(§4.4)*
13. **Explanation scope honesty:** bundles now label which evidence comes from the learned explainer vs. motif rules vs. screens — no implication that one method explains the fused score. *(§4.4)*
14. **Dataset licensing:** licenses recorded in committed manifests; repo ships download scripts, never raw data; new risk R15. *(§4.3, §8, §11)*
15. **Model card + dataset datasheets** added to Phase-2 deliverables and repo docs. *(§1.4, §7, §8)*
16. **Practitioner-recruitment fallback** (R14) and ethics-review lead time moved earlier (Week 9–10). *(§10.3, §11)*
17. **TGN/TGAT temporal-GNN stretch** added to Phase 2 (the problem statement stresses temporal graphs; snapshots + encodings may be beatable). *(§2, §4.4)*
18. **Milestone table, compute-budget estimates, buffer/cut-order policy** added to the roadmap. *(§4.1, §7)*
19. **Frontend completeness:** per-domain dataset selector, designed loading/error/empty states, chart SVG/PNG export (figures pipeline), precomputed deterministic layouts. *(§5.1, §5.3)*
20. **New 2026 references** integrated (queue granularity arXiv:2604.23494; leakage-safe features arXiv:2603.06632; Tide arXiv:2603.01863; BlazingAML arXiv:2604.12241; bidirectional aggregation arXiv:2412.00241; TGN). *(§10.4, §12)*

### v2.0 → v2.1 (final pre-development pass: July-2026 frontier positioning + collaboration workflow)

21. **EU AI Act alignment added** — high-risk obligations (fraud/AML explicitly in scope) become enforceable 2 August 2026; the paper gains a regulatory-alignment subsection and the strongest available freshness hook. *(§10.4, §10.6, ref 43)*
22. **Baseline B3 upgraded to GADBench's XGB-Graph protocol** — the benchmark community's strongest simple baseline (tree ensembles + neighborhood aggregation often beat specialized GNNs); pre-empts the most predictable review objection. *(§4.5, §10.6, ref 39)*
23. **RQ4 reframed in graph-foundation-model vocabulary** — positions the cross-domain transfer study inside the field's hottest open conversation (GFM transferability), win or lose. *(§10.4, §10.6, ref 40)*
24. **Optional strictly grounded LLM narrative layer** added to Phase 2 (verbalizes explanation bundles; schema-validated against evidence; template fallback; measured via a practitioner-study arm). *(§2 P2.1/P2.4, §4.4, §10.6, refs 41–42)*
25. **Collaboration & handoff workflow** added: trunk-based branching, conventional commits, `PROGRESS.md` ledger as a required pre-push artifact, and a reusable stage-agnostic `handoff-prompt.md` for multi-developer/AI-session continuity. *(§7, §8)*

### v2.1 → v3.0 (Gen-AI Chatbot integration)

26. **Investigator Copilot** (§4.6): the existing `Gen-AI Chatbot/` codebase (LangGraph 15-agent pipeline: router, intent classifier, clarification, planner, SQL agent, RAG agent, hybrid executor, synthesiser, critic, cross-validator, arbiter, completeness checker, read-back, finaliser) is ported as the console's conversational layer. The fit is structural, not cosmetic: its SQL agent already runs on DuckDB (our artifact-store engine), its critic already enforces the grounding and numeric-sanity guardrails our narrative layer required, and its clarification/read-back interrupts implement the EU AI Act human-oversight pattern. *(§2 P2.2, §3.2, §4.6, §5.3 view 7, §7 Week 11, §8, §9.2)*
27. **LLM narrative layer superseded** by the Copilot; guardrail principles carried over verbatim. *(§4.4, A12)*
28. **Cleanup manifest** for the chatbot folder (§4.6): TechNova datasets (15 xlsx + 15 PDFs + zip + 7.9 MB DuckDB binary), stale query results/logs, and 13 one-off scripts deleted; agent/retrieval/tools/frontend code archived to `reference/genai-chatbot/` as the port source; TechNova domain assets (schema.yaml, facts*.yaml, goldens.json, POLICY_LEXICON, prompt personas) scheduled for CollusionGraph replacements.
29. **Security finding:** a live OpenAI API key sits in the chatbot's `.env` — rotation scheduled as a Week-1 task, gitleaks pre-commit hook added, new risk R18. *(§7 Week 1 step 4, §11)*
30. **Infrastructure simplification** verified against the code: Qdrant replaced by an embedded dense store (corpus ~50–300 chunks, BM25 already in-memory), Redis dropped (never wired in — MemorySaver is used), Langfuse/Postgres optional-off — the Copilot adds zero required docker services. The SSE CRLF parser fix from `FIX_FRONTEND.md` is mandatory in the ported client. *(§4.6)*
31. **New agents/changes:** `alert_tools` (read-only artifact-store tools), red-flag lexicon replacing the policy lexicon, guilt-language guard in the finaliser, SELECT-only SQL allowlist, fast-path config for latency/cost, per-agent model configurability. *(§4.6)*
32. **Roadmap restretch:** Phase 2 is now ~8–9 weeks; new Milestone MC (Week 11, Copilot goldens gate); M6→wk 13, M7→wk 14, M8→wk 17; new risks R16–R18. *(§2, §7, §11)*
33. **Handoff workflow split into two prompts** (master laptop as integrator; collaborator laptops as continuators) with a machine-sync convention for what git does not carry — see `handoff-prompt.md`. *(§7)*

---

*End of implementation plan v3.0. Development may begin; §7 governs the sequence, §7's collaboration workflow + `handoff-prompt.md` govern how work moves between machines.*
