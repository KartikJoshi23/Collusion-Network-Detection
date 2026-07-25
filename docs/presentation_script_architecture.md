# Presentation script — the architecture page

Covers `docs/architecture.html`: the ten-stage system flowchart, the trust
boundary, the method cards, both cloud planes, and the three cost tiers.

**Total running time: about 15 minutes.** ⭐ marks the units to keep if you are
cut short.

Same three-part format as the dashboard script:

- **SAY THIS** — spoken out loud, close to word for word.
- **WHAT THIS MEANS** — for you. The real mechanism, in project vocabulary.
- **IF THEY ASK…** — the pushback that actually comes, and the answer.

**Before you start.** Open `docs/architecture.html` in any browser. It needs no
internet connection and no server. There is a light/dark toggle top right —
light reads better on a projector. Scroll to the top of the System
Architecture flowchart.

**The one sentence to hold on to:** the top half of the diagram *builds*
results and then stops running; the bottom half can only *read* them. Every
other design decision on the page falls out of that.

---

## Unit 0 — how to read the page ⭐

`[~45 seconds]`

> **SAY THIS**
>
> "This is the whole system on one page, and it reads top to bottom like a
> production line.
>
> There are two big boxes. The green one at the top is the deep-learning
> pipeline. That part runs, does its work, writes its answers to files, and then
> shuts down. The blue one underneath is the live product — the website, the
> doorway behind it, the assistant. That part is always on, and it can only read
> what the green part wrote.
>
> Between them there's a line labelled trust boundary. I'll come back to that,
> because it's the single most important line on this page."

**WHAT THIS MEANS**

Two clusters: `OFFLINE — DEEP-LEARNING PIPELINE · writes files, then exits` and
`ALWAYS-ON PRODUCT · read-only · tiny CPU · no GPU`, separated by the dashed
trust boundary at y=684 in the SVG. The whole thing runs on one machine with
`docker compose up`.

---

## Unit 1 — stages one and two: getting everything into one shape

`[~55 seconds]`

> **SAY THIS**
>
> "Box one, the readers. Six public datasets, six readers, one each. Each
> reader checks the file's fingerprint before it touches anything. If a
> download was corrupted, or somebody swapped a file, it stops. It doesn't
> quietly train on the wrong thing.
>
> Box two is the one I'd underline. Everything gets converted into a single
> common format — things, connections between things, and where we have them,
> answers. And that's where the time rules get applied too.
>
> Here's why box two is the trick of the whole project. After that box, the
> system genuinely doesn't know which crime it's looking at. Bank accounts and
> construction firms arrive as the same kind of object. That's what lets one
> stack handle both worlds — and it's why we could test whether one crime's
> knowledge transfers to the other at all."

**WHAT THIS MEANS**

Boxes 1–2: checksum-verified ingestion adapters into the unified graph IR
(§4.2 schema), plus the temporal/entity split policy. The domain-agnostic IR is
what makes RQ1 (shared structure) and the cross-domain transfer probes
expressible in the first place.

**IF THEY ASK…**

*"Don't you lose information by flattening two domains into one format?"* — You
lose nothing you cared about, because domain-specific facts survive as
attributes. What the shared format buys is that every downstream stage — the
learning, the grouping, the explaining, the measuring — is written once and
audited once, instead of twice with two sets of bugs.

---

## Unit 2 — stage three: four things happening at once ⭐

`[~80 seconds]`

> **SAY THIS**
>
> "Box three is four boxes side by side, and they're side by side because they
> genuinely run in parallel on the same network. Four different opinions about
> the same accounts.
>
> The first group learns from examples where somebody already knew the answer.
> Three different designs, and they differ in what they look at hardest. One
> works out which of your connections matter most and listens hardest to those.
> One treats money coming in differently from money going out. One handles
> several different kinds of relationship separately — winning a contract isn't
> the same as buying from someone.
>
> The second group needs no answers at all. It learns what normal looks like and
> then flags whatever it can't rebuild. That one matters far more than its
> score suggests, and I'll come back to why.
>
> The third group is hand-computed measurements. How many connections does this
> thing have. What shapes is it sitting inside. And for contracts, the classic
> warning signs — the same firms always bidding together, prices sitting
> suspiciously close.
>
> The fourth is the honesty group. That's the strongest old-fashioned method we
> could field, plus the planted-cartel tests, plus the automated test suite.
> It's there so nobody can accuse us of only racing against ourselves."

**WHAT THIS MEANS**

3a supervised GNNs (GATv2 / GraphSAGE / R-GCN, trained with focal loss against
~2% positives), 3b the unsupervised arm (DOMINANT + GAE), 3c hand-built graph
features (degrees, motif counts, k-core, procurement bid screens), 3d baselines
and checks (XGBoost, injection-recovery, 381 automated tests). Each produces a
score per node.

**IF THEY ASK…**

*"Why keep the unsupervised arm if it scores worst?"* — Because it is the only
arm that works where there is no answer key, which is the realistic deployment
case. In the Georgian planted-cartel study, where nothing is labelled, the
autoencoder scores about nine in ten on the bid-together cartels while the
non-learning floor scores about one in eight — and XGBoost cannot compete at
all, because it has nothing to train on. That is the clearest deep-learning
result in the project, and it comes from the arm with the worst headline score.

---

## Unit 3 — stage four: combining the opinions ⭐

`[~60 seconds]`

> **SAY THIS**
>
> "Box four merges those four opinions into one number per account. And the
> word 'first' in that box is doing enormous work.
>
> Here's the problem. Two models can both be good at ranking and still be on
> completely different scales. One says nought-point-nine when it's fairly sure.
> The other says nought-point-one when it's *certain*. Average those raw and the
> loud one flattens the quiet one, no matter which one was right.
>
> So we translate each model onto a proper scale first, checked against
> held-out data, and only then combine.
>
> We didn't take that on faith — we measured it both ways. Skip the translation
> step and the combined result collapses to roughly what blind guessing gets
> you. Do it properly and you get a result about nine times better. Same models,
> same data. That one ordering decision was worth more than any model we
> trained."

**WHAT THIS MEANS**

Box 4: isotonic calibration on labelled validation nodes, then fusion.
Calibrated ensemble 0.4434 ± 0.0501 versus rank fusion 0.0511 ± 0.0019 over
five seeds — a factor of about 8.7, against a prevalence baseline of 0.065.

**IF THEY ASK…**

*"Why not just pick the best single model?"* — On Elliptic we do report the
best single model, and it happens to be the trees. But the combination is what
survives when a member is weak, and the measured point is that calibrated
fusion preserves a strong member instead of being dragged down by weak
co-members. Rank fusion does the opposite. That is a finding, not a
preference.

---

## Unit 4 — stage five: from scores to a worklist ⭐

`[~55 seconds]`

> **SAY THIS**
>
> "Box five is where research becomes a product.
>
> Up to here we've got a score on every single account — sixty-seven thousand of
> them on the money side. That's useless to a human being. Nobody investigates
> sixty-seven thousand things.
>
> So we find the clusters. Those are groups that deal with each other far more
> than they deal with anyone else. We rank them. We throw away near-duplicates,
> so nobody opens the same case twice. And we cut the list at whatever number of
> cases the team can actually review.
>
> Two hundred and fifty-four groups on the money side. Two hundred and
> twenty-three on the contracts side. That's a morning's work, not a research
> output."

**WHAT THIS MEANS**

Box 5: Leiden community detection on the test-window graph, community-level
score roll-up, NMS-style overlap suppression at Jaccard 0.5, size cap at 100
members, cut at the review budget. 254 alerts from 318 communities on Elliptic
payments; 223 on Mendeley.

**IF THEY ASK…**

*"Does the grouping use the answers?"* — No. It runs on structure only. That is
deliberate, and it is what lets the exact same grouping step run on the
Georgian data, where no cartel labels exist at all.

---

## Unit 5 — stage six: the explanation layer

`[~65 seconds]`

> **SAY THIS**
>
> "Box six is the part I'd argue is the difference between a demo and something
> an investigator could use.
>
> Three things happen to every case at the top of the list.
>
> First, the explainer works out which handful of connections the decision
> actually depended on. Then we check it. We re-run the case with only those
> connections, and again with them taken away.
>
> Second, a set of hand-written rules checks the case against nine known
> shapes and puts a name on it, but only when it can actually prove the shape.
>
> Third, when a shape matches, we attach the official warning sign it
> corresponds to. The money ones come from F-A-T-F, the contract ones from the
> O-E-C-D. Quoted, with the source stamped on it.
>
> That last one is deliberate. An investigator can throw out everything the
> neural network says, and that evidence still stands on its own."

**WHAT THIS MEANS**

Box 6: PGExplainer minimal subgraph + sufficiency/necessity check, the motif
matcher (nine families), FATF/OECD red-flag citation. PGExplainer replaced
GNNExplainer after a three-arm ablation; regenerated bundles dropped
implausible-fidelity explanations from 38 of 50 to 1 of 50.

**IF THEY ASK…**

*"How do you know the explanation is honest and not a story?"* — Because it is
tested, not asserted. Sufficiency: show the model only the highlighted
connections and see whether the same alert comes out. Necessity: remove them
and see whether it disappears. When those two answers contradict each other we
put a warning on the case file rather than hide it.

---

## Unit 6 — stage seven: plain files

`[~35 seconds]`

> **SAY THIS**
>
> "Box seven. Everything the pipeline produced goes into ordinary files in a
> folder. Not a database, not a running service. Files.
>
> That sounds unglamorous and it's one of the best decisions in here. Files can
> be copied, checksummed, versioned, emailed to an examiner, and rolled back by
> pointing at a different folder. And a file cannot be quietly modified by the
> website that reads it."

**WHAT THIS MEANS**

Box 7: `alerts.parquet`, `explanations/*.json`, metrics, `serving.json`. The
file-based store is what makes the trust boundary enforceable and what makes
rollback a path change rather than a retrain.

---

## Unit 7 — the trust boundary ⭐

`[~70 seconds]`

> **SAY THIS**
>
> "Now the line. This is the thing I'd want you to remember from this page.
>
> Above the line: trains, learns, changes what the system believes. Powerful,
> and therefore dangerous. Below the line: shows people things. Reachable from
> the outside world, and therefore attackable.
>
> Those two properties must never sit in the same process, so we cut them
> completely apart. The top half writes files and exits. The bottom half opens
> those files read-only. There is no route from the bottom half back to the top.
>
> Think about what that means if somebody breaks into our website tomorrow.
> They can read published results. They cannot retrain a model, they cannot
> change anyone's score, and they cannot plant evidence in a case file.
>
> And there's a bonus. Because the serving side never trains anything, it needs
> no expensive hardware. It starts instantly, it runs on a cheap machine, and
> the whole thing demos on a laptop with the wifi switched off."

**WHAT THIS MEANS**

The security argument and the cost argument are the same argument. In the cloud
design this is enforced by AWS IAM (read-only role on the results bucket), not
merely by our own code — which is the strongest form of the claim and worth
saying explicitly if challenged.

**IF THEY ASK…**

*"Isn't that just a deployment detail?"* — It is an integrity property. In a
system whose output can affect whether somebody gets investigated, "an attacker
cannot alter a score" is not a deployment detail. It is also why the API
surface is read-only by construction: there is no write endpoint to abuse,
because none exists.

---

## Unit 8 — stage eight: the doorway and the assistant

`[~60 seconds]`

> **SAY THIS**
>
> "Below the line, box eight: a small read-only service that hands out those
> files. Give it a case number, it gives you the case. Ask for the network, it
> trims the network to a sensible size on the server before sending it, so your
> browser never receives a million lines.
>
> Every single response carries the ethics wording. Not just the pretty pages —
> the raw data too.
>
> Beside it, in its own box, the assistant. Note that it sits *beside* the
> doorway rather than behind it, and that both arrows on that box point in and
> out of the same read-only service. It has no other access to anything. Every
> number it says has to exist in what it looked up, accusing language gets
> rewritten automatically, and it sits a twenty-four question exam before every
> release."

**WHAT THIS MEANS**

Box 8: FastAPI, read-only, `/alerts?budget=k`, `/subgraph/{id}`,
`/explanations/{id}`, `/metrics`, `/rigor`. The Copilot is mounted at
`/api/v1/copilot` and reaches data only through read-only SQL and the same
served files. The §4.6 guards: numeric grounding, corpus grounding, guilt-
language rewriting, degenerate-output gate. Golden gate 24/24.

**IF THEY ASK…**

*"What stops the assistant hallucinating a number?"* — A check that runs after
the model has spoken. Every number in the answer must appear literally in the
evidence it retrieved; if it does not, the answer is marked unverified on
screen rather than shown clean. And the guard is outside the model, so
swapping the model does not weaken it.

---

## Unit 9 — stages nine and ten: the console, and the person

`[~45 seconds]`

> **SAY THIS**
>
> "Box nine is the console — the six screens I can walk you through separately.
>
> Box ten is a person. And it's on the diagram on purpose. The system produces a
> ranked list and the evidence behind it. A human being decides what happens
> next, within a fixed number of cases per week.
>
> That's not modesty. If a screening tool made the escalation decision, you'd
> have automated an accusation. This one shortens the list somebody has to
> read."

**WHAT THIS MEANS**

Box 10 exists to make the human-in-the-loop constraint architectural rather
than aspirational. It is the diagram's version of the footer caveat.

---

## Unit 10 — the method cards

`[~90 seconds]`

> **SAY THIS**
>
> "Scroll past the flowchart and every box gets a card explaining what it does
> and how it works, in everyday language. I won't read all twelve. Four worth
> pausing on.
>
> The graph networks. Ordinary machine learning looks at a thing's own
> properties. These look at *who it deals with*. Each account starts with a
> profile of numbers, and then in a few rounds every account blends in its
> neighbours' profiles. After a couple of rounds, something sitting inside a
> laundering ring looks measurably different from something that isn't — even
> if its own numbers looked perfectly normal.
>
> The rare-crime problem. Only about one in fifty of these things is a real
> case. A lazy model calls everything innocent and is right ninety-eight percent
> of the time and completely useless. So we change what the training rewards:
> easy correct answers earn almost nothing, and the effort goes where the rare
> cases are.
>
> The old-fashioned yardstick. Boosted decision trees — hundreds of small trees,
> each correcting the last. On the Bitcoin data they still beat our neural
> networks, and we publish that with a proper statistical test rather than
> burying it.
>
> And the rigour card. Every headline model was built five times with different
> starting randomness, comparisons were re-checked on thousands of reshuffles,
> and every country takes a turn being held out completely."

**WHAT THIS MEANS**

Twelve cards on the page: graph networks, GATv2 attention, GraphSAGE/R-GCN,
focal loss, the autoencoders, calibration + fusion, Leiden + dedup, XGBoost
baselines, PGExplainer, the matcher + red flags, the Copilot guardrails, and
statistical rigour. They are the visual twin of the report's methods section —
same explanations, different medium.

**IF THEY ASK…**

*"The trees beat your deep models — doesn't that sink the project?"* — On that
one dataset, they win, and section "Is this really a deep learning project?" in
the report answers it head-on. The short version: Elliptic ships hand-built
neighbour aggregates as spreadsheet columns, so the trees get the network for
free. The moment you take the answer key away — the planted-cartel studies —
the trees cannot run at all, and the deep models do the work.

---

## Unit 11 — the cloud: the always-on half ⭐

`[~70 seconds]`

> **SAY THIS**
>
> "Second diagram: what this looks like hosted as a real product. Same two
> halves, same boundary.
>
> Top half, always on. Users need a browser and nothing else. Route 53 turns our
> web address into a machine. CloudFront keeps copies of the site around the
> world so it loads fast wherever you are. There's a filter in front of
> everything that blocks the common attacks, and the connection is locked end to
> end.
>
> The site itself is just files in cheap storage, in a private area only the
> delivery network is allowed to read.
>
> The results live in their own versioned storage. Every run writes into its own
> dated folder — which means undoing a bad model is pointing at yesterday's
> folder. No retraining, no panic.
>
> And the permissions are the interesting bit. The public side is granted
> read-only rights to those results. So that trust boundary I showed you isn't
> just our own code being polite. Amazon enforces it."

**WHAT THIS MEANS**

Serving plane: Route 53 → CloudFront + WAF → S3 (private, OAC) for the site,
API/Copilot compute (Lambda at launch, Fargate across two AZs as it grows) →
versioned S3 results bucket. Plus Secrets Manager for the LLM key, read-only
IAM, CloudWatch logs and alarms, and a budget alarm from day one.

**IF THEY ASK…**

*"Why Lambda first?"* — Because it costs nothing while nobody is using it,
which is the honest state of a university project most of the time. The
migration path to containers is a configuration change, not a rewrite, because
the service is stateless and read-only.

---

## Unit 12 — the cloud: the half that only exists while it runs ⭐

`[~55 seconds]`

> **SAY THIS**
>
> "Bottom half, and this is the money-saving idea.
>
> There's an alarm clock. Every night, or every week, it starts the pipeline.
> That job rents a graphics computer at about seventy percent off, reads the
> data, trains, scores, groups, explains, writes the results — and then shuts
> itself down.
>
> Now follow that arrow going up. That's the only connection between the two
> halves. The nightly job *writes* new results into the storage that the website
> *reads*. There is no arrow coming back down. Same boundary as before, drawn in
> cloud services this time.
>
> And when new results land, the website picks them up with no downtime. Nobody
> deploys anything."

**WHAT THIS MEANS**

Scheduled DL plane: EventBridge → spot GPU batch job → publish to
`runs/<id>/` → API reload. Failure raises an SNS alarm. The single upward edge
is the diagram's restatement of the trust boundary.

**IF THEY ASK…**

*"What if the spot machine gets taken away mid-run?"* — The job fails, an alarm
fires, and the website keeps serving yesterday's results, because nothing was
overwritten in place. Every run writes to its own folder, so a half-finished
run cannot corrupt a good one.

---

## Unit 13 — what it costs

`[~60 seconds]`

> **SAY THIS**
>
> "Three levels, real list prices.
>
> Level one, a university demo: website hosting, one small always-on machine, a
> web address, and the training done on your own computer or free Colab. About
> ten dollars a month — and effectively nothing, because standard new-account
> credits cover it.
>
> Level two, a real launch: pay-per-use doorway good for about a million
> requests, storage, a rented graphics machine roughly four hours a week,
> pay-per-use assistant, monitoring. Somewhere between about fifteen and fifty
> dollars a month.
>
> Level three, a growing product: add containers across two data centres, a load
> balancer, a firewall, a nightly graphics machine, team-scale assistant usage.
> Roughly ninety to a hundred and eighty a month.
>
> The reason all three are that cheap is the shape of the thing. The expensive
> hardware exists for two hours and then vanishes. Showing results needs none of
> it."

**WHAT THIS MEANS**

Tier 1 ≈ $10/month at list, $0 inside new-account credits; Tier 2 ≈ $14–55;
Tier 3 ≈ $90–183. US-East list prices, July 2026. The cost story and the
security story are the same architectural decision seen from two angles — say
that if you have ten spare seconds.

**IF THEY ASK…**

*"What is the biggest cost risk?"* — Assistant usage, because it is per-token
and driven by humans rather than by us. That is why the budget alarm is on from
day one, and why the assistant is capped in how many lookups it may make per
question.

---

## Unit 14 — the close

`[~30 seconds]`

> **SAY THIS**
>
> "So: one page, two halves, one line between them.
>
> Above the line we train, and then we stop. Below the line we show people
> things, and we can't change anything. That single decision gives us the
> security property, the cost profile, and the ability to demo this on a laptop
> with no internet — all three from the same choice.
>
> And at the very bottom of the diagram, a person still decides."

---

## Appendix A — the shortest possible version

Four minutes: Unit 0, Unit 2, Unit 7, Unit 12, Unit 14. That is the shape, the
four parallel arms, the boundary, the cloud version of the boundary, and the
close.

## Appendix B — numbers on this page, spoken

| On the page | Say |
|---|---|
| calibrated 0.4434 vs rank 0.0511 | "about nine times better, same models, same data" |
| prevalence 0.065 | "blind guessing gets about six in a hundred" |
| ~2% positives | "about one in fifty is a real case" |
| 254 / 223 alerts | "two hundred and fifty-four, and two hundred and twenty-three" |
| fidelity-insane 38/50 → 1/50 | "used to fail on most of them, now it fails on one" |
| 24/24 goldens | "a twenty-four question exam, all twenty-four have to pass" |
| Tier 1 ≈ $9.50 + $0.55 | "about ten dollars a month" |
| Tier 2 $14–55 | "between about fifteen and fifty dollars" |
| Tier 3 $90–183 | "roughly ninety to a hundred and eighty" |
| spot discount ~70% | "about seventy percent off" |

## Appendix C — the four questions that always come

1. **"Why is the trust boundary a big deal?"** → Unit 7. An attacker on the
   public side cannot alter a score or retrain anything, and in the cloud that
   is enforced by the provider's own permissions rather than by our code.
2. **"Isn't the unsupervised arm dead weight?"** → Unit 2. It is the only arm
   that works with no answer key, and it carries the project's clearest
   deep-learning result.
3. **"Why does calibration matter so much?"** → Unit 3. Measured both ways:
   skip it and the combination collapses to roughly guessing level.
4. **"Could you actually afford to run this?"** → Unit 13. About ten dollars a
   month for the demo, because the expensive hardware exists for two hours a
   night and then disappears.
