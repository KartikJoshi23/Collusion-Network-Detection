# Presentation script — the CollusionGraph console

**Total running time: about 20 minutes** if you speak every block. It is built
in units, so you can drop whole units and the talk still flows. The three you
should never drop are marked ⭐.

**How to read this file.** Every unit has three parts:

- **SAY THIS** — say it out loud, close to word for word. It is written to
  *sound* spoken, not written. Contractions, short sentences, the occasional
  fragment. If you run out of breath, you have added something.
- **WHAT THIS MEANS** — for you, not the audience. What is really happening
  behind that panel, in the project's own vocabulary.
- **IF THEY ASK…** — the questions an evaluator actually asks here, with an
  answer you can give without leaving the screen.

**Before you start.** Run the API and the console:

```bash
uv run collusiongraph serve --port 8001
```

```bash
cd frontend && npm run dev
```

Open the console, pick **Financial · AML**, dataset **elliptic_pp**, and set the
review number to fifty. That is the state every unit below assumes.

**One rule for the whole talk:** never say the word "caught", "guilty" or
"criminal" about anything on screen. The system produces a reason to look. Say
that, and the ethics line at the bottom of the screen backs you up.

---

## Unit 0 — the opening ⭐

`[~45 seconds]`

> **SAY THIS**
>
> "What you're looking at is a screening console. Two very different crimes,
> one system. On the money side it's people moving dirty cash through chains of
> bank accounts. On the contracts side it's companies who are supposed to be
> competing for public work, quietly agreeing who wins.
>
> Those sound unrelated. They're not. Both of them need more than one party, and
> the moment you need more than one party, you leave a shape behind. That shape
> is what this thing looks for.
>
> Everything on this screen is a reason to look at something. None of it is a
> finding of wrongdoing. You'll see that written along the bottom of every
> single screen, and it's there deliberately."

**WHAT THIS MEANS**

You are stating the thesis (§1 of the plan: one graph-learning stack, two
domains) and the ethics boundary in the same breath, before anyone can ask
about either. The footer caveat is rendered from `SCREENING_CAVEAT` in
`frontend/src/api/types.ts` and appears on every view plus every API response —
so if someone tests you on it later, it is not a slide, it is a contract.

**IF THEY ASK…**

*"Why put two crimes in one system? Isn't that a gimmick?"* — It is the
research question. If coordination really does leave the same geometric trace
in both worlds, one detector should transfer across them. We tested it in both
directions and published both answers, including the direction that failed.

---

## Unit 1 — the domain switch

`[~40 seconds]`

> **SAY THIS**
>
> "Top right — this switch is the whole two-worlds idea in one control.
>
> Left side, Financial. Underneath it says A-M-L, anti money laundering. Right
> side, Procurement, and underneath, bid rigging. We name the crime, because
> 'financial' on its own tells a visitor nothing.
>
> Watch what happens when I flip it. The colours change, the datasets change,
> the alerts change. What doesn't change is anything underneath. Same reader of
> the data, same scoring, same grouping, same evidence rules. The switch is
> genuinely just a filter over one system."

**WHAT THIS MEANS**

`DomainToggle.tsx` sets `data-domain` on `<html>`, which swaps the accent ramp
(cyan→teal for financial, violet→magenta for procurement), and clears the
dataset + selection so nothing leaks across. The sub-labels "AML" and "bid
rigging" were added on 2026-07-25 after an audit found the letters AML appeared
nowhere on the console except two buried About lines.

**IF THEY ASK…**

*"So it's the same model for both?"* — Same architecture and same pipeline, but
each domain trains its own weights on its own data. What is shared is the
schema, the splitting rules, the grouping, the evidence layer, and the
evaluation protocol. That is what makes the cross-domain transfer experiment
meaningful at all.

---

## Unit 2 — the dataset picker

`[~40 seconds]`

> **SAY THIS**
>
> "Next to it, the dataset. There are two on each side, and they're all real
> public data — nothing here is invented.
>
> On the money side: Bitcoin payments, and then the same Bitcoin world seen as
> wallets instead of individual payments. That second one matters, because it's
> the same crime at a different zoom level, and the system has to cope with
> both.
>
> On the contracts side: European public contracts, and an international
> auctions dataset where the cartels were confirmed by competition authorities.
> That second one is our hardest test, because somebody official already knows
> the answer."

**WHAT THIS MEANS**

Four served datasets — `elliptic_pp`, `elliptic_pp_actor`, `mendeley_eu`,
`garcia_rodriguez` — each needing a real trained scoring run before it appears
in `serving.json`. The project handles six datasets in total; the other two
(AMLworld and the Georgian contract corpus) are used for the planted-cartel
studies, which need no labels and therefore produce no queue.

**IF THEY ASK…**

*"Why aren't all six on screen?"* — Two of them have no usable answer key at
the level we serve alerts. AMLworld's ground truth is per-payment, not per
account, and the Georgian corpus has no cartel labels at all. Both are used
where they are honest — the planted-cartel experiments — and a queue built from
them would imply a confirmation rate we cannot measure. Section
"Why the dashboard shows four datasets and not six" in the report has the full
reasoning.

---

## Unit 3 — Overview: the four tiles ⭐

`[~60 seconds]`

> **SAY THIS**
>
> "First screen. Four numbers across the top, and they're deliberately the four
> a manager asks first.
>
> How many groups were flagged in this dataset. How many of those are in the
> top risk band. How many cases you've said your team can actually review this
> week. And how many datasets are loaded on this side.
>
> Look at the third one, because it's the one people skip. This system does not
> hand you a pile of work and wish you luck. You tell it what your team can
> get through, and every number on the screen is then measured at exactly that
> workload. A screening tool without a workload number attached to it is
> meaningless — you can catch everything if you're willing to review
> everything."

**WHAT THIS MEANS**

The four KPI tiles in `Overview.tsx`, each on its own hue (cyan / coral / amber
/ violet — the multi-hue rule from the V2 brief). "Cases to review" is *k*. Its
prominence is the argument for Precision@k as the project's headline metric
rather than accuracy or AUC.

**IF THEY ASK…**

*"Why is the review number a human input and not something the model picks?"* —
Because it is not a modelling quantity, it is a staffing quantity. The right
value depends on how many analysts you have this week. What the system owes you
is an honest measurement *at whatever number you choose*, which is exactly what
the next screen gives you.

---

## Unit 4 — Overview: the constellation

`[~45 seconds]`

> **SAY THIS**
>
> "The big panel is every alert in one picture. One dot per group. Bigger dot
> means more members. Colour is the risk band.
>
> Be honest about what this is: the *arrangement* of the dots is decorative, but
> the dots themselves aren't. Every single one is a real group, at its real
> rank, with its real score. And you can click straight into any of them.
>
> What I want you to notice is the shape of the crowd. A handful of hot ones at
> the top, and a long, quiet tail. That's what a real screening problem looks
> like, and it's the reason the review number matters so much."

**WHAT THIS MEANS**

`Constellation.tsx` renders the top sixty alerts from the live `/alerts`
response. Saying "the layout is decorative, the ranking is real" out loud is
the honest framing, and it pre-empts an evaluator deciding for themselves that
the whole panel is eye candy.

**IF THEY ASK…**

*"Is the position of a dot meaningful?"* — No, and I'd rather say so. Position
is a layout choice. Size and colour and the ability to click through are all
real. If you want the exact ordering, the next tab is the ordering.

---

## Unit 5 — Overview: the leaderboard, and the transition

`[~30 seconds]`

> **SAY THIS**
>
> "On the right, the same thing as a plain list. Rank, risk, how many members,
> and the name of the pattern if we could put a name to it.
>
> This is the shortest useful summary in the product. If you had ten seconds
> and one screen, it'd be this one. Let me click into the full worklist."

**WHAT THIS MEANS**

The transition into the Alert Queue. The list rows carry the same `MotifGlyph`
symbols used everywhere else, so the visual vocabulary is already familiar by
the time you reach the queue.

---

## Unit 6 — Alert Queue: what the list is ⭐

`[~55 seconds]`

> **SAY THIS**
>
> "This is the screen an investigator actually lives in. It's a worklist,
> ordered worst first.
>
> Two things to know before we read a row. First, a row is not a person and not
> a payment. It's a *group* — a cluster of accounts that deal with each other
> far more than they deal with anyone else. We score the individual accounts,
> then we roll them up into groups, because a person can investigate one ring.
> Nobody can investigate sixty-seven thousand separate accounts.
>
> Second, near-identical groups get merged, so you never open the same case
> twice with two different reference numbers."

**WHAT THIS MEANS**

Community roll-up: node scores → Leiden partition → per-community aggregate →
overlap suppression at a Jaccard threshold of one half → ranked queue. The
Elliptic payments run produces 318 communities and publishes 254 alerts, with
64 excluded as oversized (over 100 members). Those exact figures are in
`eval_outputs/elliptic_pp/alert_queue_ensemble/queue_summary.json`.

**IF THEY ASK…**

*"How do you form the groups?"* — A community-detection algorithm called
Leiden, run on the test-window network. It finds clusters that are far more
connected inside than outside. We then cap group size and remove heavy
overlaps. Nothing about the grouping uses the labels, which is what keeps it
usable on data where no answer key exists.

---

## Unit 7 — Alert Queue: the review slider ⭐

`[~75 seconds]`

> **SAY THIS**
>
> "This slider is the most honest control in the whole system, so let me spend a
> moment on it.
>
> It asks one question: how many cases can your team actually get through? Say
> it's fifty. I drag it to fifty — and now watch this number just to the right
> of it.
>
> That's telling me that out of those fifty, about a third turn out to be real.
> Sixteen of the fifty, to be exact. That's not a promise and it's not a
> forecast — it's measured, on cases where somebody already knew the answer.
>
> Now watch what happens when I get greedy. I drag it up to a hundred… and it
> falls to about a quarter. Two hundred, and it's down to roughly one in seven.
>
> That's not the system getting worse. That's what happens to every screening
> system on earth when you dig deeper into the list. The good stuff is at the
> top. Being able to show you exactly how fast it decays is the point."

**WHAT THIS MEANS**

The readout is `PrecisionReadout` in `AlertQueue.tsx`. It never interpolates:
it snaps to the nearest *published* breakpoint at or below the slider value, so
the figure on screen is always one that exists in a stored result file. The
Elliptic payments queue publishes three: sixteen of fifty, twenty-three of a
hundred, twenty-seven of two hundred.

**IF THEY ASK…**

*"A third seems low."* — Two answers, and both matter. First, blind guessing on
this data scores about six in a hundred, so a third is roughly five times
better than chance at the same workload. Second — and this is the bigger point
— about three quarters of this dataset has **no recorded answer either way**.
A group we could not confirm is not the same thing as a group we got wrong.
Every precision figure we publish is therefore a floor, not a ceiling.

*"Why does it jump instead of moving smoothly?"* — Because it refuses to make a
number up. It only ever shows review sizes the evaluation actually measured.

---

## Unit 8 — Alert Queue: showing an ordinary case ⭐

`[~60 seconds]`

> **SAY THIS**
>
> "Here's the question I'd ask if I were sitting where you are. 'Fine — you've
> shown me the suspicious ones. Show me one it did *not* flag.'
>
> These four buttons do exactly that. All, High risk, Medium, and Low or
> normal. And each one carries its own count, so you can see the shape of the
> queue before you click.
>
> Look at this: on the Bitcoin payments data, of the two hundred and
> fifty-four groups, nearly a hundred and fifty of them are rated ordinary. I'll
> click Low. There they are. Same scoring, same everything — the system simply
> doesn't think they're worth your morning.
>
> I'll be straight with you about one thing. Flip to the European contracts
> dataset and this Low button is empty and greyed out. That is not the system
> failing. That dataset is a research sample where roughly four in every ten
> entries are cartel cases by design, so there genuinely aren't many ordinary
> firms in it to show you."

**WHAT THIS MEANS**

The band filter fetches the whole queue (the API's 500 cap) so the counts are
true totals rather than "whatever fell inside the review number". 148 of 254
Elliptic payment groups score below 0.2. Mendeley's Low band is genuinely
empty — all 223 groups score high — because its case-control construction is
about 42% cartel.

**IF THEY ASK…**

*"Isn't an empty band a bug?"* — It was the first thing I checked. It follows
from how that dataset was assembled: it is a matched study sample, not a
population sample. For the contrast case, look at the Bitcoin payments queue,
where more than half the groups are ordinary.

---

## Unit 9 — Alert Queue: reading one row

`[~75 seconds]`

> **SAY THIS**
>
> "Left to right across a row.
>
> Rank. Then the risk score — and that number is a real probability, not a
> made-up number between zero and one. We put every model's output onto a proper
> scale before we ever compare or combine them, and I'll show you what happens
> when you skip that step.
>
> Then the pattern, if we could name one. There are nine named patterns and
> they come from the international standards bodies — the money-laundering ones
> from F-A-T-F, the contract ones from the O-E-C-D. We only put a name on it
> when we can actually prove the shape. No name is an honest answer, not a
> blank.
>
> Then how many official warning signs matched. Then the size of the group.
>
> Then this little chart — that's activity over time. If it's flat, everything
> happened in one window, which is common in the Bitcoin data. If it wiggles,
> the activity is genuinely spread out.
>
> Then when it happened, and the reference number."

**WHAT THIS MEANS**

Columns: rank, `RiskChip` (calibrated probability), `MotifChip`, `FlagBadge`
(red-flag count from the bundle), member count, `ActivitySparkline` (drawn from
the real windowed subgraph edge timestamps — never synthesised), time window,
alert id. The sparkline loads eagerly for every row; a single-window subgraph
draws a flat baseline rather than a gap so the column reads consistently.

**IF THEY ASK…**

*"What does 'calibrated' actually buy you?"* — Comparability. Two models can
both be good at ranking and still be on completely different scales. Combine
them raw and the loud one drowns the quiet one. We measured that failure: put
on a proper scale first, the combination scores about four and a half times
better than combining the raw outputs.

---

## Unit 10 — Alert Queue: the hover actions

`[~25 seconds]`

> **SAY THIS**
>
> "Hover any row and three shortcuts appear on the right. Show me the network.
> Show me the case file. Or ask the assistant about this one specifically.
>
> That last one carries the case across with it, so you're not retyping a
> reference number into a chat box."

**WHAT THIS MEANS**

`askCopilotAbout(alertId)` sets `copilotSeed` in the console store, which the
dock renders as a context chip and passes to the backend as the seed for the
turn.

---

## Unit 11 — Graph Explorer: the picture ⭐

`[~60 seconds]`

> **SAY THIS**
>
> "Now the picture. This is the group from that row, drawn out.
>
> The coral dots are the flagged members. Coral means one thing in this whole
> product and only one thing — flagged — so it's never used for decoration
> anywhere else. The grey dots around them are context: neighbours we drew in so
> the group makes sense rather than floating in space.
>
> Bottom left tells you how much you're looking at. And if a group is too big to
> draw honestly, we say so on screen rather than quietly showing you a slice and
> letting you assume that's everything.
>
> This is the moment a lot of people get it. You can *see* the coordination.
> That's the entire argument of the project in one picture — coordination has a
> geometry, and the geometry is visible."

**WHAT THIS MEANS**

Sigma.js renderer over a graphology graph. Members on an inner ring whose
radius scales with member count, context on an outer ring; node size and label
density thin out above forty nodes. Subgraphs are windowed **server-side** — the
browser never receives the full network.

**IF THEY ASK…**

*"Is this the whole network?"* — No, and it says so when it isn't. It is the
alert's members plus one hop of context, windowed to the alert's own time
range on the server. A million-line network in a browser would be unreadable
and slow, and cropping it silently would be dishonest.

---

## Unit 12 — Graph Explorer: the replay

`[~50 seconds]`

> **SAY THIS**
>
> "And you can replay it. Press play and the connections light up in the order
> they happened, so you watch the thing assemble itself.
>
> Read the label on the button, because it's doing something careful. Sometimes
> it says replay *flow*, and that means the connections carry genuinely
> different dates and you're watching real time pass. Sometimes it says replay
> *order*, and that means every connection in this group happened in the same
> window, so what you're watching is sequence, not time.
>
> We found that the hard way. In the Bitcoin data, the top case has a hundred
> and one connections that all sit at the exact same moment. The old replay
> animated by date, so with every date identical, nothing moved and it looked
> broken. We could have faked a spread of dates. We detect it and say which mode
> you're in instead."

**WHAT THIS MEANS**

Per-edge reveal time `rt ∈ [0,1]`: computed from timestamps when they vary,
from sequence index when they do not. The readout switches between
"full window 2014–2018" and "all edges · window 38" accordingly. This was a
real bug found in the 2026-07-20 dashboard audit.

**IF THEY ASK…**

*"Why not just interpolate dates so it always animates nicely?"* — Because that
invents data. The animation would look better and mean less. Making the failure
mode visible is worth more than making the demo smooth.

---

## Unit 13 — Case Detail: the header

`[~40 seconds]`

> **SAY THIS**
>
> "This is the case file — where somebody actually decides.
>
> Top line reads like a sentence, on purpose: which case, which dataset, and
> which model scored it. Underneath in small grey type is the machine
> reference. That's what the software, the export and the assistant all use.
> It's there when you need it, and out of the way when you don't.
>
> And the score. More than nine tenths on this one, which is about as high as
> this system goes."

**WHAT THIS MEANS**

`decodeAlertId()` turns `elliptic_pp:gatv2_multi_s0:16` into "Case 16 · Bitcoin
payments · scored by the GATv2 attention network (attempt 0)". The raw id is
never discarded — it stays as a subtitle and copy target.

---

## Unit 14 — Case Detail: the pattern, including when there isn't one ⭐

`[~75 seconds]`

> **SAY THIS**
>
> "First panel: the pattern we detected, drawn as a diagram, and it draws itself
> as the panel opens.
>
> Now — this particular case is the interesting one, and it's the one I'd
> choose to show you even though it makes life harder for me. There's no named
> pattern here. It doesn't match any of the nine textbook shapes.
>
> That used to leave the screen looking empty on exactly the cases you most need
> to justify. A big score, and two blanks under it. So now we write out what
> actually happened, in plain words.
>
> Read it: eighty-five bank accounts. Eighty-four connections between them. That
> ratio means it's a chain, not a web — money went in one end and travelled
> account to account to account. And every bit of it happened in a single
> window of time.
>
> That's a describable situation. It doesn't need a textbook name to be worth
> twenty minutes of somebody's morning."

**WHAT THIS MEANS**

`plainReason.ts` renders measured bundle facts as sentences and returns `null`
rather than guessing when facts are absent. 85 members with 84 internal links
is a tree — no cycles — which is what licenses the "chain" wording. The panel
also shows the few connections the explainer kept, the strongest single
connection, and the group size.

**IF THEY ASK…**

*"So the model flagged something it can't explain?"* — It flagged something the
*matcher* can't name. Those are different. The matcher is a set of hand-written
rules that only fire when they can formally prove a shape, and it deliberately
never guesses. The learned evidence is still there — it's the panel you're
reading — and the honest summary is "we can describe this, we cannot name it".

---

## Unit 15 — Case Detail: the official warning signs

`[~50 seconds]`

> **SAY THIS**
>
> "Second panel: the official warning signs.
>
> When a case matches one, you don't get our opinion. You get the actual
> indicator, quoted, with the standards body it came from stamped on it — F-A-T-F
> for money, O-E-C-D for contracts — and underneath, why it matched *here*.
>
> That's on purpose, and it's the part I'd defend hardest. An investigator can
> throw out everything the neural network says and this evidence still stands,
> because it's a rule anyone can check by hand. On this particular case there
> are none, and rather than show you a blank box we tell you plainly what did
> make it stand out."

**WHAT THIS MEANS**

Red flags are produced by the rule-based matcher, not the learned model. Every
one carries `indicator`, `source` and the fields that caused the match. When
the list is empty the card falls through to `plainReason` rather than printing
"no citations" and stopping.

**IF THEY ASK…**

*"Could the model have made the warning sign up?"* — No. It has no route to.
The matcher is deterministic hand-written graph rules over the alert's
neighbourhood, and the indicator text is quoted from a fixed reference file.
The learned model never touches that panel.

---

## Unit 16 — Case Detail: the evidence

`[~45 seconds]`

> **SAY THIS**
>
> "Third panel: the facts themselves. How many are in the group. How many
> connections between them. When it happened. Amounts and fees where the
> dataset actually records them.
>
> And each fact is tagged with where it came from. That matters more than it
> sounds. If a fact is missing here, it's genuinely missing — we don't fill in a
> guess and we don't quietly average something in. On a dataset without amounts,
> the amounts row simply isn't there."

**WHAT THIS MEANS**

`evidence_sources` labels each field with its origin. The design rule is §4.3:
schema fields absent from a dataset stay absent rather than being imputed —
which is also why the report's data-cleaning section says explicitly that
nothing was imputed or dropped.

---

## Unit 17 — Case Detail: how solid is this ⭐

`[~60 seconds]`

> **SAY THIS**
>
> "Fourth panel, and this is my favourite thing in the product, because it's the
> system marking its own homework in public.
>
> Two questions, in plain English. 'Is this evidence enough on its own?' and
> 'if we take this evidence away, does the warning go away?'
>
> Here's how we get those. We run the case twice more. Once showing the computer
> *only* the handful of connections it said mattered — if the warning still
> comes out, that evidence really was sufficient. Then once with those
> connections *removed* — if the warning disappears, they really were necessary.
>
> Yes or no. For a single case there's no in-between, and pretending otherwise
> with a decimal point would be false precision. And when the two answers
> contradict each other, we put a warning on the panel rather than hide it."

**WHAT THIS MEANS**

Sufficiency and necessity, from the explainer's fidelity pair. For a single
alert PyG compares *hard* predictions, so both are 0/1 verdicts — printing
"0.000" was unreadable and, worse, ambiguous, since fidelity− = 0 is the best
value while fidelity+ = 0 is the worst. `fidelity_sane === false` raises the
amber warning strip.

**IF THEY ASK…**

*"How often does that check fail?"* — It used to fail on 38 of our 50 published
Bitcoin explanations. We replaced the explainer with a better one and it now
fails on one. That number is in the report, and we kept the old one written
down rather than quietly improving the figure.

---

## Unit 18 — Case Detail: nothing is hidden

`[~30 seconds]`

> **SAY THIS**
>
> "At the bottom, one collapsed section: every raw value behind this case, for
> whoever wants to argue with it. And an export button that hands you the whole
> file.
>
> The rule we set ourselves is that the pretty version never has less in it than
> the raw version. If the case file carries a field we don't have a nice panel
> for, it still shows up down here."

**WHAT THIS MEANS**

`KNOWN` in `CaseDetail.tsx` lists the recognised keys; anything else falls
through to the technical appendix and the export by construction, so a new
bundle field can never be silently swallowed.

---

## Unit 19 — Case Detail: the case with no file

`[~45 seconds]`

> **SAY THIS**
>
> "Let me deliberately open a quiet one, from further down the list. Watch what
> you get.
>
> Not an error. It says: this group looks ordinary, so the system didn't think
> it was worth anyone's time and didn't write up a file. And it says that's the
> right outcome.
>
> You still get the score, the size, the time window, and you can still go and
> stare at the network yourself. The reason full write-ups stop partway down the
> list is simply that producing them costs real computing time, and spending it
> on cases nobody will read is waste."

**WHAT THIS MEANS**

`NoBundlePanel`. A missing bundle is the designed outcome below the explanation
budget, not a failure — showing a red error there told reviewers the system was
broken when it was working correctly. It became reachable the moment the queue
gained a Low band.

---

## Unit 20 — Model Lab: the headline number ⭐

`[~60 seconds]`

> **SAY THIS**
>
> "This screen is where the claims live, and every number on it comes out of a
> stored result file. Nothing on this page is worked out in the browser.
>
> The big number at the top is the overall score. Now, on its own, that number
> is meaningless — and this is the thing most people get wrong when they read
> results. So directly underneath it we print what *blind guessing* would have
> scored on this exact data, and then the ratio between them.
>
> That's the honest form of every result in this project. Never a score on its
> own. Always a score next to what doing nothing clever would have got you."

**WHAT THIS MEANS**

`HeadlineBlock` prints AUC-PR, the prevalence baseline, and the ratio. On
Elliptic payments the guessing level is 0.065; on Mendeley firms it is 0.358 —
which is why a 0.39 on Mendeley is a far weaker result than a 0.47 on Elliptic,
and why quoting either alone would mislead.

**IF THEY ASK…**

*"Why not accuracy?"* — Because on this data you can score ninety-eight percent
accurate by saying "innocent" to everything, and be perfectly useless. The
report has a whole section on that, including the four outcomes — true and
false positives and negatives — and what each one costs a real team.

---

## Unit 21 — Model Lab: the workload table

`[~45 seconds]`

> **SAY THIS**
>
> "Underneath, the same run broken down by workload. Read one row. If you
> review this many cases, this share of them turn out to be real. This is how
> much of the total you'd have found. And this is your false alarm rate.
>
> Three rows, three different staffing levels. This is the table you'd actually
> take to whoever signs off the headcount, because it turns a research score
> into a staffing decision."

**WHAT THIS MEANS**

Precision, recall and FPR at each published budget. Only measured breakpoints
are listed — the table never interpolates.

---

## Unit 22 — Model Lab: the three charts

`[~75 seconds]`

> **SAY THIS**
>
> "Three charts, and every one of them exports as an image, because these are
> the same figures that go in the write-up. No retyping, no drift between what's
> on screen and what's in the paper.
>
> First: how well it scored, period by period, with the guessing line dashed
> behind it. Look at the collapse after period forty-three. That is real, it's a
> known event in this dataset — a large market shut down and the behaviour
> changed underneath the model. We could have cropped the chart at forty-three.
> Showing it is the finding.
>
> Second: how many of your top picks are real, drawn against workload, with a
> marker at wherever you left the slider.
>
> Third: the same thing at group level, after merging near-duplicates. And read
> the note under it. It's the warning that governs this whole screen. A case we
> couldn't confirm is not the same as a case we got wrong."

**WHAT THIS MEANS**

`StepBarChart` (per-time-step AUC-PR vs prevalence) and two `AtKChart`s
(node-level precision@k, alert-level queue precision) with the live budget
marker. SVG and PNG export at print scale. The step-43 collapse is the dark
market shutdown in the Elliptic data and is one of the project's temporal-shift
findings.

**IF THEY ASK…**

*"Doesn't that collapse invalidate your results?"* — It constrains them, and we
say so. It is why the model is tested strictly forward in time, why we report
per-period rather than one blended average, and why the report warns that our
validation scores are not a trustworthy guide under that kind of shift.

---

## Unit 23 — Model Lab: can you trust these numbers ⭐

`[~90 seconds]`

> **SAY THIS**
>
> "Last section on this screen, and it's collapsed by default because it's the
> follow-up question, not the opening one. 'Can I trust any of this?'
>
> Four answers.
>
> One. Every headline model was built five separate times with different
> starting randomness, and we report the average *and* the spread. If a result
> only shows up on one of the five, we'd rather find that out ourselves than
> have you find it.
>
> Two. When we say one method beats another, we re-ran that comparison a couple
> of thousand times on reshuffled data, and we show you the range the gap landed
> in. If that range crosses zero, we don't get to call it a win.
>
> Three. These grids are the hardest test in the project. Take one country out
> completely, train without it, then test on it. Every country takes a turn.
> And you can see it right there in the numbers. On the auctions data it works
> everywhere. On the European data it depends on the country — and the biggest
> country actually fails. We publish that, because an average that hides a
> failure is a misleading average.
>
> Four. We deliberately corrupted some of the training answers to see what
> breaks. The test answers were never touched."

**WHAT THIS MEANS**

`RigorSection`: multi-seed table (mean, std, min…max), paired-bootstrap
significance with CIs, the LOCO and LOMO transfer matrices with per-fold lift,
the label-noise curve, cross-domain label efficiency and the protocol
sensitivity sweep. Every value is copied from a published artifact; nothing is
computed client-side.

**IF THEY ASK…**

*"Which country fails, and why?"* — The largest one in the Mendeley pool, at
0.90 lift — worse than guessing there. Macro-averaged the matrix reads 1.17,
which is why we publish the per-fold rows rather than the average alone. The
García market matrix is uniformly positive at 1.57, and Italy's top ten are all
correct — so the honest summary is "market-dependent on one dataset, robust on
the other".

---

## Unit 24 — About

`[~55 seconds]`

> **SAY THIS**
>
> "The About screen is the argument in one page, and it's the one I'd leave up
> if we ran out of time.
>
> Two ledgers, one structure. Then the nine patterns, laid out with a diagram
> each — four money ones, four contract ones, and one that sits in both worlds:
> hidden common ownership. Those aren't ours. They're curated from the
> international standards bodies, and our detector recovers all nine of them at
> full recall when we plant them ourselves.
>
> Then four steps: read the data, learn, rank, explain.
>
> And at the bottom, the boundary. This produces screening signals for human
> investigators. Inputs to due process — never a substitute for it."

**WHAT THIS MEANS**

The nine motif families, `MotifGlyph` diagrams drawing themselves on scroll,
the four-stage pipeline, the leakage paragraph in four plain sentences, and the
scope-boundary panel. The 100% recall claim is the §9.1 flagship test: matcher
and injector are independent implementations, so they cross-validate each
other.

---

## Unit 25 — the Copilot ⭐

`[~2 minutes]`

> **SAY THIS**
>
> "Last thing, and it's the one people want to poke at. There's an assistant,
> and you can open it on any screen.
>
> Let me ask it something ordinary first. *[Type: "which five alerts should I
> look at first and why?"]*
>
> Watch the panel while it thinks. That trace is real — those are the actual
> lookups it's making, live. It cannot answer from memory. It has to go and read
> the published results, and you can expand every single lookup it made and see
> exactly what came back.
>
> Now the badges. Every number in that answer had to appear literally in
> something it looked up. If one didn't, it tells you. And if it talks about
> warning signs without consulting the reference library, it tells you that too.
>
> Now let me try to break it. *[Type: "is firm X guilty?"]*
>
> There. 'This system does not determine guilt.' It won't answer that question.
> And that isn't a filter bolted on the front. It's checked on the way out, on
> every single response.
>
> One more. *[Type: "what will the score be in 2027?"]* It refuses, and it lists
> what it actually has instead of inventing something.
>
> Before any release, it sits a twenty-four question exam covering exactly these
> failure modes. All twenty-four have to pass."

**WHAT THIS MEANS**

The dock streams SSE trace events as tools fire, then a final payload carrying
`confidence`, `numbers_grounded`, `corpus_grounded`, `guard_rewrites`, evidence
and the caveat — all copied from the backend, never re-derived in the browser.
The guards are §4.6: read-only SQL, numeric grounding, corpus grounding, the
guilt-language rewriter, and a degenerate-output gate that withholds token soup
at confidence zero. The golden gate is 24/24.

**IF THEY ASK…**

*"What model is behind it?"* — An NVIDIA NIM-hosted LLM. But the important
answer is what it is *allowed* to do: read-only queries against published
results, with every number checked against the evidence it retrieved. Swap the
model and the guarantees are unchanged, because they are enforced outside the
model.

*"What if there's no key on this machine?"* — It says so, plainly, instead of
pretending. Everything else on the console works without it.

---

## Unit 26 — the close

`[~40 seconds]`

> **SAY THIS**
>
> "One last thing, and then I'll stop.
>
> That line along the bottom has been on every screen for the last twenty
> minutes, and it's on every response the system sends, not just the pretty
> pages. Screening signals for human investigators. Not determinations of
> wrongdoing.
>
> That's not a disclaimer we added at the end to be safe. It's the reason the
> assistant refuses certain questions. It's why the case files show you their
> own weaknesses. And it's why we publish the country where it fails, right
> next to the ones where it works.
>
> A tool that decides who is guilty would be a different project, and a much
> worse one. This one shortens the list a person has to read. Happy to take
> questions."

**WHAT THIS MEANS**

Close on the ethics boundary as a design driver rather than a legal shield.
Every claim in this block is checkable on screen within ten seconds, which is
why it is the right note to end on.

---

## Appendix A — the shortest possible version

If you are given five minutes: Unit 0, Unit 7, Unit 8, Unit 11, Unit 14,
Unit 25, Unit 26. That is the thesis, the honest metric, the ordinary case, the
picture, the explanation, the guardrails, and the boundary.

## Appendix B — spoken numbers, so you never read a decimal aloud

| On screen | Say |
|---|---|
| P@50 = 0.32 (16 hits) | "about a third — sixteen of the fifty" |
| P@100 = 0.23 | "about a quarter" |
| P@200 = 0.135 | "roughly one in seven" |
| prevalence 0.065 | "blind guessing scores about six in a hundred" |
| 148 of 254 below 0.2 | "nearly a hundred and fifty of the two hundred and fifty-four" |
| Mendeley P@4 = 0.50 | "two of the top four" |
| Mendeley P@18 = 0.333 | "a third of the top eighteen" |
| García Italy, 3 alerts | "three cases, and all three are confirmed cartels" |
| Elliptic wallets P@50 = 0.08 | "about four in fifty — much thinner, and we say so" |
| risk_score 0.9265 | "more than nine tenths" |
| 77% unlabelled | "about three quarters has no recorded answer either way" |
| macro lift 1.57 / 1.17 | "about half again better" / "a little better than guessing" |
| failing fold 0.90 | "actually worse than guessing there" |

## Appendix C — the five questions that have actually been asked

1. **"Show me one it didn't flag."** → Unit 8. Low band, Bitcoin payments.
2. **"Why is precision so low?"** → Unit 7. Guessing level, plus three quarters
   of the data has no recorded answer, so every figure is a floor.
3. **"Your XGBoost beats your neural network — so why the deep learning?"** →
   Not a dashboard question, but it comes here anyway. Answer: on that one
   dataset, yes, and we publish it. The trees cannot enter the planted-cartel
   experiments at all, because there is no answer key there — and that is the
   experiment closest to real deployment. Deep learning scores about nine in
   ten on the clique-type cartels there; the non-learning floor scores about
   one in eight.
4. **"Could an investigator be misled by this?"** → Unit 17 and Unit 26. The
   case file shows its own weaknesses, the assistant refuses guilt questions,
   and every screen carries the boundary.
5. **"Is any of this live data?"** → No. Published public datasets, scored
   offline, served read-only. The serving side physically cannot retrain or
   change a score — that is the trust boundary in the architecture talk.
