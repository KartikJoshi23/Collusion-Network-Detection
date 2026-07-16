# Red-flag mappings (§4.4)

The two curated red-flag vocabularies are the only domain-specific artifacts in
the system besides the data adapters. **Source of truth:** the YAML tables in
[`backend/collusiongraph/explain/redflags/`](../backend/collusiongraph/explain/redflags/) —
this document describes them; if they diverge, the YAMLs win (and the
vocabulary-completeness test in `test_explanations.py` enforces that every
motif the matcher can emit maps to at least one indicator per domain).

All indicator texts are **paraphrased condensations** of the public source
frameworks, cited by our own stable ids — they are not verbatim reproductions.

## Financial (FATF-derived), `fatf.yaml`

| Indicator id | Motif(s) | Summary |
|---|---|---|
| FATF-STRUCT-01 | `fan_in` | Sub-threshold deposits converging on one account (structuring/smurfing) |
| FATF-LAYER-01 | `fan_out` | Rapid dispersal to many counterparties without economic purpose |
| FATF-LAYER-02 | `pass_through` | Chains with near-zero retention and abnormally short holds |
| FATF-CIRC-01 | `cycle` | Funds returning to their originator via intermediaries (round-tripping) |
| FATF-SHELL-01 | `common_control` | Ostensibly unrelated accounts sharing owners/agents/addresses |

## Procurement (OECD-derived), `oecd.yaml`

| Indicator id | Motif(s) | Summary |
|---|---|---|
| OECD-ROT-01 | `rotation` | The same supplier group wins in turn across tenders |
| OECD-COVER-01 | `cover_bid` | Losing bids implausibly close above the winner |
| OECD-ALLOC-01 | `partition` | Suppliers never competing for the same buyer/territory |
| OECD-CLUST-01 | `clique` | Recurring co-bidders with tightly clustered prices |
| OECD-LINK-01 | `common_control` | Competing firms sharing directors/addresses/contacts |

## How a citation is produced

1. The **motif matcher** (`explain/motif_matcher.py`) finds pattern-level
   structures in an alert's member subgraph — transparent rules, independent
   of the learned model and of the synthetic injector (which cross-validates
   it at 100% fixture recall, §9.1).
2. `map_red_flags` maps each matched motif type to its indicators; multiple
   instances of the same motif produce **one** citation carrying an instance
   count, never duplicate rows.
3. The citation ships inside the alert's explanation bundle as
   `{framework, indicator_id, indicator_text, matched_because}` — a bundle
   with an unresolvable citation is unconstructable by schema validation.

Every bundle carries the fixed caveat: *screening signal only — no
determination of guilt*.
