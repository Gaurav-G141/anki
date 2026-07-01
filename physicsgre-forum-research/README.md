# Physics GRE Community Research — What Users Want & Need

Research into the **[physicsgre.com](https://physicsgre.com/) Physics GRE Discussion
Forums** (the largest, most active Physics GRE community) to understand what
prospective applicants want and struggle with — intended to inform the design of a
Physics GRE study app.

## How this was gathered (and its limits)

physicsgre.com sits behind **Cloudflare bot protection** and returns **HTTP 403** to
direct fetching — including via reader proxies (r.jina.ai also hit the CAPTCHA wall).
So **none of the forum's full thread bodies were read directly**. Everything here is
reconstructed from **search-engine-indexed thread titles and snippet excerpts**,
cross-referenced with grephysics.net comment threads, The GradCafe, Physics Forums, and
a few external sources.

Each claim in the detailed files is tagged **[snippet/stated]** (paraphrased from an
indexed excerpt — higher confidence) vs **[title/inferred]** (implied by a thread title
only — lower confidence). Treat specific numbers as "reported on the forum," not verbatim
quotes. Any single in-thread detail should be verified against the live thread before
being treated as definitive.

Roughly **80–90 distinct forum threads/sources** were surfaced across the four research
streams.

## Files

| File                                                   | Focus                                                                                                                                          |
| ------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| [01-study-workflow.md](01-study-workflow.md)           | How users study & prepare — timelines, the practice-test diagnostic loop, pacing, guessing, bubbling, memorization, study groups (~45 sources) |
| [02-resources-and-tools.md](02-resources-and-tools.md) | Books, sites, flashcard decks & apps users use/recommend, and the existing-tooling gaps (~35 sources)                                          |
| [03-pain-points.md](03-pain-points.md)                 | Frustrations & anxieties — material scarcity, time pressure, memorization, plateaus, burnout, test-optional uncertainty (~31 sources)          |
| [04-problems-solutions.md](04-problems-solutions.md)   | How problems & solutions are discussed; criticism of grephysics.net; topic frequency & difficulty (~47 sources)                                |

> Related: the companion folder `physics-gre-solutions/` holds the full scraped
> problem+solution set for all four released exams (GR8677/9277/9677/0177) from
> grephysics.net.

---

## The big picture

The forum's center of gravity is the **four officially released ETS exams** (GR8677,
GR9277, GR9677, GR0177). Almost everything — workflow, discussion, complaints — orbits
this tiny, finite pool of material. The community has independently converged on the same
**practice-test-driven diagnostic loop**: take a test as a diagnostic → review every
missed/guessed problem (usually against grephysics.net) → do weak-area-targeted study →
repeat → save the last test for a timed dress rehearsal ~1 week out.

The PGRE is repeatedly described as **a test of speed, not depth** (~1.7 min/problem).
The biggest score gains are credited to fixing _timing_, not learning more physics.

## Cross-cutting themes (where all four streams agree)

1. **Material scarcity is the #1 problem.** Only ~4 released exams exist (a few more old
   forms). Serious students exhaust everything, plateau, and then _manually reinvent
   spaced repetition_ — taking a "~1-month break to clear memory" so old tests feel fresh.
   Direct snippet: _"it sure would be nice if there were more problems to work through."_
2. **Speed/pacing is the binding constraint.** Repeated reports of not finishing (stopping
   at Q40/Q59, 15 min left) and losing 100+ points to pace, not knowledge. Top scorers
   say practice _fast_, drop anything you can't do in ~1 min, learn elimination tricks.
3. **Existing solutions (grephysics.net) are trusted-but-criticized.** Constant complaints
   that solutions are "confusing," skip algebra ("why does the 1/2 disappear?"), or have
   typos. The community's real value-add is crowdsourced _clearer, alternate, faster_
   explanations — a clear product opening.
4. **Memorization is a felt gap with only ad-hoc tooling.** No formula sheet is allowed;
   students struggle to recall equations/constants. Existing aids (loose flashcards,
   14-page formula PDFs, an incomplete community Anki deck with **poor mobile LaTeX
   rendering**, CWRU cards, memory palaces) are scattered and amateur. Notably, **no forum
   thread endorses Anki/spaced-repetition for the PGRE** — so SRS is an _unmet/inferred_
   opportunity, not a stated demand.
5. **Topic coverage is uneven and weakness-driven.** Users are told not to over-study
   strengths. QM and E&M are the most-cited weak areas; optics, stat-mech, and
   "trivia"/lab-methods recall blindside people. ETS weights: CM 20%, E&M 18%, QM 12%,
   Thermo/Stat 10%, Atomic 10%, Optics 9%, Specialized 9%, Relativity 6%, Lab 6%.
6. **Emotional toll & decision paralysis.** The forum is "a stress reliever at times and a
   massive stress inducer at others." Layered on top: test-optional uncertainty — many
   programs no longer require (or even accept) the PGRE — so users agonize over whether to
   study at all.

## Prioritized design implications for a study app

Ranked by strength + convergence of evidence:

1. **A renewable / large problem bank beyond the 4 exams** — directly kills the #1
   complaint. Must be **vetted** (user-made sets get flagged for unit/answer errors) and
   **calibrated to real PGRE difficulty** (textbooks and CTPG are harder/unrepresentative).
2. **Timed exam mode + untimed study mode on the same item, with per-problem target
   times** and analytics that separate "got it wrong" from "ran out of time." Operationalizes
   the community's two-pass method and the speed-test reality.
3. **Spaced re-exposure of missed problems + spaced-repetition formula/fact decks** with
   first-class mobile equation rendering — automates the manual "memory-clearing break"
   and fills the ad-hoc-flashcards gap. (Anki/SRS = inferred opportunity, strong fit.)
4. **Better solutions than grephysics.net** — correct, fully-stepped (show the skipped
   algebra), with a distinct **"fast path"** field per problem (elimination / limiting
   cases / dimensional analysis / symmetry). This is the clearest differentiator.
5. **Dual-addressable, topic-tagged items** — reachable by (exam, problem #) _and_ by
   topic/subtopic, with a per-topic mastery dashboard that biases practice toward weak
   areas (and over-indexes the painful ones: optics, stat-mech, lab/trivia recall).
6. **Guided, schedule-driven study plan** built around the user's test date and the 4
   exams (which test when), resumable, with a readiness/score-prediction signal.
7. **EV-based guessing coach** (encode "no penalty → always answer"; nudge once choices
   are eliminated) and **realistic exam simulation including bubble mechanics**.
8. **Low-stress, streak-style daily review** (SRS's core selling point vs. cramming);
   avoid leaderboard-style social comparison the forum itself worries about. Optional
   **opt-in cohorts** by test date (they already self-organize on Discord).
9. **Up-to-date per-program requirement tracker** (required / optional / not accepted) to
   resolve the "is it even worth studying?" decision paralysis.

## Caveats

- Snippet-only sourcing: directional and well-corroborated across communities, but not a
  substitute for reading full threads. Verify specifics against live pages.
- Reddit (r/physicsGRE, r/gradadmissions) returned no usable indexed snippets in this
  environment, so its threads aren't individually cited; themes were corroborated
  elsewhere.
- No code in this repository was modified — these are new markdown research notes only.
