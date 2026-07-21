# Datasheet — García Rodríguez multi-country collusion data (D3, procurement cross-market spine)

*Per Gebru et al. (2021), abbreviated; §7 step 33. Facts verified in Week-1
EDA (notebook 04).*

**Motivation.** Bid-level auction data across six markets with per-bid
collusion labels (García Rodríguez et al. 2022, Automation in Construction
133:104047) — the cross-market transfer spine (RQ2) and the only source of
losing-bid identity structure among the labeled procurement sets.

**Composition.** 64,348 bid rows, 9,781 tenders, 6 markets (Japan, Italy,
Brazil, USA, Switzerland ×2); 54,389 losing-bid rows; collusive share
11.3%–81.8% per market; bids-per-tender 2.3–91.9. Seven screen variables
(CV, SPD, DIFFP, RD, KURT, SKEW, KSTEST) 100% populated. **Bidder identities
(`Competitors`) exist in 4 of 6 markets** — the Swiss files carry the
anonymous bid-price tier only. Italy ships no date column; Japan dates are
epoch seconds.

**Collection & preprocessing.** Compiled by the original authors from
competition-authority case records; firms appear as numeric IDs. Our adapter
ingests per-market files (the combined file drops the identity column);
undated data participates only in entity-disjoint (LOMO) evaluation, never in
temporal splits (§9.1b).

**Uses & measured results.** LOMO transfer (macro lift 1.57 — positive on
every identified market; Italy P@10 = 1.00), co-bid screens, bid-tier
features. Within-file prevalences are research-sample artifacts — lift is the
only cross-fold comparator.

**Distribution & license.** Open-access supplement (article CC BY-NC-ND 4.0
per Crossref); fetched from ars.els-cdn.com; never redistributed here;
manifest `data/manifests/garcia_rodriguez.json`.

**Maintenance.** Static journal supplement; manifest pins checksums.
