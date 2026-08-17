# Presentation scripts

Spoken scripts for the demo, in the reference slide format: per slide a title,
an **Importance** rating, a **Suggested time**, a blue **Say this** box, a
green **What this actually means (plain English)** box, and an amber **If the
evaluator asks** box.

| File | Covers | Length |
|---|---|---|
| [`dashboard.tex`](dashboard.tex) | the Investigator Console, tab by tab — **this is the opening of the talk** | 30 slides, ~21 min |
| [`architecture.tex`](architecture.tex) | `docs/architecture.html` — the pipeline, the trust boundary, the cloud, the costs | 19 slides, ~16 min |
| [`scriptstyle.sty`](scriptstyle.sty) | the shared house style — **must sit beside the `.tex` files** | — |

## Building the PDFs

From inside this directory:

```bash
pdflatex dashboard.tex
pdflatex architecture.tex
```

Run each **twice** if you want the running-header page numbers settled. Works
with MiKTeX, TeX Live, or by uploading the three files to Overleaf. No custom
packages — everything comes from a standard TeX distribution (`tcolorbox`,
`fancyhdr`, `enumitem`, `needspace`, `geometry`, `xcolor`, `lmodern`).

Both files were last compiled clean with pdflatex (MiKTeX 25.12): dashboard
24 pages, architecture 14 pages, zero errors, no margin overflow.

## Conventions inside a `Say this` box

- **` / `** is a breath — pause there.
- **`[ square brackets ]`** are stage directions: things you *do* with the
  mouse, not words you say.
- **`____`** is a blank to fill in live (your group number, a name).

## The one rule these scripts are checked against

`scripts/audit/ui_jargon.py` (pass 2) reads every `Say this` block and fails if
it finds machine-learning jargon, a printed decimal (`0.32` instead of "about a
third"), a bullet list, or a sentence over 30 words — because none of those are
audible until you are already on stage. Run it after any edit:

```bash
uv run python scripts/audit/ui_jargon.py
```
