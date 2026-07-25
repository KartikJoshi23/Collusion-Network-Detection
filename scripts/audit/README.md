# Audit scripts

The checkers used to *measure* quality claims instead of asserting them. Every
one was written because a stakeholder review found something we had not checked.

Run from the repository root:

```bash
uv run python scripts/audit/ui_jargon.py
```

| Script | What it checks | Last measured |
|---|---|---|
| `ui_jargon.py` **pass 1** | Machine-learning jargon in strings a **user actually reads** on screen (JSX text, `title=`, `label=` — never comments or identifiers). | 24 → 5 → **7 accepted** (6 chart/metric labels where the metric's real name belongs, 1 JSON export key) |
| `ui_jargon.py` **pass 2** | The `> **SAY THIS**` blocks of `docs/presentation_script_*.md` — text read **aloud**. Stricter than the screen: pass-1 jargon plus the brief's §4 list, no printed decimals ("about a third", never `0.32`), no bullet lists, no sentence over 30 words. Exits non-zero on any violation. | 42 blocks, **0 violations** |
| `readability.py` | Long sentences, stacked clauses and jargon density in the LaTeX report. | 33 of 787 (4.2%) → **47 of 1196 (3.9%)** after the architecture/cloud/dashboard rewrite |
| `jargon_audit.py` | Terms used in the report but never defined in its glossary. | 59 → **31**, all false positives |
| `why_audit.py` | Bare parameter values (`2 layers`, `0.5 threshold`) with no justification nearby — the "why that number?" an evaluator asks. | all now answered |
| `texcheck.py` | Report LaTeX: brace balance, environment matching/nesting, undefined custom envs, dangling `\ref`. | clean |
| `texcols.py` | Every `tabular`/`longtable` row width against its declared column count. | 0 mismatches |
| `verify_numbers.py` | **Every number quoted in the report against the stored result files.** | **46/46** |
| `api_audit.py` | Every API surface for every dataset: alerts, metrics, rigor, subgraph, explanations. | 0 failures |
| `normal_case_sweep.py` | Every alert on every dataset resolves to a bundle or a clean 404. | 980 alerts, 0 surprises |
| `copilot_battery.py` | Simple / medium / adversarial questions at the live assistant, graded for grounding and guilt language. | 11/11 answered, 0 violations |

`copilot_battery.py` and `api_audit.py` need the API running:

```bash
uv run collusiongraph serve --port 8001
```

## The habit these encode

A claim nobody measured is not a finding. Three times this project stated a
limit that turned out to be false when someone finally ran it — most recently
"AMLworld needs hardware we do not have", which trains on a laptop CPU in 52
seconds. If you are about to write "X is not possible because Y", spend the
five minutes proving Y first.

**And check the checker.** On 2026-07-25 `ui_jargon.py` reported 5 remaining
hits and was believed. Its JSX-text rule required a capital letter and 14+
characters, so the alert queue's slider label `budget k` — eight lowercase
characters, on the busiest screen in the product — was invisible to the audit
whose entire job was finding exactly that. Two more (`Motif`, `review budget`)
were hiding behind the same rule. A measurement tool with a blind spot reports
a clean number and is worse than no tool, because the clean number gets quoted.
