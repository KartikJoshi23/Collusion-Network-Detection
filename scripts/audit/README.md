# Audit scripts

The checkers used to *measure* quality claims instead of asserting them. Every
one was written because a stakeholder review found something we had not checked.

Run from the repository root:

```bash
uv run python scripts/audit/ui_jargon.py
```

| Script | What it checks | Last measured |
|---|---|---|
| `ui_jargon.py` | Machine-learning jargon in strings a **user actually reads** on screen (JSX text, `title=`, `label=` — never comments or identifiers). | 24 → **5** (3 chart axis labels, 1 export key, 1 heading) |
| `readability.py` | Long sentences, stacked clauses and jargon density in the LaTeX report. | 38 → **33** of 787 |
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
