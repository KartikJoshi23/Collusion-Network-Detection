# Declarations — draft for the authors

Status: **draft, not yet in the manuscript.** Part G (the Springer template and its
declarations section) waits for the target journal. Items marked
**[AUTHORS TO PROVIDE]** or **[AUTHORS TO CONFIRM]** are decisions or facts only
the authors can supply. Nothing here has been sent anywhere.

## Funding
[AUTHORS TO PROVIDE]

## Competing interests
[AUTHORS TO PROVIDE]

## Ethics approval and consent
Draft wording, for confirmation: "Not applicable. The study uses only public
datasets and a synthetic dataset, and involves no human participants. The
practitioner study protocol is described but was not run."
[AUTHORS TO CONFIRM]

## Data availability
Draft wording: "All datasets are public and are downloaded from their canonical
sources: Elliptic++ (Elmougy and Liu, 2023), IBM AMLworld HI-Small (Altman et
al., 2023), the Mendeley EU cartel dataset (Fazekas et al., 2025,
doi:10.17632/f3y4nrn3s6.2), García Rodríguez et al. (2022), and OCDS Georgia
(OpenTender). No raw or modified data is redistributed."
[AUTHORS TO NOTE: this holds for branch `paper/journal-revision`. Until it
is merged, the public main branch shows raw-row previews in three EDA
notebooks (5 Mendeley, 5 García and 3 AMLworld rows), and the repository
history keeps them after the merge. Whether to rewrite that history is
yours to decide.]

## Code availability
**Recommended (item L3), for Dr. Garg to confirm.** Now in the abstract and
Appendix C:

> The code, every experiment configuration, the number manifest and the leakage
> tests are available at https://github.com/KartikJoshi23/Collusion-Network-Detection.

Recommendation: before submission, archive a tagged release of the repository on
Zenodo and add its DOI here, so the cited version cannot change. That needs an
author's Zenodo account, so it is left to the authors.

## Author contributions
[AUTHORS TO PROVIDE] (for example, CRediT roles per author)

## Acknowledgements
[AUTHORS TO PROVIDE] The manuscript keeps its existing placeholder.

## Use of generative AI — draft, flagged for confirmation
**[AUTHORS TO CONFIRM every sentence below before it is used.]** It is written
from the repository history and from this revision, and states only what the
record shows.

> The authors used AI coding and writing assistants in this work. The software
> was developed with substantial help from Anthropic's Claude models (Claude
> Fable 5, Claude Opus 4.8, Claude Opus 5 and Claude Opus 5.5) through Claude
> Code; the repository history marks each assisted change. The first full draft
> of the manuscript was generated with Claude Opus 5 from the project blueprint
> and then edited by the authors. During the revision, Claude Opus 5.5 ran the
> reproducibility checks and the new experiments, implemented the code changes,
> checked every reference against its source, and drafted the text changes.
> [The authors reviewed every change and take full responsibility for the
> content. — AUTHORS TO CONFIRM] No AI system is an author. The guarded copilot
> in Section VI uses NVIDIA Nemotron models as part of the system under study;
> it was not used to write the paper.

Facts behind the draft, for checking:

- Commit 09c027b (17 August 2026), "the research paper, written from the
  blueprint", carries the trailer "Co-Authored-By: Claude Opus 5".
- Commit trailers across the repository: Claude Fable 5 (131), Claude Opus 5
  (34), Claude Opus 5.5 (43 when this draft was last updated, all from this
  revision), Claude Opus 4.8 (12).
- This revision ran on the branch `paper/journal-revision` with Claude Opus 5.5
  in Claude Code.

## Earlier versions of these results (item 19)
**Recommended wording, for Dr. Garg to confirm or change.** Known earlier
appearances, from the revision plan (item D8):

- the course report (`Report.pdf`, SP Jain School of Global Management, Deep
  Learning course, August 2026), which quotes 0.5492 and 0.4729;
- the public repository's documentation and the earlier draft of this
  manuscript, in the same repository.

No preprint, conference paper or other peer-reviewed publication was found.

In the manuscript (Section IV-E), the old sentence "Our own previously published
seed-0 GATv2 figure of 0.5492" now reads: "Our earlier project report and public
repository quoted the seed-0 GATv2 figure of 0.5492, which happens to be the best
of the five."

Recommended paragraph for the cover letter:

> Earlier versions of some of these results appeared in an unreviewed course
> project report (SP Jain School of Global Management, August 2026) and in the
> project's public GitHub repository. Neither has been peer reviewed or submitted
> elsewhere. The revised manuscript reports five-seed results throughout; the
> seed-0 figure quoted earlier (0.5492) is now given as one of five seeds, with the
> five-seed mean of 0.4729 as the headline.

Two corrections made during the revision could also be mentioned if the editor
asks: the explanation counts were rebuilt from the committed queues (the counts
did not change), and one cross-domain probe value moved from 0.2841 to 0.2843
between machines (the paper states this).
