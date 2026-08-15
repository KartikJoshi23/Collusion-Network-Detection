# Presentation Q&A — the two dataset questions that get fired hardest

These are the questions an evaluator asks about the datasets, and how to answer
each one **with the Stress Test tab open on screen**, not with theory. Every
number below is the real 5-run measured result, served live by the console.

Open the tab first: **Stress Test** (the lime tab). Have it ready.

---

## Q1. "Your playground has no answer key — so plant the fake cartels right now and show me the output."

**Do it, don't describe it.** This is exactly what the tab is for.

> **SAY THIS**
>
> "Happy to. This is our biggest network — over 163,000 real Georgian
> government contracts — and it has no answer key at all. So here's how we
> test it honestly: I plant fake cartels of known shapes into the real data,
> and we measure how many come back. Watch. I pick how many cases the team can
> review — let's say the top 1%. I hit Plant and Detect… it's scanning all
> 163,000 firms… and here are the results. The bid-together ring: we caught 92%
> of it. Firms taking turns: 7% — it basically escapes. And that's the honest
> headline: we reliably catch cartels whose firms physically bid together, and
> we're blind to ones that just take turns and never appear side by side.
> Knowing exactly which is which is worth far more than one average score."

**If they push — "is that a canned number?"**

> **SAY THIS**
>
> "No — and here's the proof. This command on screen plants fresh, random fake
> cartels into the real network and reproduces these numbers in a few minutes.
> Same protocol, different random cartels every time. I can run it right now if
> you'd like to wait four minutes, or you can run it yourself after."

The command (shown in the tab, copy button included):
```bash
uv run collusiongraph train -c configs/experiment/injection_recovery_ocds_georgia_multiseed.yaml
```

**The tighter-budget beat (very strong, do it if you have 10 seconds):** click
**top 500** first, then **top 2000**. At the tight budget the ring shows 0%; widen
the budget and it jumps to 92%. That shows the numbers are real and
budget-dependent, not a picture.

**The real measured numbers (top 2000 = 1.2% of the network, 5 runs):**

| Planted shape | Recovered | Verdict |
|---|---|---|
| Bid-together ring (clique) | **92% ± 18** | Caught — 4 of 5 runs perfect |
| Hidden common owner | 57% ± 2 | Partly caught |
| Market carve-up | 19% ± 4 | Escapes |
| Take-turns (rotation) | 7% ± 1 | Escapes |
| Cover bidding | 1% ± 1 | Escapes |

**The one-line why-this-matters:** on this data there is no answer key, so the
tree model and everything that needs answers can't even take part — only the
learn-what's-normal models can. This is the clearest thing deep learning does
in the whole project that nothing else could.

---

## Q2. "AMLworld scores below blind guessing — so why keep a dataset you barely use?"

Scroll to the **known-answer bench** panel (bottom of the Stress Test tab) and
answer off it.

> **SAY THIS**
>
> "Fair question, and we answer it honestly. The stress test you just saw only
> means something if the planting method itself is trustworthy. AMLworld is
> where we prove that. It's made-up bank payments where *every* answer is known
> perfectly — 6,357 known-criminal accounts out of half a million. So it's our
> reference standard: we check the whole machine against the truth, we copy its
> eight real laundering shapes into our fake cartels, and it gives us real money
> amounts our other money dataset doesn't have. As for the low score — yes, our
> per-account model scores below guessing on it, and we *report that openly*.
> Its job was never to win a leaderboard. Putting a weak queue on the dashboard
> would mislead, so we don't. A tool that hides its weak spots is the one you
> shouldn't trust."

**The pattern to hammer home for both datasets:**

- **OCDS Georgia** = the no-answer-key **playground** (plant → detect → measure).
- **AMLworld** = the perfect-answer-key **proving ground** (validate the method
  where the truth is known).

They are two halves of one honesty story: you validate the method where you
*can* check it (AMLworld), then apply it where you *can't* (OCDS Georgia). That
is why both are kept and why neither belongs on the ranked-queue screen — the
dashboard shows queues you can check against known answers, and by design these
two don't fit that mould.

**AMLworld facts on the panel (all measured):** 515,088 accounts · 5,078,345
payments with real amounts · 6,357 known-criminal (perfect key) · all 8 real
laundering shapes.

---

## One-sentence answers if you only get a sentence

- **"No answer key, prove it?"** → *"We plant fake cartels of known shapes into
  the real network and measure recovery live — 92% of bid-together rings caught,
  take-turns cartels escape — and the command reproduces it from scratch."*
- **"Why keep AMLworld?"** → *"It's our reference standard: every answer is known,
  so it's where we prove the method is sound before trusting it on data that has
  no answers — and we report its weak score openly rather than hide it."*
