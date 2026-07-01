# Physics GRE (PGRE) Prep — Resources, Materials & Tools

Research source: **physicsgre.com** (Physics GRE Discussion Forums), the largest and
most active community for Physics GRE prep, plus cross-references to The GradCafe and
general study-resource indexes. physicsgre.com is behind Cloudflare (HTTP 403 on direct
fetch), so all findings below are reconstructed from search-engine-indexed **thread
titles** and **snippet excerpts**. Each claim is tagged:

- **[snippet]** = stated in an indexed snippet excerpt (higher confidence)
- **[title]** = inferred from the thread title only (lower confidence, content not seen)

Purpose: inform the design of a study app for Physics GRE prep.

---

## Summary (key takeaways for app design)

1. **The corpus of "official" practice material is tiny and finite.** There are only
   ~4-5 legally obtainable full released exams (GR8677, GR9277, GR9677, GR0177, plus
   older 1986/1992/1996 forms). Users repeatedly **run out of material** and ask what to
   do next. This is the single clearest unmet need.
2. **"Conquering the Physics GRE" (Kahn & Anderson, Cambridge)** is the dominant
   modern prep book — near-universal recommendation as the best PGRE-specific resource,
   though noted as harder than the real test and not great for _learning_ physics from
   scratch.
3. **Undergrad textbooks are the foundation** (Halliday/Resnick/Walker, Griffiths E&M
   and QM, Shankar, Boas for math). Used for filling gaps, not for test-style practice.
4. **The exam is widely described as a test of speed, not just knowledge.** Time
   management and pacing (≈1.7 min/question) is the recurring pain point — a strong
   signal for timed/adaptive practice features in an app.
5. **Flashcards and spaced repetition are actively used**, but existing assets are
   scattered, incomplete, error-prone, and have **poor LaTeX rendering on mobile** —
   a concrete product opportunity.
6. **Community-built tools already exist but are amateur/abandoned**: a JavaScript
   flashcard quiz app, an Anki deck, CWRU's flashcards, a half-finished Android app.
   No polished, integrated, mobile-first practice+SRS product was found.
7. **Trust/quality is a theme**: the cheaper books (REA "purple book", Sterling) are
   criticized as full of errors and unrepresentative. Users want _vetted, representative,
   calculator-free_ problems with worked solutions.

Distinct sources found: **~35 distinct physicsgre.com threads/forum pages** plus
external corroborators (GradCafe, CWRU, grephysics.net, OSU, physicsgreprep.com).

---

## Ranked list of recommended resources (with citations)

### Tier 1 — Most recommended / consensus

1. **ETS official released practice exams / "Practicing to Take the Physics Test"**
   — Considered _the_ best study material because they show exactly how ETS tests.
   Only a handful exist (GR8677, GR9277, GR9677, GR0177; book contains 3 full exams).
   Users are told to weight the **2008 (GR0177)** form most heavily and prioritize it
   first, then GR9677, GR9277, GR8677. **[snippet]**
   - "Sticky: Physics GRE 4 Practice Tests and Solutions" — https://physicsgre.com/viewtopic.php?t=2548
   - "ETS Physics Problems - GRE Practicing to take the Physics" — https://physicsgre.com/viewtopic.php?t=1059
   - "Sticky: Books and Other Preparation Materials" — https://physicsgre.com/viewtopic.php?t=2559
   - "If you could go back...." (prioritize GR0177 → GR9677 → GR9277 → GR8677) — https://physicsgre.com/viewtopic.php?t=679
   - "How Relevant are the 80's and 90's Practice Tests?" — https://physicsgre.com/viewtopic.php?t=6325

2. **"Conquering the Physics GRE" (CTPG) by Yoni Kahn & Adam Anderson, Cambridge UP**
   — The dominant PGRE-specific book; full topic review + strategy chapter (limiting
   cases, order-of-magnitude, dimensional analysis) + practice exams. Caveats: practice
   exams are **harder than recent real exams** (closer to older PGREs), earlier editions
   had many typos, and it's a _review_ not a _learning_ text. **[snippet]**
   - "BOOK: Conquering the Physics GRE" — http://www.physicsgre.com/viewtopic.php?f=18&t=5168
   - "New Physics GRE prep book available" — https://physicsgre.com/viewtopic.php?t=4771
   - "New Gre Physics prep book" — https://physicsgre.com/viewtopic.php?t=4750
   - "Conquering the Physics GRE - Amazon reviews" — https://physicsgre.com/viewtopic.php?t=6300
   - "Are the CTPG practice exams harder?" — https://physicsgre.com/viewtopic.php?t=145180

3. **grephysics.net** — Free, worked solutions to **all** problems on all released
   PGREs, with crowd-discussion of multiple solution methods under each problem.
   Repeatedly cited as the go-to companion to the released exams. **[snippet]**
   - "GREPhysics.net Problems" — https://physicsgre.com/viewtopic.php?t=2249
   - (External) http://grephysics.net/ans/

4. **Ohio State University PGRE site** — Hosts released tests and topic practice
   (e.g., quantum) for free; frequently recommended. **[snippet]**
   - "OSU practice questions" — https://physicsgre.com/viewtopic.php?t=4062
   - (External) https://physics.osu.edu/physics_gre

### Tier 2 — Foundational textbooks (for content, not test format)

5. **Halliday, Resnick & Walker — Fundamentals of Physics** (a.k.a. HRW): the
   recommended intro foundation; "go through HRW + the 4 practice exams" is cited as
   sufficient for a ~700 target. **[snippet]**
   - "Long-term study strategies" — https://physicsgre.com/viewtopic.php?t=20
   - "Physics Textbooks - Lets Build a List" — https://physicsgre.com/viewtopic.php?t=23
   - "best book for gre physics" — https://physicsgre.com/viewtopic.php?t=3321

6. **Griffiths — Introduction to Electrodynamics** and **Introduction to Quantum
   Mechanics**: near-revered for E&M and QM review. **[snippet]**
   - "Physics Textbooks - Lets Build a List" — https://physicsgre.com/viewtopic.php?t=23
   - "Rant About Textbooks by Griffiths" — https://physicsgre.com/viewtopic.php?t=523
   - "Best Quantum Mechanics text" — https://physicsgre.com/viewtopic.php?t=73

7. **Shankar — Principles of Quantum Mechanics** (QM review) and **Boas —
   Mathematical Methods** (math review: diff eq, linear algebra). **[snippet]**
   - "Long-term study strategies" — https://physicsgre.com/viewtopic.php?t=20

8. **"3,000 Solved Problems in Physics" (Schaum's)** — recommended as a better source
   of extra practice problems than the REA book. **[snippet]**
   - "REA purple book" — https://physicsgre.com/viewtopic.php?t=3979
   - "Sticky: Books and Other Preparation Materials" — https://physicsgre.com/viewtopic.php?t=2559

### Tier 3 — Mixed / cautioned-against (quality complaints)

9. **REA "The Best Test Preparation for the GRE Physics" (the "purple book")** —
   Mixed-to-negative. Praised for _quantity_ of problems but criticized as full of
   errors/typos, too hard, **calculator-dependent (not allowed on the real test)**, and
   unrepresentative. Treated as a "starter refresh" only. **[snippet]**
   - "REA purple book" — https://physicsgre.com/viewtopic.php?t=3979
   - "Be Careful When Using the REA GRE Physics Book" — https://physicsgre.com/viewtopic.php?t=9
   - "REA - The Best Test Preparation for the GRE" — https://physicsgre.com/viewtopic.php?t=1075

10. **Sterling Test Prep — GRE Physics Practice Questions** (1,420 Qs, 12 diagnostic
    tests, per-topic formula sheets) — Reviewed critically: reads like _AP Physics_
    material, too easy / plug-and-chug, and **missing ~50% of the test** (no QM, stat
    mech, special relativity, Lagrangian/Hamiltonian, lab methods). **[snippet]**
    - "Book review: Sterling Test Prep GRE Physics Practice Questions" — https://physicsgre.com/viewtopic.php?t=6353

11. **physicsgreprep.com** — A competing prep book/site offering 3 full sample exams +
    practice problems; promoted on the forum. **[snippet]**
    - "More practice problems?" — http://www.physicsgre.com/viewtopic.php?t=4141
    - (External) https://www.physicsgreprep.com/ , http://www.physicsgreprep.com/links.html

### Tier 4 — Supplementary / free online (mentioned, less central)

12. **HyperPhysics, MIT OpenCourseWare, Khan Academy** — referenced as free concept
    review / quick reference, more in GradCafe and resource-index contexts than as PGRE
    forum favorites. **[snippet, partly external]**
    - (GradCafe) "GRE PHYSICS PREP MATERIAL" — https://forum.thegradcafe.com/topic/109375-gre-physics-prep-material/
13. **Major Field Test (MFT) sample questions** — liked as good extra practice
    material, but users want _more_ of them (see Unmet Needs). **[snippet]**
    - "other source of practice questions?" — https://physicsgre.com/viewtopic.php?t=1728
14. **University of Washington PGRE study site** — weekly practice-test schedule
    (GR8677 week 1, GR9677 week 8, etc.); an example of structured self-study people
    follow. **[snippet, external]**
    - https://sites.google.com/a/uw.edu/physicsgre/home

---

## Tools / apps mentioned (existing — mostly amateur or abandoned)

These show what the community has already hacked together and where the gaps are.

1. **JavaScript flashcard quiz app — "mathandcode.com/pgre/"** — A user created **103
   Q&A flashcards** (things to derive / memorize / sketch mentally, _not_ full practice
   problems), sourced from the Kahn & Anderson (CTPG) book, with a JS app that
   **shuffles and quizzes** the user. Author solicited bug/typo/missing-card feedback.
   **[snippet]**
   - "Physics GRE Practice 'flash cards'" — https://physicsgre.com/viewtopic.php?t=6495

2. **Anki deck — "PGRE Flashcards (on Anki)"** — Community Anki deck shared via
   AnkiWeb covering classical mechanics, E&M, optics/waves, thermo/stat-mech. Author
   warns it's **incomplete, may contain errors**, and that **LaTeX often doesn't render
   properly on the Anki mobile (iOS/Android) apps**. **[snippet]**
   - "PGRE Flashcards (on Anki)" — https://physicsgre.com/viewtopic.php?t=5242

3. **CWRU (Case Western Reserve) Physics GRE Flashcards** — Free, dept-built flashcard
   set: **14 categories** (classical mechanics → fluids), browse-in-order or random;
   also offered as free **physical printable/mailed cards**. Praised as effective for
   recall ("memorized material from the cards"), but **some content is harder/more
   advanced than the real exam**. **[snippet]**
   - "Physics Gre free flash cards." — https://physicsgre.com/viewtopic.php?t=4649
   - "Physics GRE flash cards available again!" — http://www.physicsgre.com/viewtopic.php?f=1&t=5494
   - (External) http://great.cwru.edu/ , https://physics.case.edu/flashcards/

4. **Printable PGRE flashcards — physicsgrad.com/printable-pgre-flash-cards** —
   Printable + digital flashcard set linked from the forum. **[snippet]**
   - "Physics Gre free flash cards." — https://physicsgre.com/viewtopic.php?t=4649

5. **Student-built Android app (PGRE practice tests)** — A user developed an Android
   app to take released exams (GR0177, GR9677, GR8677, GR9277) on mobile; at time of
   posting it was **unfinished — only GR0177 available for trial**. Indicates demand for
   a mobile practice-test experience but no maintained product. **[snippet/title]**
   - "GRE test on mobile device" — https://physicsgre.com/viewtopic.php?t=5256

6. **Community Physics Problems (CPP)** — physicsgre.com's own crowd-submitted problem
   set — but it was a small, now-defunct experiment (**~15 problems total**), and a
   separate sticky of ~70 user-submitted Q&A. Demonstrates the community _wanted_ a
   crowd problem bank but it never reached scale. **[snippet]**
   - "Physics GRE Practice Problems" — https://physicsgre.com/viewtopic.php?t=1073
   - "Community Physics Problems" — http://www.physicsgre.com/viewtopic.php?f=13&t=1074

7. **General/commercial GRE apps (Magoosh, Kaplan, Manhattan Prep, Barron's,
   Varsity Tutors)** — exist for the _general_ GRE but **none are Physics-subject-test
   specific**; surfaced as adjacent options, not forum favorites. **[external]**

Notable absence: **no polished, integrated, mobile-first app combining a large
representative problem bank + timer/pacing + spaced repetition + good math
(LaTeX) rendering** was found. That whitespace is the design opportunity.

---

## Unmet needs / what users wish existed

Ordered by strength of signal.

1. **"I ran out of practice material — what now?"** — The strongest, most explicit
   unmet need. The finite supply of released exams + CTPG means dedicated students
   exhaust everything and resort to _re-taking_ old tests (and waiting a month for memory
   to fade so scores aren't inflated). **[snippet]**
   - "How to practice for physics gre when out of study material?" — https://physicsgre.com/viewtopic.php?t=173830
   - "More practice problems?" — http://www.physicsgre.com/viewtopic.php?t=4141
   - "other source of practice questions?" — https://physicsgre.com/viewtopic.php?t=1728

2. **"It would be nice if there were more problems."** — Direct quote in a snippet
   about the Major Field Test sample questions: users like them but **want more
   representative problems to work through**. General desire for "a good source of
   practice problems other than the old tests." **[snippet]**
   - "other source of practice questions?" — https://physicsgre.com/viewtopic.php?t=1728

3. **More / better practice TESTS specifically** (not just loose problems) — full,
   timed, exam-shaped forms are scarce; people want additional full-length forms that
   match current difficulty. **[snippet/title]**
   - "Sticky: Physics GRE 4 Practice Tests and Solutions" — https://physicsgre.com/viewtopic.php?t=2548
   - "Are the CTPG practice exams harder?" (want forms matching _current_ difficulty) — https://physicsgre.com/viewtopic.php?t=145180

4. **A vetted "which problems are good / list of errors" guide** — Because cheap books
   (REA, Sterling) are error-ridden and unrepresentative, a user explicitly asks: _"Is
   there a guide anywhere that says which problems are useful and/or lists the errors?"_
   → demand for **curated, quality-tagged, representative** problem sets with worked
   solutions, calculator-free. **[snippet]**
   - "Be Careful When Using the REA GRE Physics Book" — https://physicsgre.com/viewtopic.php?t=9
   - "More practice problems?" — http://www.physicsgre.com/viewtopic.php?t=4141

5. **Speed / pacing training** — Repeatedly framed as "GRE is a test of speed more than
   knowledge." Top regret: not practicing fast enough (timed at 3.5 hrs, only finished
   70 Qs on the real test). Implies demand for **per-question timers, pacing analytics,
   and elimination-strategy drills (~1 min/question)**. **[snippet]**
   - "If you could go back...." — https://physicsgre.com/viewtopic.php?t=679
   - "Physics GRE strategies" — https://physicsgre.com/viewtopic.php?t=1636
   - "Re-Take Physics Gre? How to improve guessing?" — https://physicsgre.com/viewtopic.php?t=5721

6. **Flashcards that actually work on mobile with proper math rendering** — Existing
   Anki/JS/CWRU decks are incomplete, error-prone, and the most-used one (Anki) **renders
   LaTeX poorly on phones**. Clear gap for a mobile-first SRS with first-class equation
   rendering and a vetted, complete card set. **[snippet]**
   - "PGRE Flashcards (on Anki)" — https://physicsgre.com/viewtopic.php?t=5242
   - "Physics GRE Practice 'flash cards'" — https://physicsgre.com/viewtopic.php?t=6495

7. **Topic-targeted remediation** — After diagnosing weak areas via a practice test,
   users want focused practice by topic (E&M, optics, modern, thermo, etc.); the forum
   even organizes recommendations this way, but practice material isn't well organized
   by topic + difficulty. Implies demand for **adaptive, weakness-targeted problem
   selection**. **[snippet/title]**
   - "Practice problems in EM and optics" — https://physicsgre.com/viewtopic.php?t=2600
   - "Physics GRE Preparation Advice - Overview" — https://physicsgre.com/viewtopic.php?t=1057

8. **A guided study plan / structured schedule** — Long-term planning is hard;
   students fear losing progress if they pause (">5 days away and you're in jeopardy").
   Demand for **structured, paced, resumable study plans** (the UW weekly schedule is a
   manual workaround). **[snippet]**
   - "Long-term study strategies" — https://physicsgre.com/viewtopic.php?t=20

---

## Cross-reference notes

- **The GradCafe** corroborates CTPG as the single most popular/effective resource and
  echoes the ETS-official-materials-first approach. — https://forum.thegradcafe.com/topic/109375-gre-physics-prep-material/
- Reddit r/physicsGRE was searched but returned no usable indexed snippets via the
  search tool; not used as a citation here.

## Confidence note

The richest, snippet-backed findings concern: the resource rankings (CTPG, ETS, REA,
Sterling, grephysics.net), the existing flashcard/Anki/CWRU/JS tools, mobile-LaTeX
rendering complaints, the "ran out of material" / "would be nice if more problems"
needs, and the speed/pacing pain point. Thread _existence and topic_ are confirmed by
indexed titles; full thread contents were not directly accessible (Cloudflare 403), so
any single in-thread detail tagged [title] should be verified against the live thread
before being treated as definitive.
