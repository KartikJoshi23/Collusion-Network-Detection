# Datasheet — Mendeley EU cartel dataset (D4, primary labeled procurement anchor)

*Per Gebru et al. (2021), abbreviated; §7 step 33. Facts verified in Week-1
EDA (notebook 03).*

**Motivation.** Court-verified cartel cases matched to public-procurement
contract records (Fazekas, Wachs, Tóth & Abdou; companion paper IJIO
S0167718725000943) — the only labeled firm-level procurement anchor here.

**Composition.** 15,616 contract rows; 73 distinct cartel cases; `is_cartel=1`
on 6,548 rows (41.9%); 7 anonymized countries (`country_1..7`), 2004–2021;
per-country rows 162–7,860 and cartel share 9.9%–59.6%. Precomputed screens
ship with the data (`lot_bidscount` 100% populated, `relative_value`,
Benford MAD, single-bid share).

**Collection & preprocessing.** Assembled by the original authors from public
tender records + competition-authority case files; firm/buyer identifiers are
anonymized within country. Our adapter builds the award-network-first IR
(§4.2 rule 1) — **losing-bidder identities do not exist in this data**
(verified: `bidder_id` is the awardee), so no co-bid identity graph is
constructible from it. Training labels are reconstructed as-of the split
boundary (audit F1) to prevent future-label leakage.

**Uses & measured caveats.** LOCO transfer matrices, firm-level baselines,
R-GCN experiments (honest negative: 0.2808 ± 0.0087 vs 0.358 prevalence),
alert queue + bundles. **This is a case-control research sample, not a
population file:** within-sample prevalence (41.9%; 0.29–0.89 per fold) is a
construction artifact — cross-fold comparisons must use lift over the fold's
own prevalence, never raw AUC-PR; population screening claims are out of
scope.

**Distribution & license.** CC BY-NC 3.0 (per the Mendeley record, DOI
10.17632/f3y4nrn3s6.2); sha256 matches Mendeley's official API hash; never
redistributed here; manifest `data/manifests/mendeley_eu.json`.

**Maintenance.** Versioned upstream (v2, 2025-08-12); manifest pins v2.
