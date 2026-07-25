# BRIEF — Presentation scripts + "explain, don't define" rewrite

**Status: NOT STARTED. This is the top priority and the whole of the next session.**

Written 2026-07-25 after a stakeholder review. Read this whole file before
writing a line — it contains six rounds of rejection history, and repeating any
of those mistakes wastes another session.

---

## 1. What the stakeholder actually said

Verbatim, condensed:

- *"Case 16 still uses extremely tough language. I showed it to a professional
  and he said such difficult language is not at all used in industry. Make it so
  simple that even a high school kid understands it just by reading it. Not only
  Case 16 — all the cases and cases like 16."*
- *"You made huge errors in the report. In system architecture and cloud
  architecture, everything is just a single or two-three lines of meaning, no
  proper explanations. There is no point reading it from the report — it made
  the work harder rather than simpler. Same for the dashboard screens."*
- *"Create a new presentation script file. These two are the most important
  things the evaluator will question."*
- *"Make the script so that even if we read it, it sounds completely natural and
  no one can tell we are reading from a script."*
- *"After each script part, give an explanation part so we understand what it
  actually means."*
- *"During the presentation we are not going to say only the meaning. We would
  have to explain it in very very simple terms."*

**The core diagnosis: the report and UI give DEFINITIONS. The stakeholder needs
EXPLANATIONS he can speak aloud.** "AUC-PR is the area under the
precision-recall curve" is a definition and is useless on stage. "If you shut
your eyes and picked at random you'd score 6 out of 100. We score 47. That's
about seven times better than guessing" is an explanation.

---

## 2. Deliverables

### 2a. `docs/presentation_script_dashboard.md` (NEW)

A spoken script covering **every tab, every control, every panel** of the
console. Nothing omitted — if it is on screen, it is in the script.

Tabs to cover: Overview · Alert Queue · Graph Explorer · Case Detail ·
Model Lab · About · plus the Copilot dock, the domain toggle, the dataset
picker, the budget slider and the risk-band filter.

### 2b. `docs/presentation_script_architecture.md` (NEW)

Same treatment for `docs/architecture.html`: the ten numbered pipeline stages,
the trust boundary, the algorithm cards, both AWS planes, and the three cost
tiers.

### 2c. Report rewrite — `docs/internal_report/collusiongraph_internal_report.tex`

Sections `\label{sec:arch}`, `\label{sec:cloud}` and `\label{sec:dashboard}`
currently list components with one line each. Replace with real explanations:
what it is, why it exists, what breaks without it, and the sentence you would
say out loud about it.

### 2d. Another plain-language pass on the dossier

`frontend/src/lib/plainReason.ts` was rewritten once and is *still* too hard.
See §5 for what to try next.

---

## 3. The required format (non-negotiable)

Every unit of both script files looks exactly like this:

```markdown
### Alert Queue — the budget slider

> **SAY THIS**
>
> "This slider is the honest part of the whole system. It asks: how many cases
> can your team actually get through this week? Say it's fifty. I drag it to
> fifty — and watch this number here. That's telling me that of those fifty,
> about a third turn out to be real. Not a promise. That's measured on cases
> where we already know the answer."

**WHAT THIS MEANS**

The slider sets *k* in Precision@k. Every headline number in the project is
quoted at a budget because a screening tool has no meaning without one — you can
catch everything if you're willing to review everything. The readout recomputes
from stored results; it is never estimated in the browser.

**IF THEY ASK…**

*"Why is precision only 0.32?"* — Because these are groups, not single
transactions, and 77% of this dataset has no recorded answer at all. A group we
could not confirm is not the same as a group that was wrong.
```

Rules for the **SAY THIS** blocks:

1. **Speakable, not readable.** Contractions, short sentences, the occasional
   sentence fragment. Read it aloud — if you run out of breath, it is too long.
2. **No lists.** Nobody speaks bullet points. Turn them into "there are three
   of these — first… then… and finally…".
3. **Signpost with the mouse.** "Watch this number", "up here on the left",
   "I'll click into one of these".
4. **Numbers spoken, not printed.** "about a third", "roughly seven times
   better", "one in a hundred" — not "0.3245".
5. **No jargon at all.** Not one term from the banned list in §4.
6. **Include the transitions** between tabs, so the talk flows.
7. **Mark timing**, e.g. `[~90 seconds]`, and give a total at the top.

---

## 4. Banned vocabulary (already enforced on the UI by a test)

Never in a **SAY THIS** block: *node, edge, subgraph, motif, attention,
embedding, calibrated, prevalence, AUC-PR, precision@k, inductive, isotonic,
ensemble, ablation, bootstrap, artifact, corpus, heuristic, topology,
structural, attribution, fidelity, deduplicated, Leiden, Jaccard, k-core,
seed, multi-seed, regime, quantile.*

Say instead: *account / company · connection · small piece of the network ·
pattern · which link mattered most · summary of behaviour · put on a proper
0-to-1 scale · what blind guessing would score · how many of your top picks are
real · the honest test · combining several models · removing a part to see if it
mattered · a fairness check · a saved result file · our reference library ·
shape · repeat runs.*

The **WHAT THIS MEANS** blocks *may* use the technical term — but must
introduce it, e.g. "this is what the paper calls Precision@k".

---

## 5. The dossier language, attempt three

Current output for Case 16 (`elliptic_pp:gatv2_multi_s0:16`) is in
`frontend/src/lib/plainReason.ts`. It already avoids jargon and passes a
14-term banned-word test, yet was still judged too hard. Diagnosis for the next
attempt:

- The sentences are still **explaining a system** ("We asked the computer which
  parts actually made it suspicious"). They should **describe a situation**
  ("Eighty-five accounts. Money went through all of them in one go, one after
  another, in a single afternoon. That's not how a normal business moves
  money.").
- Lead with the **striking fact**, not the method.
- Cut every clause that explains *how we know* — that belongs in the technical
  panel underneath.
- Target: a 15-year-old reads it once, at normal speed, and could repeat the
  gist to a friend.

Test the result on `elliptic_pp:gatv2_multi_s0:16` (85 accounts / 84 links /
one time window) and on `mendeley_eu:sage_struct_s0:1` (2 firms).

`frontend/src/lib/plainReason.test.ts` pins the banned words and a 26-word
sentence cap — keep both, tighten the cap to 20 if it still reads long.

---

## 6. Rejection history — do not repeat these

| Round | What was rejected | The lesson |
|---|---|---|
| UI V1 | flat, single colour | subtle reads as unfinished |
| UI V2 | "still horrible, one colour dominant" | needed simultaneous multi-hue |
| UI V3 | passed on look | — |
| UI V4 | "still blue dominated" | the *canvas* was blue, not the accent — fixed by making chrome neutral |
| Report v1 | "extremely tough language" | rewrote whole report, glossary 71→144 entries |
| Report v2 | "still tough; only meanings, no explanations" | **current round** — meanings ≠ explanations |
| Architecture doc | rejected 5 times | landed only after asking the stakeholder to choose the format first |

**The pattern: ask what "good" looks like before building, and when told
something is too hard, do not assume the previous fix was close.**

---

## 7. Verification tooling (already written, in `scripts/audit/`)

Run these; they are how the last round was measured rather than guessed.

| Script | What it checks |
|---|---|
| `ui_jargon.py` | jargon in strings a user actually sees on screen. Was 24, now 5 |
| `readability.py` | long sentences / stacked clauses / jargon density in the report |
| `texcheck.py`, `texcols.py` | report LaTeX structure and table column counts |
| `verify_numbers.py` | every quoted number against the stored result files (46/46) |
| `jargon_audit.py` | report terms used but never defined in the glossary |
| `why_audit.py` | bare parameter values with no justification nearby |
| `api_audit.py`, `normal_case_sweep.py` | every API surface, every alert |
| `copilot_battery.py` | simple/medium/hard questions at the live assistant |

Run from the repo root, e.g. `uv run python scripts/audit/ui_jargon.py`.

**Apply the same discipline to the new script files:** extend `ui_jargon.py`'s
word list at the `SAY THIS` blocks and drive the count to zero.

---

## 8. Current state (all green as of 2026-07-25)

- backend `uv run poe check` — **381/381**
- frontend `npx tsc -b --noEmit` clean, `npx vitest run` — **43/43**
- report: structure clean, 0 table mismatches, **46/46 numbers verified**
- dashboard: 24 view×dataset combinations, 0 render errors
- last commit on `main`: `24a5116`

Start the console with:

```bash
uv run collusiongraph serve --port 8001
```

then in `frontend/`:

```bash
VITE_API_TARGET=http://127.0.0.1:8001 npm run dev
```
