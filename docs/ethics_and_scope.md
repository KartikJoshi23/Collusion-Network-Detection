# Ethics & Scope Statement

*§8 repo deliverable; §7 step 33 (M8). The binding constraints below are
enforced in code where a surface exists, not only asserted here.*

## The one-sentence rule

**Screening signal only — no determination of guilt.** Every output of this
system is an investigative prioritization aid over public research data;
nothing it produces is, or may be presented as, a finding of wrongdoing by
any person or firm.

## Where the rule is enforced (not just stated)

| Surface | Enforcement |
|---|---|
| API responses | `caveats` field on every payload (read-only artifact server) |
| Explanation bundles | immutable `caveats` field — a pydantic validator refuses any altered wording |
| Frontend | ethics footer on every screen; dossier carries the caveat |
| Investigator Copilot | guilt-language guard rewrites/blocks accusatory drafts before release (measured: 0 released violations across the goldens gate); every answer carries an AI-generated label + the caveat |
| Practitioner-study packets | caveat rendered verbatim; a leak guard refuses to render ground-truth vocabulary |

## Data boundaries

- Public and/or anonymized research datasets only (see `docs/datasheets/`);
  AMLworld is fully synthetic. No UAE institutional, personal, or classified
  data enters the project at any point.
- Raw data is never committed or redistributed; the repo ships download
  scripts + checksum manifests; licenses are recorded per dataset.
- No per-person outputs exist anywhere in the stack; procurement entities are
  anonymized firm/buyer identifiers from the source datasets.

## Scope limits (TRL 3–4)

Validated research prototype: no authentication/multi-user hardening, no
real-time scoring, no case-management workflow, alert export only. Model
limitations that bear on responsible use — validation blindness under
temporal shift, seed variance, case-control prevalence artifacts, absent
explanations for the R-GCN — are quantified in `docs/model_card.md` and the
paper's limitations section.

## Regulatory alignment

Fraud/AML screening is an EU AI Act high-risk category (obligations
enforceable 2 Aug 2026). The paper carries a regulatory-alignment section;
the design choices above (human-in-the-loop framing, explanation bundles,
logged caveats, no automated adverse action) are the project's alignment
posture, documented — not a compliance claim.
