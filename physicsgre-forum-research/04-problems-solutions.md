# PhysicsGRE.com Forum Research — Problems, Solutions & Discussion

**Focus boards:** "Problems, Solutions, and Discussion" ([f=19](https://physicsgre.com/viewforum.php?f=19)) and "Registration and Test Preparation" ([f=18](https://physicsgre.com/viewforum.php?f=18)).
**Method:** ~22 distinct WebSearch queries (direct fetching blocked by Cloudflare 403). Findings are built from search-result titles + snippets, cross-referenced with grephysics.net answer-page comment threads and a few external corroborating sources. Each finding is tagged **[stated-in-snippet]** when the snippet text directly asserts it, or **[inferred-from-title]** when drawn from a thread title / URL pattern only.

---

## Summary

The PhysicsGRE.com community is organized almost entirely around the **four officially released ETS exams** — GR8677 (1986), GR9277 (1992), GR9677 (1996), GR0177 (2001) — plus a small amount of user-generated practice material. The dominant pattern is **per-problem discussion**: students post "GR8677 #6", "GR9277 #50" style threads asking for help on a single numbered problem, and experienced members reply with alternate or faster solutions. The community's de-facto canonical solution set is **grephysics.net** (Yosun Chang's "GREPhysics.NET: Full Solutions to ALL GRE Physics Exam Problems"), and a huge fraction of the discussion is people saying grephysics solutions are **confusing, incomplete, or contain typos**, then crowdsourcing better explanations in the comments.

Three needs surface repeatedly and map directly onto a practice-problem study app:

1. **More problems than the 4 released exams exist** — students explicitly run out of official material and ask "what else can I drill?"
2. **Better/clearer solutions** — the existing canonical solutions (grephysics.net) are frequently criticized; users want multiple solution approaches, especially fast "GRE-style" tricks (limiting cases, dimensional analysis, elimination).
3. **Speed and timing** — the test is widely described as a speed test (100 problems / 170 min); the recurring ask is to drill _fast_ solving and answer-elimination, not rigorous derivation.

---

## Theme 1 — Discussion is structured per-problem, by exam + problem number

The forum's natural unit is a single numbered problem from one of the four exams. This is the single strongest structural signal for app design (problems should be addressable as exam+number).

- **[stated-in-snippet]** Dedicated single-problem threads are common, e.g. "GR8677 #6", "Problem 26, GR8677", "GR8677 #2 (Classical Mechanics Problem)", "(GR8677#98) solution?", "gr9277 #6 (edited post)", "GR9277 #50". ([GR8677 #6](https://physicsgre.com/viewtopic.php?t=111); [Problem 26, GR8677](https://physicsgre.com/viewtopic.php?t=4014); [GR8677 #2](https://physicsgre.com/viewtopic.php?t=4009); [GR8677 #98](https://physicsgre.com/viewtopic.php?t=101); [gr9277 #6](https://physicsgre.com/viewtopic.php?t=4164); [GR9277 #50](https://physicsgre.com/viewtopic.php?t=5169))
- **[stated-in-snippet]** A community-maintained master index thread, "Questions/Answers GR0177 - GR9677 - GR9277 - GR8677," is kept up to date by members and links problem discussions across all four exams; it is associated with Yosun Chang (grephysics.net creator) and references a lesson plan spanning E&M, Mechanics, Stat Mech, QM, Special Relativity, Optics, and Condensed Matter. ([t=109](https://physicsgre.com/viewtopic.php?t=109))
- **[stated-in-snippet]** A University of Minnesota physics wiki mirrors this exact structure, organizing discussions by "Test 1 (GR9277), Test 2 (GR8677), Test 3 (GR9677), Test 4 (GR0177)." ([UMN physgre wiki](https://zzz.physics.umn.edu/groups/physgre/home))
- **[inferred-from-title]** The f=19 board also hosts topic-named (not number-named) threads: "Moment of Inertia!!", "Electromagnetic induction and magnet shapes. Help!", "Angular momentum question...", "Interesting Probability sum!", "a statics problem", "List of important problems in University Physics." ([f=19 index](https://physicsgre.com/viewforum.php?f=19))

**Implication:** Students think in terms of (exam, problem #) AND in terms of physics topic. An app should support both addressing schemes.

---

## Theme 2 — grephysics.net solutions are the default, but heavily criticized as unclear/incomplete

This is the most actionable finding for a "better solutions" product. grephysics.net is universally used but its solutions draw constant complaints, and the _community fills the gaps in the comment threads_ — exactly the value a curated app could capture.

Direct user complaints about clarity (grephysics.net comment threads):

- **[stated-in-snippet]** GR9277 #6: "For me the solution shown is pretty confusing. For some reason it works but it definitely eludes me." ([9277/6](http://grephysics.net/ans/9277/6))
- **[stated-in-snippet]** GR8677 #76: "This solution is confusing. Please specify why the factor of (1/2) disappears when you equate the translational energy with the potential energy." ([8677/76](http://grephysics.net/ans/8677/76))
- **[stated-in-snippet]** GR8677 #97: users say "the terms 'rotational/translational angular momentum' are confusing and don't really explain what's going on." ([8677/97](https://grephysics.net/ans/8677/97/5177))
- **[stated-in-snippet]** GR8677 #47: a user notes the solution's introduction "makes this seem confusing." ([8677/47](http://grephysics.net/ans/8677/47))
- **[stated-in-snippet]** GR9277 #21: "I don't understand the explanation for II." ([9277/21](http://grephysics.net/ans/9277/21/674))

Direct reports of errors/typos in the canonical solutions:

- **[stated-in-snippet]** GR9277 #95: a user flags a typo — denominator should have one factor, not two. ([9277/95](http://grephysics.net/ans/9277/95))
- **[stated-in-snippet]** GR9277 #88: a user says the solution claims the field is larger for (D) but it "should" be smaller. ([9277/88](http://grephysics.net/ans/9277/88))
- **[stated-in-snippet]** GR9277 #33: the answer's author "mistyped" the result. ([9277/33](http://grephysics.net/ans/9277/33))
- **[stated-in-snippet]** GR0177 #16: "small typo… 10,000 should be number of counts (unitless)." ([0177/16](http://grephysics.net/ans/0177/16))

Community supplies _better/alternate_ explanations (the value-add the forum provides on top of grephysics):

- **[stated-in-snippet]** GR8677 #55: a user adds a clarification distinguishing "Born Probability interpretation" vs. "Born Approximation." ([8677/55](https://grephysics.net/ans/8677/55))
- **[stated-in-snippet]** GR8677 #65: user explains where the extra term in the Biot–Savart law comes from (the sin term in the cross product). ([8677/65](http://grephysics.net/ans/8677/65/1742))
- **[stated-in-snippet]** GR8677 #77: a user posts an alternative solution using conservation of energy. ([8677/77](http://grephysics.net/ans/8677/77))
- **[stated-in-snippet]** GR9277 #87: "That's exactly where I was getting confused on this problem!" after another user posts an alternate solution. ([9277/87](http://grephysics.net/ans/9277/87))
- **[stated-in-snippet]** On the forum itself, a GR0177 #5 thermal-equilibrium thread: a user didn't understand why a Hamiltonian was used; another member gave a cleaner explanation via the equipartition theorem (avg internal energy = f/2 kT). A Doppler-effect thread similarly corrected the formula to F' = F·[(V+Vo)/(V+Vs)]. ([GR0177 #5 thread](https://physicsgre.com/viewtopic.php?f=19&t=70); [GREPhysics.net Problems thread](https://physicsgre.com/viewtopic.php?t=2249))

**Implication:** There is clear, repeated demand for solutions that are (a) correct, (b) step-by-step with the "skipped algebra" shown, and (c) offer multiple approaches. The single most-requested missing piece is _why a step happens_ (e.g., "why does the 1/2 disappear"), not just the final number.

---

## Theme 3 — Students want MORE problems beyond the 4 released exams

The supply of official material is a hard, repeatedly stated constraint.

- **[stated-in-snippet]** "The four previous exams… are the only ones out there. Other than practicing on those, students can do homework problems from a favorite university physics text or buy a book of problems." ([more practice thread context](https://physicsgre.com/viewtopic.php?t=1073))
- **[stated-in-snippet]** Community-generated supplements exist precisely to fill this gap: a sticky "User Created 70 Sample Questions with answers" thread (questions deliberately _imitate_ ETS style because posting real ETS items "would be plagiarism"). ([t=2492](https://physicsgre.com/viewtopic.php?t=2492))
- **[stated-in-snippet]** Other recommended supplements: "3000 Solved Problems in Physics" (Halpern), a ~15-problem PhysicsGRE-only set, and "500 practice problems found online" with grephysics solutions. ([key to success thread](https://physicsgre.com/viewtopic.php?t=1782))
- **[stated-in-snippet]** "Conquering the Physics GRE" is the most-recommended _book_ of additional problems: 3 full practice exams + 150+ extra problems, "problems… tend to be more difficult than those provided by ETS," with a final chapter dedicated to limiting cases / order-of-magnitude / dimensional analysis strategy. Caveats noted: earlier editions had "numerous errors and typos." ([book thread](http://www.physicsgre.com/viewtopic.php?f=18&t=5168); [Amazon-reviews thread](https://physicsgre.com/viewtopic.php?t=6300))
- **[inferred-from-title]** Additional user-made resources circulate: "Physics GRE 1777 Solutions" (a non-released exam), "Sterling Test Prep GRE Physics Practice Questions" review. ([1777 solutions](https://physicsgre.com/viewtopic.php?t=127211); [Sterling review](https://physicsgre.com/viewtopic.php?t=6353))

**Implication:** A study app that can generate or curate ETS-style problems _beyond_ the 4 exams addresses the community's single biggest material shortage. Quality control matters — user-made sets are valued but repeatedly flagged for unit errors and disputed answers (e.g., the 70-question thread had corrections to Q50 units and disputed answers on Q23/Q25).

---

## Theme 4 — How users actually want to DRILL (workflow)

The community has a fairly codified practice methodology that an app could operationalize.

- **[stated-in-snippet]** Canonical two-pass method ("Working Practice Problems on the Physics GRE"): **Step I** — attempt under exam conditions, quickly solve or eliminate choices and guess; **Step II** — rework it as untimed homework (references/help allowed), then revisit and ask "how would I solve this in the shortest possible time?" ([t=1063](http://www.physicsgre.com/viewtopic.php?t=1063))
- **[stated-in-snippet]** Overall loop ("Preparation Advice — Overview"): review fundamentals/equations → work sample problems → review them → study related material → take a sample test → review → repeat. Multiple-choice drilling should be a large share of prep because the test is multiple choice. ([t=1057](https://physicsgre.com/viewtopic.php?t=1057))
- **[stated-in-snippet]** Study groups and online study groups are a recurring desire (members coordinate weekly problem sets and per-subject deadlines). ([Online Study Group](https://physicsgre.com/viewtopic.php?t=4136))
- **[stated-in-snippet]** Spacing the official tests is standard advice: take one early, one mid-prep, save the last for a few weeks before the exam (treat them as a scarce, calibrated resource). ([t=1057](https://physicsgre.com/viewtopic.php?t=1057))
- **[stated-in-snippet]** Equation drilling / self-made formula sheets reviewed daily are common; debate exists over memorization vs. application ("less about memorization and more about applying concepts"). ([key to success](https://physicsgre.com/viewtopic.php?t=1782); [Memorizing Formulas](https://physicsgre.com/viewtopic.php?t=3957); [What to memorize](https://physicsgre.com/viewtopic.php?t=1726))

**Implication:** App should support (a) a timed "exam mode" and an untimed "study mode" on the same problem, (b) spaced re-exposure of missed problems, (c) topic-scoped problem sets with deadlines, and (d) formula/flashcard drilling alongside problems. (No direct evidence found of the forum discussing Anki/SRS specifically — that query returned only external blogs, not forum threads — so SRS is an _inferred_ fit, not a stated demand.)

---

## Theme 5 — Speed / timing is the #1 difficulty, not conceptual depth

- **[stated-in-snippet]** "How can I break 600 on this test?" — top advice is timing: practice under time limits, **drop any problem you can't solve in ~1 minute**, on the first pass look at units/limits unless the calc is trivially fast, mark-and-skip anything needing written calculation. ([t=3515](https://physicsgre.com/viewtopic.php?t=3515))
- **[stated-in-snippet]** "The PGRE mostly tests your speed at simple computations and eliminating wrong answers rather than any in-depth thinking." ([f=18 prep](https://physicsgre.com/viewforum.php?f=18))
- **[stated-in-snippet]** Tricks are highly valued: "an absurd number of questions… you can answer just by being good at limiting cases and using dimensional analysis"; recent exams sometimes deliberately give answer choices identical units to _forbid_ dimensional analysis. ([dimensional analysis thread](http://www.physicsgre.com/viewtopic.php?t=5321))
- **[stated-in-snippet]** GR8677 #6 is a worked example of this culture: the "real" answer is a derivation, but the community-preferred answer is "tangential acceleration must be >0 and <g, so eliminate" — solve by reasoning, not algebra. ([8677/6 forum](http://www.physicsgre.com/viewtopic.php?f=19&t=2518))

**Implication:** Each problem in the app should carry not just a correct solution but a "fast path" (elimination / limiting-case / dimensional-analysis route) and ideally a target-time. This is a distinct, under-served content type vs. grephysics.net's derivation-style answers.

---

## Topic-frequency observations

**A. Official ETS subject weighting** (the structural prior for how many problems exist per topic; corroborated via ETS, surfaced through forum-adjacent results — **[stated-in-snippet]**):

| Topic                                                    | Approx. weight |
| -------------------------------------------------------- | -------------- |
| Classical Mechanics                                      | 20%            |
| Electromagnetism                                         | 18%            |
| Quantum Mechanics                                        | 12%            |
| Thermodynamics & Statistical Mechanics                   | 10%            |
| Atomic Physics                                           | 10%            |
| Optics & Wave Phenomena                                  | 9%             |
| Specialized (Nuclear, Condensed Matter, Astro, Particle) | 9%             |
| Special Relativity                                       | 6%             |
| Laboratory Methods                                       | 6%             |

Subscores are reported in three buckets: Classical Mechanics; Electromagnetism; Quantum + Atomic. ([ETS content structure](https://www.ets.org/gre/test-takers/subject-tests/about/content-structure.html))

**B. Which topics generate the most _forum_ discussion** (observed via thread titles + recurring problem threads — mix of **[stated-in-snippet]** and **[inferred-from-title]**):

- **Classical mechanics** — heaviest per-problem traffic (rotational motion / moment of inertia, angular momentum, statics, frictionless-track kinematics like GR8677 #6). Matches its 20% weight and its reliance on multi-step setups where students get stuck. ([f=19 index](https://physicsgre.com/viewforum.php?f=19))
- **E&M** — induction, coaxial-cable / Biot–Savart fields (e.g., GR9277 #9), AC/DC circuits; "Electromagnetic induction and magnet shapes. Help!" is a named thread. ([f=19 index](https://physicsgre.com/viewforum.php?f=19))
- **Quantum / Atomic** — Born probability vs. Born approximation, momentum operator (GR9277 #1), harmonic oscillator; community view is that PGRE QM is often "definitions-level," but the _confusing-solution_ complaints cluster here. ([Best QM text thread](https://physicsgre.com/viewtopic.php?t=73))
- **Thermo / Stat Mech** — equipartition / thermal-equilibrium confusion (GR0177 #5); undergrads often haven't taken stat mech, so these draw "how do I even start" posts. ([stat mech as undergrad](https://physicsgre.com/viewtopic.php?t=552))
- **Optics** — reported as the _hardest_ on at least one administration: "October 2016 was much harder… optics questions were brutal… wouldn't have focused as much on optics if I'd known." Thin-film and lensmaker/telescope problems (GR9677 #58, #82). ([Oct 2016 thread](https://physicsgre.com/viewtopic.php?t=6496))
- **Special Relativity** — photon→e⁺e⁻ pair-production threshold (1.022 MeV) and relativistic Doppler recur. ([t=109](https://physicsgre.com/viewtopic.php?t=109))
- **"Trivia" / Lab methods** — a distinct pain point: students report unexpected fact-recall questions (lab techniques, Compton-effect-style facts) "that hadn't appeared in practice exams," causing stress and careless errors elsewhere. ([Oct 2016 thread](https://physicsgre.com/viewtopic.php?t=6496); [Trivia Question thread](https://physicsgre.com/viewtopic.php?t=3595))

**C. Relative exam difficulty perception** — **[stated-in-snippet]** "The 1996 test (GR9677) is the hardest conceptually, while the 1986 exam (GR8677) had more trick questions." Useful for difficulty-tagging an item bank. ([Oct 2016 thread](https://physicsgre.com/viewtopic.php?t=6496))

---

## User wants / needs (implications for a practice-problem study app)

1. **Problem-centric, dual-addressable item bank.** Every item should be reachable by (exam, problem #) _and_ by physics topic/subtopic — both are how the community already organizes. [Strong evidence: Theme 1.]
2. **Solutions that beat grephysics.net.** The bar is low and the demand is explicit: correct (no typos), fully stepped (show the algebra users complain is skipped), and offering _multiple approaches_. The recurring complaint is missing "why this step," not the final answer. [Strong: Theme 2.]
3. **A separate "fast path" per problem.** Distinct content field for the GRE-style elimination route (limiting cases, dimensional analysis, units, symmetry, order-of-magnitude). This is what experienced members actually teach and what grephysics under-serves. [Strong: Theme 5.]
4. **More problems than the 4 exams — quality-controlled.** The hard material ceiling is the top complaint; user-made supplements are welcomed but criticized for unit/answer errors, so generated/curated problems must be vetted. [Strong: Theme 3.]
5. **Timed exam mode + untimed study mode on the same item, with per-problem target times.** Mirrors the community's codified two-pass method and the "speed test" framing. [Strong: Themes 4 & 5.]
6. **Spaced re-exposure of missed problems + topic-scoped sets with deadlines.** Reflects the study-group cadence and the "save the last practice test" spacing advice. SRS/flashcards for formulas is a plausible adjacent feature but is _inferred_ (no forum thread directly endorsing SRS was found). [Moderate: Theme 4.]
7. **Difficulty + topic tagging.** Drive coverage by ETS weights (CM 20%, E&M 18% as the top two) while over-indexing remediation on the disproportionately painful areas: optics, stat mech, and "trivia"/lab-methods recall. [Strong: topic-frequency section.]
8. **Equation/fact reference and a "trivia" drill mode.** Lab-methods and fact-recall questions blindside students because they can't be derived; a dedicated rote-fact drill addresses a stated gap. [Moderate: Theme 5 / trivia.]

---

## Source count

**Distinct PhysicsGRE.com forum threads/boards identified:** ~30
(boards: f=1, f=3, f=13, f=14, f=18, f=19, f=21, f=22, f=27; threads incl. t=70, t=73, t=101, t=109, t=111, t=145180, t=552, t=1057, t=1059, t=1063, t=1064, t=1073, t=1782, t=2249, t=2444, t=2492, t=2518, t=2548, t=3515, t=3595, t=3957, t=4009, t=4014, t=4136, t=4164, t=4586, t=4771, t=5168, t=5169, t=5210, t=5321, t=6300, t=6353, t=6496, t=127211).

**Distinct grephysics.net answer pages cited (with user comments):** ~14
(8677/#6,#47,#55,#65,#76,#77,#97; 9277/#6,#21,#33,#87,#88,#95; 0177/#16; plus the all-solutions index).

**Distinct corroborating external sources:** ~3 (ETS content-structure page; UMN physics wiki; misc. prep guides used only to confirm weightings/structure).

**Total distinct sources: ~47** (≈44 directly from physicsgre.com + grephysics.net, the two target ecosystems; ~3 external corroborating).
