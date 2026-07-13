# Detecting Collusion Networks
## An Explainable, Imbalance-Robust Graph-Learning Framework for Illicit-Finance and Bid-Rigging Integrity Screening

**Working name:** CollusionGraph — a unified integrity-analytics capability.

**Thesis.** Money laundering in a bank ledger and bid rigging in a procurement ledger are the same crime wearing two costumes: a small group of parties that should be acting independently instead coordinates, and the proof of that coordination lives in the *shape of the network*, never in any single record. This project builds one graph-anomaly detection system that learns that shared shape, flags the suspicious subgraph under a strict false-positive budget, explains each flag in the investigator's own red-flag vocabulary, and shows that a single learned notion of "collusion structure" transfers across both typologies and across markets — despite the fact that confirmed cases are vanishingly rare in either domain. The contribution is an *imbalance-robust, explainable, transfer-capable graph collusion detector* validated on both financial-transaction and public-procurement networks with one shared stack.

---

## 1. The Core Insight: Two Ledgers, One Structure

Start with the observation that makes this a single project rather than two.

A single wire transfer of AED 40,000 is unremarkable. Twelve accounts passing the same funds among themselves in a circle within 72 hours is money laundering. A single bid on a government tender is procedurally clean — the required bids were received, an evaluation was run, a winner was declared. Five firms that repeatedly bid on the same tenders, quietly rotate the winner among themselves, submit implausibly clustered losing prices, and turn out to share directors and registered addresses are a cartel.

In both cases the individual record is innocent and the network is guilty. In both cases the parties deliberately keep every single record below the thresholds that record-level rules check, so the illegality only becomes visible one level up — in the *topology* of money flows or of co-bidding. And in both cases the defenders are drowning: rule-based transaction monitoring generates alert floods that are overwhelmingly false, and procurement auditors check tenders one at a time, by hand, on a tiny sample, usually discovering cartels only after the fact through complaints or leniency applications.

The crimes even share a motif vocabulary. Once you draw the graph, the two domains stop looking like different problems:

| Collusion mechanism | Financial-crime manifestation | Procurement manifestation | Shared graph signature |
|---|---|---|---|
| Circular coordination | Laundering cycle — funds return to origin through intermediaries, fabricating commercial activity | Bid rotation — the win is passed around the cartel so each firm's individual win rate looks plausible | Directed cycle / recurring closed walk |
| Convergent funneling | Smurfing / structuring — many small deposits converge on one target, each below reporting thresholds | Cover (complementary) bidding — losing bids cluster around one pre-agreed winner to simulate competition | High in-degree star / fan-in motif |
| Divergent dispersal | Fan-out / layering — a lump sum is scattered across dozens of accounts | Market allocation — cartel members carve up regions, categories, or customers | High out-degree star / partition motif |
| Hidden common control | Shell-company chains, shared beneficial owners, common registration agents | "Rival" firms sharing directors, addresses, phone numbers, or bid-preparation fingerprints | Dense co-ownership / shared-attribute subgraph |
| Coordinated clustering | Pass-through accounts with near-zero retention and abnormally short holding times | Clustered losing prices, sequential submission timestamps, prices derived from a common formula | Tight community / near-clique with abnormal edge attributes |

This is the conceptual bridge the whole project stands on. Both problems reduce to one machine-learning task:

> **Anomalous-subgraph detection with explanations, on heterogeneous temporal graphs, under a low-false-positive (fixed alert budget) constraint, in a label-scarce environment.**

The finance and procurement domains are not two projects — they are two *evaluation surfaces* for one system. Graph construction, feature engineering with temporal encodings, a detector combining supervised graph neural networks (where labels exist) with unsupervised anomaly scoring (where they don't), a subgraph-explanation layer that turns model output into investigator-readable evidence, and an evaluation protocol built on precision-at-budget rather than accuracy — roughly 70% of that stack is identical across the two. Only the data adapters and the domain red-flag vocabularies differ. Solving it once yields a dual-use integrity capability that speaks to two UAE national priorities at the same time.

The academic literature backs this framing directly. Graph anomaly detection is now a mature field with a unifying taxonomy spanning node-, edge-, and subgraph-level anomalies across exactly these application areas (Ma et al., *IEEE TKDE*, 2023), and the specific reduction of both money-laundering and cartel detection to graph problems is established in the AML GNN literature (e.g., Motie & Raahemi, *Expert Systems with Applications*, 2024) and the procurement-collusion GNN literature (Gomes et al., 2024; Imhof, Viklund & Huber, 2025).

---

## 2. Plain-Language Summary

Criminals hide two very different crimes in the same way: by spreading the activity across a group so that no single piece looks suspicious. Money launderers move dirty money through chains and loops of accounts — including terror financing and sanctions evasion — so its origin is impossible to trace from any one transaction. Cartels secretly agree to rig public contracts by taking turns winning and submitting fake losing bids, so every individual tender looks like a fair competition. Banks and auditors mostly rely on systems that look at one transaction, or one tender, at a time, which is precisely the level at which both crimes are invisible.

This project builds a single "graph AI" that looks at the whole picture instead. It turns bank activity into a network of accounts and money flows, and procurement activity into a network of firms, tenders, and ownership links, and then learns to spot the *shapes* that coordination leaves behind — the laundering ring, the rotating cartel, the funnel of shell companies, the clique of "competitors" that share an office. Crucially, for every case it flags, it points to the exact subgraph and explains *why* — this ring of accounts, this rotation sequence, this shared director — in the same language investigators and auditors already use for red flags. It finds networks, not single transactions, and it gives compliance analysts and auditors a screening tool that ranks the cases most worth a human's time. It matters for national security, for the UAE's standing as a clean financial hub, and for the integrity and value-for-money of public and defense procurement, where eliminating bid rigging can cut prices by a fifth or more.

---

## 3. Classification (Merged)

- **Bucket:** Defense / national-integrity analytics.
- **Domain:** Financial-crime and procurement integrity intelligence (dual-domain).
- **Sub-domain:** Collusion and illicit-coordination network analysis — spanning illicit-finance network detection and public-procurement cartel detection.
- **Technique:** Graph neural networks (GraphSAGE / GAT / R-GCN) with graph anomaly detection, subgraph-level explainability, class-imbalance handling, and cross-domain / cross-market transfer learning.

---

## 4. Source and Mandate

The problem is anchored to current, verified authority in both domains. Together these establish that a networked, explainable integrity-screening capability is a live national priority — not a hypothetical one.

**Financial-crime mandate.**

- **INTERPOL Global Financial Fraud Threat Assessment (Second Edition), released 16 March 2026** at the Global Fraud Summit (co-organised with UNODC). It rates the global fraud risk as **"high"** and warns, in the Secretary General's foreword, that AI, cheap digital tools, and cross-border criminal collaboration are producing an **"industrialization of fraud."** The report cites one estimate putting global fraud losses in 2025 at roughly **USD 442 billion** (a cited estimate, not a measured total) and assesses AI-enabled fraud as materially more profitable than traditional methods.
- **The April 2026 FBI–China–Dubai Police operation.** Announced by the US Department of Justice on **29 April 2026**, this joint operation led by Dubai Police with the FBI and China's Ministry of Public Security dismantled at least nine scam centres, arrested 276 individuals, and restrained **more than USD 701 million in cryptocurrency** (reported by *The Next Web* and others in 2026). It is a concrete, UAE-centred demonstration of exactly the multi-jurisdiction, network-structured illicit-finance activity this project targets.
- **CBUAE Federal Decree-Law No. 6 of 2025**, issued 8 September 2025 and **effective 16 September 2025**, whose **Article 149** requires licensed financial institutions to implement robust fraud prevention and detection mechanisms and to cooperate with the Central Bank on fraud data and patterns (with a compliance runway to 16 September 2026). This is a standing legal mandate for advanced fraud detection in the UAE banking system.

**Procurement-integrity mandate.**

- **Tawazun Council** — the UAE's defense and security acquisitions authority for the UAE Armed Forces and Abu Dhabi Police. In February 2021 at IDEX, a resolution appointed Tawazun to manage the procurements and contracts of these bodies, with the stated intent to adopt **"international best practice in contract and procurement management"** (Ministry of Defence Undersecretary Matar Al Dhaheri, via *The National*) and to **"synergize the supply chain"** into a homogeneous system rather than scattered procurement (CEO Tareq Al Hosani, via *Janes*), reported across *The National*, *Khaleej Times*, and *Janes*. Tawazun's supplier portal states its values of **transparency, efficiency, and fairness**, and it remains the standing acquisitions authority through 2025–2026.
- **OECD Guidelines for Fighting Bid Rigging in Public Procurement (2025 Update)** (OECD Publishing, Paris; declassified 19 June 2025; DOI 10.1787/cbe05a56-en). The OECD states that member countries spend **approximately 13% of GDP** on public procurement (some earlier secondary sources cite ~12%), and that **"the elimination of bid rigging could help reduce procurement prices by 20% or more."** Procurement integrity is a named defense-acquisition priority.

Both mandates point at the same missing capability: a system that reasons over *networks* of activity, screens at portfolio scale, keeps false positives inside investigator capacity, and explains itself.

---

## 5. The Problem

**Regulatory, supervisory, and audit institutions lack an analytical capability that can (a) represent financial and procurement activity as networks, (b) detect anomalous or collusive structures within those networks with a low false-positive rate, and (c) explain each detection in terms a human investigator can verify and act upon.** The same gap appears in two domains.

On the financial side, money laundering, terror financing, and sanctions evasion rely on *layering* — moving funds through chains of accounts, shell companies, money mules, and jurisdictions to obscure their criminal origin. The characteristic structures are the ones in the motif table above: smurfing fan-ins below reporting thresholds, fan-out dispersal, laundering cycles, pass-through accounts, and shell-company chains linked by common agents or owners. Rule-based transaction monitoring flags individual transactions against static thresholds ("cash deposit above X," "transfer to a high-risk jurisdiction"), and criminals, knowing the thresholds, structure around them. Tabular machine-learning models improve on rules but still classify each transaction or account in isolation using local features, so neither approach models the joint structure of a laundering network — the exact layer at which the crime is defined. The consequence is a double failure: alert floods on innocent behaviour, and silence on sophisticated networks. The alert floods are severe — industry benchmarks (e.g., PwC) put the false-positive share of rule-based AML alerts at 90–95%, and academic work reports comparable rates (Lannoo & Parlour, 2021, as cited in AAAI-2022 fraud-detection work). And the crime is rare in the data: in the standard public benchmark fewer than **2% of transactions are illicit**, with additional label noise, so raw accuracy is a meaningless metric.

On the procurement side, the crime is bid rigging: firms that should compete instead coordinate through bid rotation, cover (complementary) bidding, bid suppression, market allocation, and structural concealment (shared owners, directors, addresses, phone numbers, or bid-preparation fingerprints such as identical formatting and sequential timestamps). Each individual tender in a rigged series is procedurally clean, so manual red-flag checklists — including the OECD's — get applied tender-by-tender, by hand, on a small sample, and cartels are typically discovered only after the fact, through complaints, leniency applications, or whistleblowers. There is no systematic *screening* capability that examines a whole procurement portfolio and ranks tenders and firm-clusters by collusion risk. Statistical screens (coefficient of variation, price spread, kurtosis) miss network structure, and the models that do exist transfer poorly across countries and markets. Proven cartels are, again, rare relative to the volume of clean tenders — the same extreme-imbalance, label-scarce regime as the financial side.

**Why it matters.** On the financial side, network-level blind spots directly weaken sanctions enforcement and counter-terror finance, and every false positive burns scarce investigator capacity that could be spent on genuine cases. On the procurement side, with documented bid-rigging premiums of 20% or more, the addressable waste in any large national procurement portfolio runs into the hundreds of millions of dirhams annually — and in the defense context, procurement integrity is additionally a matter of supply-chain trust and national-security assurance. Both are UAE national priorities, and both are currently served by systems that cannot, by construction, see the crime.

**What is missing (common to both).** A detection layer that:
1. constructs a heterogeneous, temporal graph — of accounts, entities, and transactions on one side; of firms, tenders, bids, and ownership/registration links on the other;
2. identifies suspicious *subgraphs and communities* (not merely suspicious accounts or single bids) using learned structural patterns combined with unsupervised anomaly signals;
3. operates under an explicit **low-false-positive constraint**, evaluated at fixed alert budgets (e.g., precision within the top 100 alerts, or within the top 5% of the tender queue), because investigator and auditor capacity — not model output — is the binding resource;
4. attaches to every flag a **human-verifiable explanation**: the subgraph involved, the structural motif detected, the amounts and time window or the rotation sequence and price anomaly, and the specific red-flag indicator it maps to. An alert that cannot be explained cannot be filed as a suspicious-transaction report, cannot survive an audit challenge, and will not be trusted by analysts.

---

## 6. Why Current Systems Fail

The failure mode is identical across the two domains, which is a large part of why one system can serve both:

- **Record-level blindness.** Rule engines and tabular models score one transaction, account, or tender at a time. Collusion is a network property; scoring records in isolation cannot detect it by construction.
- **Threshold gaming.** Sophisticated actors deliberately keep every individual record below the thresholds the rules check, so the more static the rules, the more reliably they are evaded.
- **False-positive overload.** Record-level rules over-fire on innocent behaviour — hence the 90%+ AML false-positive rates and the tender-by-tender manual review that never scales to a portfolio.
- **Weak or absent explainability.** Proprietary AML suites and procurement-analytics vendors produce scores without verifiable, subgraph-level rationales, which is fatal in domains where an unexplained flag has no legal or operational value.
- **Poor generalization.** Models trained on one market or typology transfer badly to unseen ones, so a detector proven in one context does not carry over — a problem the cartel literature documents explicitly (cross-country accuracy drops) and the AML literature echoes (instability across typologies and under imbalance).

---

## 7. The Research Gap (Merged)

The competitive landscape divides into existing tooling, current research, and the open problem — described here across both domains together because the gap is shared.

**Existing tooling.** On the financial side: the Elliptic dataset and analytics ecosystem, Chainalysis, and bank AML suites — largely proprietary, with weak explainability and record- or account-level orientation. On the procurement side: procurement-analytics vendors and competition-authority statistical screens — with limited machine learning and no learned network modelling. Neither side offers an open, explainable, network-level, transfer-capable detector.

**Current research — financial.** Recent graph-based AML work is real and strong but leaves the target open:
- **LineMVGNN** (Poon et al., *AI* / MDPI, vol. 6 no. 4, art. 69, 3 April 2025) — line-graph-assisted multi-view GNN with two-way message passing, evaluated on Ethereum-phishing and industrial payment data; advances directed-graph AML but does not solve explainable, imbalance-robust detection across typologies.
- **Explainable GNN on the Elliptic dataset** (Lawal, Okolie & Obunadike, *IJCNC*, 17 December 2025) — uses GNNExplainer for subgraph attribution but explicitly documents that performance **remains unstable under class imbalance even with class weighting and focal loss**. This is the motivating evidence that headline accuracy is deceptive at 2% prevalence.
- **Wavelet-temporal graph transformer** ("ChronoWave-GNN," Lin et al., *Scientific Reports* 16:1548, version of record **13 January 2026**, DOI 10.1038/s41598-025-23901-3) — reports ~0.98 accuracy/F1 on Elliptic, but its own ablation concedes the wavelet features add only ~0.01 and are "not strictly indispensable," so the headline should be cited cautiously.

**Current research — procurement.** The cartel-detection literature converges on the same open questions:
- **Imhof, Viklund & Huber, "Catching Bid-rigging Cartels with Graph Attention Neural Networks"** (arXiv 2507.12369, July 2025) — GATs over tender-firm graphs across 13 markets in 7 countries; a best configuration reaches ~91% cross-market prediction and maintains **~84% average accuracy across 12 markets**, beating traditional ensemble ML — but with a clear **cross-country performance drop** that leaves transfer open.
- **Gomes et al., "Collusion Detection with Graph Neural Networks"** (arXiv 2410.07091, October 2024) — Relational GCNs across Japan, the US, two Swiss regions, Italy, and Brazil, with a zero-shot / transfer-learning phase that explicitly probes **out-of-distribution generalization** to markets with no training data; GNNs beat feedforward baselines but OOD degradation persists.
- **EPJ Data Science systematic mapping study** ("Detection of fraud in public procurement using data-driven methods," 2025) — screens 6,000+ works to 93 and names the **real-world-validation gap** and the over-reliance on single-sector (construction/infrastructure) validation.

**The merged open problem.** Neither domain has a detector that is simultaneously *explainable at the subgraph level*, *robust under extreme class imbalance*, and *transfer-capable across markets and typologies*. Each domain's 2025–2026 literature names some subset of these as open, but no work treats them as one problem and, critically, **no work asks whether a shared notion of "collusion structure" learned in one domain informs the other** — cross-domain transfer between illicit-finance networks and procurement cartels is unexplored territory.

**Is it solved?** No.

**Contribution.** A single imbalance-robust, explainable, transfer-capable graph collusion detector, demonstrated on both illicit-finance and bid-rigging networks with one shared stack, plus the first empirical study of whether collusion-structure representations transfer across the two domains.

**Confidence:** Medium–High.

---

## 8. Research Questions

- **RQ1.** Can graph neural networks combined with unsupervised graph anomaly detection identify illicit-finance network structures and bid-rigging cartel structures with materially higher precision at fixed alert budgets than rule-based and tabular machine-learning baselines?
- **RQ2.** Can collusion fingerprints learned from ground-truth-labeled cases — international cartel prosecutions and labeled illicit-finance graphs — augmented with synthetically injected patterns, transfer to unseen markets and unseen typologies as an effective risk-screening tool at a controlled flag rate?
- **RQ3.** Can subgraph-level explanation methods produce alert rationales that human practitioners (compliance analysts, procurement auditors) judge to be verifiable, useful, and aligned with the established red-flag frameworks they already use?
- **RQ4.** To what extent can a single shared technical stack — graph construction, detection, explanation, and evaluation — serve both financial-crime and procurement-collusion detection, and does a representation of "collusion structure" learned in one domain provide any usable signal in the other?

---

## 9. Technical Approach (Merged Methodology)

One pipeline, two data adapters. The stack is deliberately shared so that the same components are exercised on both the financial-transaction graph and the procurement graph.

**Graph construction.** A heterogeneous, temporal graph builder with two adapters. The financial adapter builds accounts/entities as nodes and transactions as directed, timestamped, attributed edges (amount, currency, time), with entity-linkage edges for shared owners/agents/addresses. The procurement adapter builds firms, tenders, bids, and lots as nodes with co-bidding, awarding, and ownership/registration edges. Both produce the same internal graph schema so downstream components are domain-agnostic.

**Feature engineering.** Node and edge features with temporal encodings; for the procurement arm, classic collusion screens are computed as features — coefficient of variation of bids, price spread, kurtosis, bid-difference and relative-distance statistics — so the network model and the statistical-screen tradition are fused rather than competing. Analogous local statistical features (holding time, retention ratio, in/out-degree burstiness) are computed on the financial side.

**Detection layer.** A supervised GNN backbone family — **GraphSAGE**, **GAT** (attention weights double as an interpretability signal), and **R-GCN** for heterogeneous/relational edges — trained where labels exist, combined with **line-graph views** (following LineMVGNN) for directed money-flow modelling, and paired with **unsupervised graph anomaly detection** (graph autoencoders / structural anomaly scoring) for the label-scarce regions. The two are ensembled so that the system produces a ranked risk score for subgraphs and communities, not just for individual nodes.

**Class-imbalance handling.** Focal loss and resampling (over/under-sampling, SMOTE-style graph-aware augmentation), plus synthetic pattern injection with known ground truth — deliberately planting laundering motifs and cartel motifs into unlabeled graphs to create controllable training signal. This directly targets the instability-under-imbalance failure documented in the 2025 Elliptic explainability work.

**Explainability layer.** **GNNExplainer**-style subgraph attribution (complemented by GAT attention) that returns, for every flag, the minimal responsible subgraph, the detected motif, the amounts/time window or rotation sequence/price anomaly, and a mapping to the domain's existing red-flag vocabulary. An unexplained flag is treated as a non-deliverable.

**Transfer / domain adaptation.** Domain-adaptation techniques for cross-market transfer (train on some markets, test on others) and a controlled cross-domain experiment (does a representation trained on cartel graphs help on illicit-finance graphs, and vice versa). This is where the merged framing pays off scientifically.

**Course alignment.** GNNs, autoencoders, transfer learning, and AI ethics — all within the Deep Learning capstone scope, with no exotic hardware required.

---

## 10. Datasets

Every dataset from both original problem statements is retained; the two labeled anchors (Elliptic++ and the Mendeley cartel dataset) form the shared benchmark spine, with the synthetic and unlabeled sets as scale and fallback extensions. All are public and near-zero-cost.

**Financial-crime graphs.**
- **Elliptic / Elliptic++** — the standard public Bitcoin-transaction graph for illicit-finance detection. Elliptic++ contains **203,769 transaction nodes and 234,355 directed edges across 49 time steps** (~2% illicit, ~21% licit, remainder unknown), plus ~822k wallet addresses. Base Elliptic is available through PyTorch Geometric (`EllipticBitcoinDataset`); Elliptic++ is on GitHub (git-disl/EllipticPlusPlus, arXiv 2306.06108). This is the primary real-world financial anchor.
- **IBM AMLworld** — six public synthetic AML transaction datasets (HI/LI × small/medium/large, up to ~180M transactions) with complete ground-truth labels modelling eight laundering patterns (fan-in/out, cycle, scatter-gather, etc.); Altman et al., NeurIPS 2023, arXiv 2306.16424; on Kaggle (ealtman2019/ibm-transactions-for-anti-money-laundering-aml). Used for scale, controllable imbalance, and synthetic-pattern experiments.

**Procurement graphs.**
- **García Rodríguez et al. (2022) multi-country collusion dataset** — collusive-tender data from **Brazil, Italy, Japan, Switzerland, and the United States**, published as the supplement to "Collusion detection in public procurement auctions with machine learning algorithms," *Automation in Construction* 133:104047 (ScienceDirect S0926580521004982, item #ec0010). A widely reused cross-country benchmark.
- **Mendeley EU cartel dataset** — **73 confirmed cartel cases, 15,000+ contracts** awarded to cartel members, across **7 countries (Bulgaria, France, Hungary, Latvia, Portugal, Spain, Sweden), 2004–2021**, harmonized from opentender.eu; Mendeley Data f3y4nrn3s6/2 (paper in the *International Journal of Industrial Organization*, S0167718725000943). The primary labeled procurement anchor.
- **OCDS (Open Contracting Data Standard) bulk data** — free, non-proprietary, actively maintained procurement data adopted by 50+ governments, downloadable via the Data Registry (data.open-contracting.org). The unlabeled fallback for synthetic-injection and unsupervised experiments, and the path to future UAE-portfolio deployment.

Prototype: yes, on all of the above, at near-zero cost, with no access to classified or personal UAE data required.

---

## 11. Evaluation Protocol

Because investigator and auditor time is the binding resource, evaluation is conducted at **fixed alert budgets**, never at global accuracy:
- **Precision@k** — precision within the top-k alerts (e.g., top 100 transactions/subgraphs, or the top 5% of the tender queue).
- **AUC-PR** — area under the precision–recall curve, the appropriate summary under extreme imbalance (Saito & Rehmsmeier).
- **False-positive rate at operational thresholds**, reported at the alert budgets a real compliance or audit team would actually work.
- **Transfer metrics** — held-out-market and held-out-domain Precision@k, to quantify cross-market and cross-domain generalization directly.
- **Explanation quality** — practitioner-judged verifiability and alignment with established red-flag frameworks (RQ3).

---

## 12. Why This Is Defensible Through Submission

The combined project is stable to build on for the full academic term, on both arms, for the same reasons the two arms were individually defensible.

- **The benchmarks are the standing standard and will not move.** Elliptic / Elliptic++ and IBM AMLworld remain the reference public datasets for financial-crime graph ML; García Rodríguez (2022) and the Mendeley EU cartel dataset remain the reused cross-country benchmarks for procurement collusion. None is at risk of deprecation within the project window.
- **The open problem is named as open in the current literature — on both sides.** The 2025 explainable-Elliptic paper names instability under imbalance; the 2025 cartel-GAT and R-GCN papers name cross-market/OOD transfer; the 2025 EPJ mapping study names the real-world-validation gap. Parallel work is advancing the field but explicitly leaving imbalance + explainability + transfer open, so the contribution does not evaporate mid-term.
- **The framing is conventional integrity analytics, not a moving target.** The financial arm is deliberately positioned as conventional/blockchain-forensics financial intelligence — not crypto trading — and the procurement arm as competition/audit screening. Both are stable, policy-backed problem spaces.
- **The merge itself is the moat.** Even if one arm's specific result is matched by concurrent work, the cross-domain transfer study and the single-shared-stack demonstration are novel and not addressed elsewhere.

---

## 13. MVP Definition (Merged)

A single, demonstrable prototype exercising the shared pipeline on both domains:

1. Train the GNN + anomaly stack on **Elliptic++** with imbalance handling, and flag an illicit money-laundering subgraph with a GNNExplainer rationale (motif, amounts, time window, red-flag mapping).
2. Train the same stack on the **García Rodríguez / Mendeley** cartel data, test **cross-country transfer**, and flag a cartel subgraph with screen-based explanations (rotation sequence, co-bidding clique, price anomaly, shared-ownership link).
3. Run one **cross-domain transfer probe** — does a collusion-structure representation trained on one domain give usable signal on the other — reported honestly, even if the answer is partial.
4. Surface all of the above in a single **screening dashboard** that ranks cases for a human investigator at a fixed alert budget, with the explanation attached to each flag.

---

## 14. Publication Targets (Merged)

The venues from both arms are reconciled around the merged contribution:
- **ACM ICAIF** (International Conference on AI in Finance) — best fit for the financial arm and for a merged paper led by the AML result.
- **EPJ Data Science** — best fit if the paper leads with the procurement / computational-social-science angle.
- **ACM DGov** (Digital Government: Research and Practice) — strong fit for the governance/audit framing of the procurement arm.
- **IEEE Big Data** — scale-oriented alternative for the combined transaction-graph work.
- **KDD workshops** (anomaly detection / graph mining / fraud) — the natural home for a *merged* paper whose novelty is the shared cross-domain graph-anomaly framework.

Demonstrations: a flagged laundering subgraph with explanation, and a flagged cartel subgraph with screen explanations, presented from one system.

---

## 15. Future / Product Potential (Merged)

One platform, two go-to-market surfaces. The shared stack becomes a **unified integrity-analytics product** with a RegTech face (bank/FIU AML compliance screening) and a GovTech face (procurement/defense-acquisition audit screening) — a single "collusion-network detection" engine sold into two markets. For the UAE specifically, it maps onto CBUAE-mandated fraud detection on the financial side and Tawazun-mandated procurement integrity on the defense-acquisition side, with a documented path to piloting on institutions' own data (via OCDS-standard procurement feeds and bank transaction graphs) without ever touching classified or personal data during the research phase.

---

## 16. Significance in the UAE Context

- **Financial-hub integrity.** The UAE exited the FATF grey list on **23 February 2024** after a concerted national AML/CFT program (specialist financial-crimes court, an Executive Office to Combat Money Laundering and Terrorist Financing, strengthened beneficial-ownership transparency). Sustaining advanced, network-level anti-financial-crime analytics beyond minimum compliance is a stated national priority and a reputational asset for the banking sector, the Central Bank, and the UAE Financial Intelligence Unit — reinforced by CBUAE Decree-Law No. 6 of 2025.
- **Terror-financing and sanctions pressure.** Regional conflict dynamics raise the volume and sophistication of illicit-finance activity transiting Gulf systems, increasing the cost of record-level blind spots.
- **Procurement integrity as defense policy.** Integrity and value-for-money in acquisition are explicit priorities of the UAE's defense-enablement agenda, and Tawazun Council holds a standing mandate for exactly this screening capability; the 20%+ bid-rigging premium translates to hundreds of millions of dirhams of addressable waste annually.
- **Data feasibility without classification barriers.** The whole project runs on public and synthetic data — labeled cryptocurrency transaction graphs, large synthetic AML corpora, open international procurement datasets with prosecuted-cartel ground truth — requiring no classified or personal UAE data while remaining directly transferable to UAE institutions that later choose to deploy it.

---

## 17. Scope Boundaries

**In scope:** graph construction from transactional and procurement records; supervised and unsupervised graph-based detection; temporal modelling; subgraph explainability; fixed-budget evaluation; cross-market and cross-domain transfer study; demonstration on public and synthetic datasets; a screening dashboard for human investigators.

**Out of scope:** any determination of legal guilt; processing of personal or classified UAE data; real-time production deployment inside a bank or ministry (target maturity is a validated prototype, TRL 3–4, with a documented path to piloting); investigation case management beyond alert export. The system is a **risk-screening and triage instrument that ranks cases for human investigation — not an accusation engine, and it produces no determination of guilt.** This constraint governs the ethics, the legal positioning, and the language of every output.

---

## 18. Project Scorecard and Flags (Reconciled)

Scores reconciled across both arms (the merge lifts novelty via the cross-domain contribution; source and freshness stay maximal; feasibility is unchanged since the stack is shared):

| Criterion | Financial arm | Procurement arm | Merged |
|---|---|---|---|
| Publication ceiling | 4 | 4 | 4 |
| Presentation / demo | 4.5 | 4 | 4.5 |
| Novelty | 3.5 | 4 | **4.5** (cross-domain transfer is new) |
| Source strength | 5 | 4.5 | 5 |
| Technical depth | 4 | 4 | 4.5 |
| Dataset readiness | 5 | 4.5 | 5 |
| Freshness | 5 | 4.5 | 5 |
| Feasibility | 4 | 4 | 4 |

**Flags.** Sources: INTERPOL 2026 (2nd ed.) + CBUAE Decree-Law No. 6 of 2025 + Tawazun Council 2021 mandate + OECD 2025 Guidelines — all verified. Data: available (Y). Special hardware: not required (N). Primary venue: ACM ICAIF or a KDD graph-anomaly workshop for the merged paper, EPJ Data Science / ACM DGov if led by the procurement angle. Overall confidence: **Medium–High**.

*Verification corrections folded in from source-checking:* OECD public-procurement spend is stated by OECD as ~13% of GDP (earlier secondary sources say ~12%); the wavelet-transformer paper's version of record is 13 January 2026 (a 2025 submission cycle); the INTERPOL report is the second edition (16 March 2026) and its USD 442B figure is an estimate it cites rather than measures.

---

## 19. References and Source Links

**Policy, mandate, and threat-assessment sources**
- INTERPOL, *Global Financial Fraud Threat Assessment* (2nd ed.), 16 March 2026 — https://www.interpol.int/en/News-and-Events/News/2026
- US Department of Justice announcement of the FBI–Dubai Police–China MPS operation (~USD 701M crypto restrained), 29 April 2026 — https://www.justice.gov ; secondary coverage: *The Next Web*, "The global scam economy hit $442 billion in 2025…" — https://thenextweb.com
- CBUAE Federal Decree-Law No. 6 of 2025 (effective 16 September 2025), Article 149 — https://www.centralbank.ae
- Tawazun Council procurement mandate (IDEX, February 2021): *The National* — https://www.thenationalnews.com/business/aviation/tawazun-to-manage-procurement-process-of-uae-armed-forces-and-abu-dhabi-police-1.1172144 ; *Janes*; *Khaleej Times*; Tawazun supplier portal — https://www.tawazun.ae
- OECD, *Guidelines for Fighting Bid Rigging in Public Procurement (2025 Update)*, DOI 10.1787/cbe05a56-en — https://www.oecd.org/en/publications/2025/09/oecd-guidelines-for-fighting-bid-rigging-in-public-procurement-2025-update_127880ea/full-report.html
- FATF, UAE removed from the grey list, 23 February 2024 — https://www.fatf-gafi.org

**Financial-crime methods and datasets**
- Poon et al., "LineMVGNN: Anti-Money Laundering with Line-Graph-Assisted Multi-View Graph Neural Networks," *AI* (MDPI) 6(4):69, 2025 — https://www.mdpi.com/2673-2688/6/4/69
- Lawal, Okolie & Obunadike, "An Explainable Graph Neural Network Framework for AML in Cryptocurrency Transactions Using the Elliptic Dataset," *IJCNC*, 17 December 2025 — https://www.ijcnc.com
- Lin et al., "Detecting illicit transactions in bitcoin: a wavelet-temporal graph transformer approach for anti-money laundering," *Scientific Reports* 16:1548, 13 January 2026, DOI 10.1038/s41598-025-23901-3 — https://www.nature.com/articles/s41598-025-23901-3
- Elmougy & Liu, "Elliptic++ Dataset," arXiv:2306.06108, 2023 — https://github.com/git-disl/EllipticPlusPlus ; base Elliptic via PyTorch Geometric `EllipticBitcoinDataset`
- Altman et al., "Realistic Synthetic Financial Transactions for AML Models" (IBM AMLworld), NeurIPS 2023, arXiv:2306.16424 — https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml

**Procurement-collusion methods and datasets**
- Imhof, Viklund & Huber, "Catching Bid-rigging Cartels with Graph Attention Neural Networks," arXiv:2507.12369, July 2025 — https://arxiv.org/abs/2507.12369
- Gomes, Kueck, Mattes, Spindler & Zaytsev, "Collusion Detection with Graph Neural Networks," arXiv:2410.07091, October 2024 — https://arxiv.org/abs/2410.07091
- "Detection of fraud in public procurement using data-driven methods: a systematic mapping study," *EPJ Data Science*, 2025, DOI 10.1140/epjds/s13688-025-00569-3
- García Rodríguez et al., "Collusion detection in public procurement auctions with machine learning algorithms," *Automation in Construction* 133:104047, 2022 — https://www.sciencedirect.com/science/article/pii/S0926580521004982
- "Public procurement cartels: A large-sample testing of screens using machine learning," *Int'l Journal of Industrial Organization*, 2025 — https://www.sciencedirect.com/science/article/pii/S0167718725000943 ; dataset: Mendeley Data f3y4nrn3s6/2 — https://data.mendeley.com/datasets/f3y4nrn3s6/2
- Open Contracting Data Standard bulk data — https://data.open-contracting.org ; standard docs — https://standard.open-contracting.org

**Additional citations supporting the merged framing (from verification research)**
- Ma, Wu, Xue, Yang, Zhou, Sheng, Xiong & Akoglu, "A Comprehensive Survey on Graph Anomaly Detection with Deep Learning," *IEEE TKDE* 35(12):12012–12038, 2023, arXiv:2106.07178 — the unifying taxonomy for node-/edge-/subgraph-level anomaly detection across finance and beyond.
- Motie & Raahemi, "Financial fraud detection using graph neural networks: A systematic review," *Expert Systems with Applications*, 2024 — https://www.sciencedirect.com/science/article/pii/S0957417423026970
- "Graph neural networks for financial fraud detection: a review," *Frontiers of Computer Science* (Springer), 2024.
- PwC, on rule-based AML transaction-monitoring false-positive rates (90–95%); Lannoo & Parlour (2021), as cited in AAAI-2022 fraud-detection work (arXiv:2112.07508).
- Saito & Rehmsmeier (2015), on the precision–recall curve as the appropriate metric under extreme class imbalance.
- Curated literature index: `safe-graph/graph-fraud-detection-papers` — https://github.com/safe-graph/graph-fraud-detection-papers

---

*This document is a self-contained, unified problem statement for a single Deep Learning capstone. Methodology, work plan, and submission logistics can be elaborated in an accompanying guidebook. The system is a human-in-the-loop screening and triage instrument; it makes no determination of guilt.*
