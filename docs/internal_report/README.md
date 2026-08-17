# Internal team report (LaTeX)

`collusiongraph_internal_report.tex` — a complete, plain-language walkthrough of
the whole project for internal use: datasets and their spread, splits, cleaning,
every algorithm and why it was chosen over the alternatives, the tuning history
with the numbers at each step, the results (including the negative ones), the
system and AWS architecture diagrams explained box by box, every dashboard
screen and control, use cases, limitations, future work (with an honest Web3
assessment), logs and reproducibility, and an anticipated-questions section.

## Building the PDF

No LaTeX toolchain is installed on the master machine, so the `.tex` is shipped
as source. It uses only standard TeX Live / MiKTeX packages — nothing to
download beyond a normal distribution.

```bash
pdflatex collusiongraph_internal_report.tex
```

Run it **twice** so the table of contents and cross-references resolve, or use:

```bash
latexmk -pdf collusiongraph_internal_report.tex
```

Overleaf also compiles it as-is: upload the single `.tex` file and hit Recompile.

To install a toolchain on Windows:

```bash
winget install MiKTeX.MiKTeX
```

## House rule

Every number in the report is copied from a measured artifact under
`eval_outputs/` and cross-referenced to `PROGRESS.md`, `docs/model_card.md` or
`docs/reproducibility.md`. Nothing is estimated or recalled from memory.

At the time of writing, all 36 quoted metric values were verified
programmatically against the stored artifact JSON files, and the structure
(braces, environments, table column counts, cross-references) was checked
mechanically.

When results change, update the report alongside the ledger — the same
discipline `poe paper-tables` enforces for the manuscript tables.
