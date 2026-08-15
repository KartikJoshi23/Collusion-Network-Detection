# Datasheet — Georgia OpenTender OCDS corpus (D5, unlabeled scale + deployment path)

*Per Gebru et al. (2021), abbreviated; §7 steps 30/33. Facts measured at
ingestion, 2026-07-20.*

**Motivation.** An unlabeled, standards-formatted (OCDS) national procurement
corpus for (a) synthetic cartel-motif injection with known ground truth at
scale (RQ2), (b) unsupervised-arm stress testing, (c) the documented path to
OCDS-standard deployment. Publisher selected by measurement across all 134
OCP Data Registry publications: Georgia populates the standard
`bids.details[]` extension with identified tenderers **including losing
bidders** — the co-bid substrate injected motifs live in (selection rationale
and runners-up in the PROGRESS.md Decision log).

**Composition (measured).** 451,346 compiled releases, 2010–2025; IR graph:
488,300 nodes (33,218 firms / 451,346 tenders / 3,736 buyers) and 1,449,077
edges (687,336 identified-bidder `bids_on`, 310,395 `awarded`, 451,346
`buys_from`); zero undated releases, zero bids without tenderer ids; amounts
in GEL.

**Collection & preprocessing.** Published by the Georgian procurement system
via OpenTender/OCP Data Registry (publication 52); per-year JSONL.gz
(~230 MB). Adapter `ocds_to_ir` streams releases → IR; id-less records and
undated releases are skipped and counted, never guessed. **No ground-truth
collusion labels exist** — every firm/tender is `unknown` by construction;
this dataset is the unsupervised/injection substrate and must never be
presented as a labeled benchmark.

**Uses & measured results.** At-scale injection study (163,327-node test
window): clique-type coordination recoverable at 1.2% budget
(coordinated_cluster 0.9275 ± 0.162 @2000), award-pattern motifs evade
structure-only arms seed-invariantly.

**Distribution & license.** CC BY-NC-SA 4.0 (registry publication page,
verified 2026-07-20); research use with attribution; never redistributed
here; checksums in `data/manifests/ocds_georgia.json`.

**Maintenance.** Registry updates half-yearly; the manifest pins the
2026-07-20 snapshot — re-running `poe data` verifies against it and will
flag upstream changes as mismatches rather than silently absorbing them.
