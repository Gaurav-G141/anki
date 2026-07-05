# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""PGRE Performance quiz: real released exam MCQs (Physics GRE fork).

This is the honest **Performance** dimension: instead of grading recall on cards
the student has already studied, it serves *real, unseen* multiple-choice
questions from a released ETS exam (GR9277, community-scraped from grephysics.net)
and grades each answer against the known key. The questions + answer key are
bundled as ``qt/aqt/data/pgre_mcq.json`` (generated from ``speedrun/pgre_problems.py``)
so the packaged app needs no source markdown at runtime.

The GUI-free pieces — ``load_questions`` and ``QuizSession`` (question order,
grading, running accuracy) — are unit-tested in ``qt/tests/test_pgre_quiz.py``
against the in-repo data file, with no running Qt app. ``MCQQuiz`` is the dialog
that presents them in a webview (MathJax renders the LaTeX offline, exactly like
the card reviewer).
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import aqt
from aqt.qt import QDialog, Qt, QVBoxLayout
from aqt.utils import disable_help_button, restoreGeom, saveGeom
from aqt.webview import AnkiWebView, AnkiWebViewKind

# ------------------------------------------------------------------ data / core


def _default_data_path() -> str:
    """Bundled MCQ data path (resolved lazily so import stays GUI-free)."""
    from aqt.utils import aqt_data_path

    return str(aqt_data_path() / "pgre_mcq.json")


def load_questions(path: str | None = None) -> list[dict[str, Any]]:
    """Load the bundled MCQ questions (list of dicts). Each has ``id``,
    ``subject``, ``topic``, ``statement``, ``choices`` (``[[letter, text], …]``),
    ``answer`` (letter), and ``solution``.

    In addition to the released-exam bank (``pgre_mcq.json``), this also appends
    the AI-generated Phase-2 questions from ``pgre_mcq_generated.json`` in the
    same directory, when that file is present (missing => skipped silently)."""
    if path is None:
        path = _default_data_path()
    with open(path, encoding="utf-8") as f:
        questions: list[dict[str, Any]] = json.load(f)["questions"]

    # Also fold in the AI-generated Phase-2 bank sitting next to the main file.
    generated = os.path.join(os.path.dirname(path), "pgre_mcq_generated.json")
    try:
        with open(generated, encoding="utf-8") as f:
            questions.extend(json.load(f).get("questions", []))
    except (OSError, ValueError):
        pass  # missing/unreadable/malformed -> ship the released bank alone

    return questions


def select_variants(
    questions: list[dict[str, Any]], rotation: dict[str, int]
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Reduce the pool to ONE surface variant per concept, rotating across calls
    (the fluency-illusion fix: a repeated question comes back *reworded* so the
    student retrieves the concept instead of pattern-matching a memorized card).

    A ``source:"reworded"`` item groups with its seed via ``seed_id``; a real seed
    and any *novel* generated item are independent (keyed by their own ``id``), so
    novel variants stay in the pool alongside the seed. Within a group the seed is
    first (real bank loads before the generated bank), so rotation 0 serves the
    original and later sessions cycle the rewordings. Returns
    ``(selected_questions, updated_rotation)``; pure — no I/O, safe on any list."""
    groups: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for q in questions:
        key = q.get("seed_id") if q.get("source") == "reworded" else q.get("id")
        key = key or q.get("id") or ""
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(q)

    rot = dict(rotation or {})
    selected: list[dict[str, Any]] = []
    for key in order:
        members = groups[key]
        if len(members) == 1:
            selected.append(members[0])
            continue
        idx = rot.get(key, 0) % len(members)
        selected.append(members[idx])
        rot[key] = rot.get(key, 0) + 1
    return selected, rot


class QuizSession:
    """Tracks progress through a fixed list of MCQs: the current question, the
    per-question record, and the running accuracy. Pure logic, no Qt.

    ``order`` lets callers fix the sequence (tests pass an explicit order for
    determinism; the dialog shuffles).
    """

    def __init__(
        self, questions: list[dict[str, Any]], order: list[int] | None = None
    ) -> None:
        self.questions = questions
        self.order = order if order is not None else list(range(len(questions)))
        self.pos = 0
        #: One dict per answered question: ``{"id", "chosen", "correct"}``.
        self.records: list[dict[str, Any]] = []
        self._answered_current = False

    @property
    def done(self) -> bool:
        return self.pos >= len(self.order)

    def current(self) -> dict[str, Any] | None:
        if self.done:
            return None
        return self.questions[self.order[self.pos]]

    def submit(self, letter: str) -> bool | None:
        """Grade the current question against the key. Returns whether it was
        correct, or ``None`` if there is nothing to answer / already answered
        (so a double-tap can't inflate the count)."""
        q = self.current()
        if q is None or self._answered_current:
            return None
        correct = letter == q["answer"]
        self.records.append({"id": q["id"], "chosen": letter, "correct": correct})
        self._answered_current = True
        return correct

    def advance(self) -> None:
        """Move to the next question (only after the current one was answered)."""
        if self._answered_current:
            self.pos += 1
            self._answered_current = False

    @property
    def answered(self) -> int:
        return len(self.records)

    @property
    def correct(self) -> int:
        return sum(1 for r in self.records if r["correct"])

    @property
    def accuracy(self) -> float:
        """Fraction correct of answered (0.0 when none answered yet)."""
        return self.correct / self.answered if self.answered else 0.0


_DISPLAY_MATH = re.compile(r"\$\$(.+?)\$\$", re.S)
_INLINE_MATH = re.compile(r"\$(.+?)\$", re.S)


def to_mathjax(text: str) -> str:
    """Convert the source's ``$…$`` / ``$$…$$`` math delimiters to the
    ``\\(…\\)`` / ``\\[…\\]`` that Anki's MathJax config expects."""
    text = _DISPLAY_MATH.sub(r"\\[\1\\]", text)
    text = _INLINE_MATH.sub(r"\\(\1\\)", text)
    return text


# ------------------------------------------------------------------ dialog


class MCQQuiz(QDialog):
    """Presents the Performance MCQ quiz in a MathJax-capable webview.

    The whole question set is embedded in the page and the quiz runs fully
    client-side (render / grade / next / accuracy). This deliberately avoids the
    ``pycmd`` bridge + ``eval`` round-trip: for a dialog-hosted webview those are
    only delivered after an internal ``domDone`` handshake, and a mistimed
    handshake left the page blank. Embedding the data removes that dependency, so
    the quiz always renders.
    """

    def __init__(self, mw: aqt.main.AnkiQt) -> None:
        QDialog.__init__(self, mw, Qt.WindowType.Window)
        mw.garbage_collect_on_dialog_finish(self)
        self.mw = mw
        self.name = "pgreMcqQuiz"
        self.setWindowTitle("Ankimatter — Practice MCQs")
        disable_help_button(self)
        self.setMinimumSize(600, 560)
        restoreGeom(self, self.name, default_size=(860, 780))

        try:
            questions = load_questions()
        except Exception:
            questions = []

        # Fluency-illusion fix: serve one surface variant per concept, rotating the
        # choice across sessions so a repeated question returns reworded. Rotation
        # state persists in the collection config (per-concept counter).
        try:
            rotation = dict(self.mw.col.get_config("pgreRewordRotation", {}) or {})
        except Exception:
            rotation = {}
        questions, rotation = select_variants(questions, rotation)
        try:
            self.mw.col.set_config("pgreRewordRotation", rotation)
        except Exception:
            pass

        from aqt import heuristic_coach

        # Keep the raw questions for the AI grader (it wants unformatted text).
        self._by_id = {q["id"]: q for q in questions}
        try:
            ai_on = heuristic_coach.ai_available(self.mw.col)
        except Exception:
            ai_on = False

        def optimal(q: dict[str, Any]) -> dict[str, Any] | None:
            rec = heuristic_coach.optimal_for(q.get("id", "")) or {}
            expl = rec.get("student_explanation", "")
            if not expl:
                return None
            return {
                "explanation": to_mathjax(expl),
                "eliminations": [
                    [e.get("choice", ""), to_mathjax(e.get("reason", ""))]
                    for e in (rec.get("eliminations") or [])
                ],
            }

        data = [
            {
                "id": q["id"],
                "statement": to_mathjax(q["statement"]),
                "choices": [
                    [letter, to_mathjax(text)] for letter, text in q["choices"]
                ],
                "answer": q["answer"],
                "solution": to_mathjax(q.get("solution", "")),
                "subject": q.get("topic") or q.get("subject", ""),
                "source": q.get("source", ""),
                "seed_id": q.get("seed_id", ""),
                "difficulty": q.get("difficulty", 3),
                "optimal": optimal(q),
            }
            for q in questions
        ]

        self.web = AnkiWebView(kind=AnkiWebViewKind.PGRE_QUIZ)
        # A user-click "grade my approach" round-trip (safe — unlike the initial
        # render, which is why the question data is still embedded, not bridged).
        self.web.set_bridge_command(self._on_cmd, self)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web)
        self.setLayout(layout)

        # Embed the questions in <head> so the body script has them synchronously.
        head = (
            f"<script>window.QUIZ_DATA = {json.dumps(data)};"
            f"window.AI_ON = {'true' if ai_on else 'false'};</script>"
        )
        self.web.stdHtml(
            _QUIZ_PAGE,
            head=head,
            css=["css/pgre.css"],
            js=["js/mathjax.js", "js/vendor/mathjax/tex-chtml-full.js"],
            context=self,
        )
        self.show()
        self.activateWindow()

    # -- AI heuristic grading (Stage 2) -------------------------------------

    def _on_cmd(self, msg: str) -> Any:
        """Bridge handler: JS asks us to grade a typed approach, or for Andy's
        spoken step-by-step explanation of the fastest solution."""
        if msg.startswith("grade:"):
            self._grade(msg[len("grade:") :])
        elif msg.startswith("explain:"):
            self._explain(msg[len("explain:") :])
        return False

    def _explain(self, payload_json: str) -> None:
        """Fetch Andy's spoken solution script for a question (off the UI thread)
        and hand it back to the page, which animates the narration."""
        from aqt import heuristic_coach

        try:
            payload = json.loads(payload_json)
        except json.JSONDecodeError:
            return
        q = self._by_id.get(payload.get("id"))
        if q is None:
            return

        def task() -> dict[str, Any]:
            return heuristic_coach.explain_steps(q)

        def on_done(fut: Any) -> None:
            try:
                res = fut.result()
            except Exception:
                res = {"ok": False, "steps": []}
            if self.web:
                self.web.eval(f"window.showAndySteps({json.dumps(res)});")

        self.mw.taskman.run_in_background(task, on_done)

    def _grade(self, payload_json: str) -> None:
        from aqt import heuristic_coach

        try:
            payload = json.loads(payload_json)
        except json.JSONDecodeError:
            return
        q = self._by_id.get(payload.get("id"))
        if q is None:
            return
        chosen = str(payload.get("chosen", ""))
        reasoning = str(payload.get("reasoning", ""))

        def task() -> dict[str, Any]:
            return heuristic_coach.grade(q, chosen, reasoning)

        def on_done(fut: Any) -> None:
            try:
                res = fut.result()
            except Exception:
                res = {"ok": False}
            if self.web:
                self.web.eval(f"window.showCoach({json.dumps(res)});")

        self.mw.taskman.run_in_background(task, on_done)

    def reject(self) -> None:
        if self.web:
            self.web.cleanup()
            self.web = None  # type: ignore[assignment]
        saveGeom(self, self.name)
        QDialog.reject(self)


#: Self-contained quiz page. Reads ``window.QUIZ_DATA`` + ``window.AI_ON``
#: (embedded by the dialog), shuffles, and for each question renders the A–E
#: choices AND a free-response box where the student types HOW they'd solve it.
#: On answering it grades the pick client-side, shows the worked solution and the
#: precomputed "fastest approach" (from the optimal-approach key — always shown,
#: no network), and — when a key is present and the student typed reasoning —
#: sends {id, chosen, reasoning} over ``pycmd('grade:…')`` to the Stage-2 AI
#: heuristic grader (``heuristic_coach.grade``), which calls back via
#: ``window.showCoach`` with warm, specific coaching on their *approach*.
#: Raw string: the page's JS carries regex backslashes (Andy's math-stripper)
#: that must reach the browser verbatim, not be interpreted as Python escapes.
_QUIZ_PAGE = r"""
<style>
  /* Observatory MCQ console. Dark-always; tokens from css/pgre.css. */
  :root { color-scheme: dark; }
  body { margin: 0; padding: 20px 22px 32px; }
  #hdr { display: flex; justify-content: space-between; align-items: center;
         gap: 16px; margin-bottom: 16px; }
  #progressWrap { flex: 1; min-width: 0; }
  #progress { display: block; margin-bottom: 6px; }
  /* thin cyan focus meter under the mono "Q n / N" */
  #progressMeter { height: 3px; border-radius: var(--pg-pill); background: var(--pg-line);
                   overflow: hidden; }
  #progressFill { height: 100%; width: 0; border-radius: var(--pg-pill);
                  background: var(--pg-accent); box-shadow: var(--pg-glow);
                  transition: width 220ms ease; }
  #score { color: var(--pg-text-dim); font-size: 13px; white-space: nowrap; }
  #subject { display: flex; align-items: center; gap: 9px; margin-bottom: 12px; }
  #subjectText { font-family: var(--pg-mono); text-transform: uppercase;
                 letter-spacing: 0.14em; font-size: 11px; color: var(--pg-text-dim); }
  /* AI-generated pill: cyan variant of the shared badge (JS toggles display) */
  #genPill { display: none; }
  #genPill.pg-badge { border-color: color-mix(in srgb, var(--pg-accent) 55%, transparent);
                      color: var(--pg-accent);
                      background: color-mix(in srgb, var(--pg-accent) 14%, transparent); }
  #stmt { font-size: 19px; line-height: 1.55; padding: 18px 20px; margin-bottom: 18px; }
  /* .choice styling comes from .pg-choice in css/pgre.css */
  .choice { font-size: 17px; }
  #frq { margin: 16px 0 4px; }
  #frq label { display: block; font-size: 13px; color: var(--pg-text-dim); margin-bottom: 6px; }
  /* console input */
  #reason { width: 100%; box-sizing: border-box; min-height: 74px; resize: vertical;
            border-radius: var(--pg-radius-sm); border: 1px solid var(--pg-line);
            background: var(--pg-panel); color: var(--pg-text);
            font-family: var(--pg-mono); font-size: 14px; padding: 11px 13px; }
  #reason:focus { outline: none;
                  border-color: color-mix(in srgb, var(--pg-accent) 55%, transparent);
                  box-shadow: 0 0 0 1px color-mix(in srgb, var(--pg-accent) 40%, transparent); }
  #verdict { font-size: 17px; font-weight: 600; margin: 18px 0 8px; }
  #solution { font-size: 15px; line-height: 1.55; color: var(--pg-text-dim);
              border-left: 2px solid color-mix(in srgb, var(--pg-accent) 45%, transparent);
              padding-left: 13px; }
  /* .pg-card / .pg-card--fast / .pg-card--coach edges come from css/pgre.css */
  .pg-card .t { font-weight: 700; font-size: 14px; margin-bottom: 6px;
                font-family: var(--pg-mono); letter-spacing: 0.04em; }
  #fast .t { color: var(--pg-accent); }
  #coach .t { color: var(--pg-accent-2); }
  .missed { margin: 8px 0 0 1em; padding: 0; font-size: 14px; color: var(--pg-text-dim); }
  .muted { color: var(--pg-text-dim); font-size: 13px; }
  #summary { text-align: center; padding-top: 46px; }
  #summary .big { font-size: 54px; font-weight: 700; color: var(--pg-accent);
                  text-shadow: 0 0 20px var(--pg-accent-glow); margin: 6px 0;
                  animation: pg-bloom 3.2s ease-in-out infinite; }
  @keyframes pg-bloom {
    0%, 100% { text-shadow: 0 0 14px var(--pg-accent-glow); }
    50%      { text-shadow: 0 0 28px var(--pg-accent-glow); }
  }
  #wm { position: fixed; bottom: 14px; right: 18px; }
  #stmt, #solution, .pg-card { overflow-wrap: anywhere; }
  /* Wide display equations scroll instead of clipping. */
  mjx-container { font-size: 108% !important; max-width: 100%; overflow-x: auto; }
  @media (prefers-reduced-motion: reduce) {
    #summary .big { animation: none; }
    #progressFill { transition: none; }
  }

  /* ---- Andy the atom: a floating tutor that flies around the problem and
     narrates the fastest solution step by step. #andy is fixed-positioned and
     its left/top are transitioned, so setting a new target "flies" him there. */
  #andy {
    position: fixed; left: 50%; top: -90px; width: 46px; height: 46px;
    z-index: 9999; transform: translate(-50%, -50%); pointer-events: none;
    opacity: 0; transition: left 0.9s cubic-bezier(.34,.15,.2,1),
      top 0.9s cubic-bezier(.34,.15,.2,1), opacity 0.4s ease;
  }
  #andy.show { opacity: 1; }
  .andy-atom { position: absolute; inset: 0; animation: andy-bob 2.6s ease-in-out infinite; }
  .andy-nuc {
    position: absolute; left: 50%; top: 50%; width: 18px; height: 18px;
    margin: -9px 0 0 -9px; border-radius: 50%;
    background: radial-gradient(circle at 34% 30%, #eafcff, var(--pg-accent) 60%,
      color-mix(in srgb, var(--pg-accent) 45%, transparent));
    box-shadow: 0 0 12px var(--pg-accent-glow), 0 0 22px var(--pg-accent-glow);
  }
  #andy.thinking .andy-nuc { animation: andy-think 0.9s ease-in-out infinite; }
  .andy-eye { position: absolute; top: 6px; width: 3px; height: 3.6px;
    border-radius: 50%; background: #0a0d16; }
  .andy-eye.l { left: 4.5px; } .andy-eye.r { right: 4.5px; }
  /* Each orbit is a tilted+flattened ellipse; the wrap spins the electron on it. */
  .andy-orbit { position: absolute; left: 50%; top: 50%; width: 46px; height: 46px;
    margin: -23px 0 0 -23px; }
  .andy-ew { position: absolute; inset: 0; }
  .andy-e { position: absolute; left: 50%; top: 50%; width: 5px; height: 5px;
    margin: -2.5px 0 0 -2.5px; border-radius: 50%; background: var(--pg-accent);
    box-shadow: 0 0 6px var(--pg-accent-glow); transform: translateX(21px) scaleY(2.5); }
  .andy-orbit.ao1 { transform: rotate(0deg) scaleY(0.4); }
  .andy-orbit.ao2 { transform: rotate(60deg) scaleY(0.4); }
  .andy-orbit.ao3 { transform: rotate(120deg) scaleY(0.4); }
  .ao1 .andy-ew { animation: andy-orbit 2.6s linear infinite; }
  .ao2 .andy-ew { animation: andy-orbit 3.5s linear infinite reverse; }
  .ao3 .andy-ew { animation: andy-orbit 3.0s linear infinite; }
  /* The bubble docks ABOVE Andy (below him when he's near the top), centred on
     him, so it stays inside the reserved right lane and never covers the text. */
  .andy-bubble {
    position: absolute; left: 50%; bottom: calc(100% + 13px);
    width: max-content; min-width: 120px; max-width: 188px;
    background: var(--pg-panel-2); color: var(--pg-text);
    border: 1px solid color-mix(in srgb, var(--pg-accent) 45%, var(--pg-line));
    border-radius: 13px; padding: 9px 24px 10px 13px; font-size: 13.5px;
    line-height: 1.42; box-shadow: 0 8px 26px rgba(0,0,0,.5), 0 0 16px var(--pg-accent-glow);
    opacity: 0; transform: translateX(-50%) translateY(6px) scale(.96);
    transform-origin: bottom center;
    transition: opacity .25s ease, transform .25s ease; pointer-events: auto;
    white-space: normal;
  }
  .andy-bubble.show { opacity: 1; transform: translateX(-50%); }
  .andy-bubble::after {
    content: ""; position: absolute; left: 50%; bottom: -6px; margin-left: -5px;
    width: 10px; height: 10px; background: var(--pg-panel-2);
    border-right: 1px solid color-mix(in srgb, var(--pg-accent) 45%, var(--pg-line));
    border-bottom: 1px solid color-mix(in srgb, var(--pg-accent) 45%, var(--pg-line));
    transform: rotate(45deg);
  }
  /* Near the top of the window the bubble drops below Andy instead. */
  #andy.below .andy-bubble { bottom: auto; top: calc(100% + 13px); transform-origin: top center; }
  #andy.below .andy-bubble::after { bottom: auto; top: -6px;
    border-right: none; border-bottom: none;
    border-left: 1px solid color-mix(in srgb, var(--pg-accent) 45%, var(--pg-line));
    border-top: 1px solid color-mix(in srgb, var(--pg-accent) 45%, var(--pg-line)); }
  /* While Andy narrates, reserve a right-hand lane so he never covers the problem:
     the content shifts left and Andy flies vertically in the gutter beside it. */
  body.andy-on { padding-right: 232px; transition: padding-right .35s ease; }
  body.andy-on #wm { opacity: 0; }
  .andy-close { position: absolute; top: 3px; right: 7px; cursor: pointer;
    color: var(--pg-text-dim); font-size: 13px; line-height: 1; }
  .andy-close:hover { color: var(--pg-accent); }
  /* Step controls so the student can pace / re-read at will. */
  .andy-nav { display: flex; align-items: center; justify-content: space-between;
    gap: 8px; margin-top: 8px; padding-top: 7px;
    border-top: 1px solid var(--pg-line); }
  .andy-nav button { cursor: pointer; background: transparent;
    border: 1px solid var(--pg-line); color: var(--pg-text-dim);
    border-radius: 8px; padding: 1px 10px; font-size: 15px; line-height: 1.3;
    font-family: var(--pg-mono); }
  .andy-nav button:hover:not(:disabled) { color: var(--pg-accent); border-color: var(--pg-accent); }
  .andy-nav button:disabled { opacity: 0.32; cursor: default; }
  .andy-step { font-family: var(--pg-mono); font-size: 11px; color: var(--pg-text-faint); }
  .andy-caret { color: var(--pg-accent); animation: andy-blink 1s steps(1) infinite; }
  /* The choice/statement Andy is currently talking about lights up. */
  .pg-choice.andy-focus, #stmt.andy-focus {
    border-color: var(--pg-accent) !important;
    box-shadow: 0 0 0 1px var(--pg-accent), 0 0 20px var(--pg-accent-glow) !important;
    transition: box-shadow .3s ease, border-color .3s ease;
  }
  @keyframes andy-orbit { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
  @keyframes andy-bob { 0%, 100% { transform: translateY(-2.5px); } 50% { transform: translateY(2.5px); } }
  @keyframes andy-think { 0%, 100% { box-shadow: 0 0 10px var(--pg-accent-glow); }
    50% { box-shadow: 0 0 22px var(--pg-accent), 0 0 34px var(--pg-accent-glow); } }
  @keyframes andy-blink { 50% { opacity: 0; } }
  @media (prefers-reduced-motion: reduce) {
    #andy { transition: opacity 0.4s ease; }
    .andy-atom, .ao1 .andy-ew, .ao2 .andy-ew, .ao3 .andy-ew,
    #andy.thinking .andy-nuc, .andy-caret { animation: none; }
  }
</style>
<div class="pg-watermark" id="wm">ℏ ∮ ∇ ψ λ ∂</div>
<div id="hdr">
  <div id="progressWrap">
    <span id="progress" class="pg-eyebrow"></span>
    <div id="progressMeter"><div id="progressFill"></div></div>
  </div>
  <span id="score" class="pg-num"></span>
</div>
<div id="subject"><span id="subjectText"></span><span id="genPill" class="pg-badge">⚛ AI-generated</span></div>
<div id="stmt" class="pg-panel"></div>
<div id="choices"></div>
<div id="frq">
  <label id="frqLabel"></label>
  <textarea id="reason" placeholder="e.g. The choices span orders of magnitude, so I'd estimate…"></textarea>
</div>
<div id="feedback"></div>
<div id="summary" style="display:none"></div>
<script>
(function () {
  document.body.classList.add("pg-observatory");
  var DATA = (window.QUIZ_DATA || []).slice();
  var AI_ON = !!window.AI_ON;
  function shuffle(a) {
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
  }
  shuffle(DATA);  // randomises tie-breaks; the actual order is chosen adaptively below
  var answered = 0, correct = 0, locked = false;
  // Adaptive difficulty (Zone of Proximal Development): serve the unanswered
  // question whose 1-5 difficulty is closest to a running ability estimate that
  // rises on a correct answer and falls (faster) on a wrong one.
  var ability = 3.0, served = 0, cur = -1, used = {};
  var coachTimeout = null;  // safety net if AI grading never calls back
  function diffOf(q) { var d = q && q.difficulty; return (typeof d === "number" && d >= 1) ? d : 3; }
  function pickNext() {
    var best = 1e9, cands = [];
    for (var i = 0; i < DATA.length; i++) {
      if (used[i]) { continue; }
      var gap = Math.abs(diffOf(DATA[i]) - ability);
      if (gap < best - 1e-9) { best = gap; cands = [i]; }
      else if (gap < best + 1e-9) { cands.push(i); }
    }
    return cands.length ? cands[Math.floor(Math.random() * cands.length)] : -1;
  }

  function typeset(el) {
    if (window.MathJax && MathJax.typesetPromise) { MathJax.typesetPromise(el ? [el] : undefined); }
  }
  function esc(s) {
    return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function score() {
    document.getElementById("score").textContent =
      answered ? (correct + "/" + answered + " correct (" + Math.round(100 * correct / answered) + "%)") : "";
  }
  function render() {
    andyStop();
    cur = pickNext();
    if (cur < 0) { return done(); }
    used[cur] = true; served++;
    locked = false;
    var q = DATA[cur];
    document.getElementById("summary").style.display = "none";
    document.getElementById("feedback").innerHTML = "";
    document.getElementById("frq").style.display = "block";
    document.getElementById("frqLabel").textContent =
      AI_ON ? "How would you solve this? (type your approach — you'll get AI coaching on it)"
            : "How would you solve this? (jot your approach, then check it against the fastest route)";
    var ta = document.getElementById("reason");
    ta.value = ""; ta.disabled = false;
    document.getElementById("progress").textContent = "Q " + served + " / " + DATA.length;
    var pf = document.getElementById("progressFill");
    if (pf) { pf.style.width = (DATA.length ? (served / DATA.length) * 100 : 0) + "%"; }
    score();
    document.getElementById("subjectText").textContent = q.subject || "";
    // Badge AI-generated items only (real released questions have no pill).
    document.getElementById("genPill").style.display =
      q.source === "generated" ? "inline-block" : "none";
    document.getElementById("stmt").innerHTML = q.statement;
    var box = document.getElementById("choices");
    box.innerHTML = "";
    q.choices.forEach(function (c) {
      var b = document.createElement("button");
      b.className = "choice pg-choice"; b.dataset.letter = c[0];
      b.innerHTML = "<span class='lab'>" + c[0] + "</span>" + c[1];
      b.onclick = function () { choose(c[0]); };
      box.appendChild(b);
    });
    typeset();
  }
  function choose(letter) {
    if (locked) { return; }
    locked = true;
    var q = DATA[cur];
    var reasoning = document.getElementById("reason").value.trim();
    document.getElementById("reason").disabled = true;
    var ok = letter === q.answer;
    answered++; if (ok) { correct++; }
    // ZPD: climb on a correct answer, ease down (faster) on a miss.
    ability = ok ? Math.min(5, ability + 0.5) : Math.max(1, ability - 0.8);
    score();
    document.querySelectorAll(".choice").forEach(function (b) {
      b.disabled = true;
      if (b.dataset.letter === q.answer) { b.classList.add("correct"); }
      else if (b.dataset.letter === letter) { b.classList.add("wrong"); }
    });
    var html =
      "<div id='verdict'>" + (ok ? "✅ Correct" : "❌ Incorrect — answer is " + q.answer) + "</div>" +
      (q.solution ? "<div id='solution'>" + q.solution + "</div>" : "");
    // Always show the fastest expert approach (from the key; no network needed).
    if (q.optimal && q.optimal.explanation) {
      html += "<div class='pg-card pg-card--fast' id='fast'><div class='t'>⚡ Fastest approach</div>" +
              "<div>" + q.optimal.explanation + "</div></div>";
    }
    // Personalised AI coaching only when a key is present AND the student wrote something.
    if (AI_ON && reasoning) {
      html += "<div class='pg-card pg-card--coach' id='coach'><div class='t'>🧠 Coaching your approach…</div>" +
              "<div class='muted'>Grading how you tackled it…</div></div>";
    }
    html += "<button class='pg-btn' id='andyBtn' style='margin-right:8px'>⚛ Explain with Andy</button>";
    html += "<button class='pg-btn pg-btn--primary' id='nextBtn'>Next question →</button>";
    var fb = document.getElementById("feedback");
    fb.innerHTML = html;
    document.getElementById("nextBtn").onclick = function () { render(); };
    document.getElementById("andyBtn").onclick = function () { andyExplain(DATA[cur]); };
    typeset(fb);
    if (AI_ON && reasoning) {
      pycmd("grade:" + JSON.stringify({ id: q.id, chosen: letter, reasoning: reasoning }));
      // Safety net: if grading never calls back (hang/offline), show the fallback.
      coachTimeout = setTimeout(function () { window.showCoach({ ok: false }); }, 25000);
    }
  }
  // Called from Python (heuristic_coach.grade) with the coaching result.
  window.showCoach = function (res) {
    var coach = document.getElementById("coach");
    if (!coach) { return; }
    if (coachTimeout) { clearTimeout(coachTimeout); coachTimeout = null; }
    if (!res || !res.ok) {
      // AI coaching unavailable (no key / offline / error / timed out): keep the
      // card but explain, and point to the always-present fastest-approach fallback.
      var hasFast = !!document.getElementById("fast");
      coach.innerHTML =
        "<div class='t'>🧠 Your approach</div>" +
        "<div class='muted'>AI coaching isn't available right now" +
        (hasFast ? " — see the ⚡ Fastest approach above for the quickest route." : ".") +
        "</div>";
      return;
    }
    var badges = {
      optimal:      ["⚡ Optimal approach", "pg-badge--optimal"],
      valid_slower: ["✅ Valid — a faster route exists", "pg-badge--valid"],
      overcomputed: ["🧮 You over-solved it", "pg-badge--over"],
      guessed:      ["🎲 Let's make it rigorous", "pg-badge--guess"],
      flawed:       ["⚠️ Reasoning slip", "pg-badge--flaw"]
    };
    var b = badges[res.verdict];
    var inner = "<div class='t'>🧠 Your approach</div>";
    if (b) { inner += "<span class='pg-badge " + b[1] + "'>" + b[0] + "</span>"; }
    inner += "<div>" + esc(res.feedback) + "</div>";
    if (res.missed && res.missed.length) {
      inner += "<ul class='missed'>";
      res.missed.forEach(function (m) { inner += "<li>" + esc(m) + "</li>"; });
      inner += "</ul>";
    }
    coach.innerHTML = inner;
    typeset(coach);
  };
  function done() {
    document.getElementById("stmt").innerHTML = "";
    document.getElementById("choices").innerHTML = "";
    document.getElementById("feedback").innerHTML = "";
    document.getElementById("frq").style.display = "none";
    document.getElementById("subjectText").textContent = "";
    document.getElementById("genPill").style.display = "none";
    document.getElementById("progress").textContent = "Finished";
    var pf = document.getElementById("progressFill");
    if (pf) { pf.style.width = "100%"; }
    document.getElementById("score").textContent = "";
    var sm = document.getElementById("summary");
    sm.style.display = "block";
    var pct = answered ? Math.round(100 * correct / answered) : 0;
    sm.innerHTML =
      "<div class='pg-eyebrow'>Performance on real GR9277 questions</div>" +
      "<div class='big pg-num'>" + pct + "%</div>" +
      "<div>" + correct + " / " + answered + " correct</div>" +
      "<button class='pg-btn pg-btn--primary' id='againBtn'>Try again</button>";
    document.getElementById("againBtn").onclick = function () {
      shuffle(DATA); used = {}; served = 0; ability = 3.0; answered = 0; correct = 0; render();
    };
  }

  // ---- Andy the atom: flies around the problem and narrates the fastest
  // solution step by step. Steps come from the AI (window.showAndySteps) when a
  // key is present, else from a client-side script derived from the baked
  // optimal-approach key — so Andy always works, online or off.
  var andyEl = null, andyBubble = null, andyPlaying = false, andyPending = false;
  var andyTimers = [], andyReduced = false;
  var andySteps = [], andyIdx = 0, andyManual = false;
  try {
    andyReduced = window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch (e) {}

  function andyClearTimers() {
    andyTimers.forEach(function (t) { clearTimeout(t); });
    andyTimers = [];
  }
  function andyLater(fn, ms) { var t = setTimeout(fn, ms); andyTimers.push(t); return t; }

  function andyMake() {
    if (andyEl) { return; }
    andyEl = document.createElement("div");
    andyEl.id = "andy";
    andyEl.innerHTML =
      '<div class="andy-atom">' +
        '<span class="andy-orbit ao1"><span class="andy-ew"><i class="andy-e"></i></span></span>' +
        '<span class="andy-orbit ao2"><span class="andy-ew"><i class="andy-e"></i></span></span>' +
        '<span class="andy-orbit ao3"><span class="andy-ew"><i class="andy-e"></i></span></span>' +
        '<span class="andy-nuc"><span class="andy-eye l"></span><span class="andy-eye r"></span></span>' +
      '</div>' +
      '<div class="andy-bubble" id="andyBubble"><span class="andy-close" id="andyClose">✕</span>' +
      '<span id="andyText"></span>' +
      '<div class="andy-nav" id="andyNav" style="display:none">' +
        '<button id="andyPrev" title="Back — re-read the previous step">‹</button>' +
        '<span class="andy-step" id="andyStep"></span>' +
        '<button id="andyNext" title="Next step">›</button>' +
      '</div></div>';
    document.body.appendChild(andyEl);
    andyBubble = document.getElementById("andyBubble");
    document.getElementById("andyClose").onclick = andyStop;
    // Manual pacing: stepping takes Andy out of auto-advance so the student can
    // linger / re-read. Buttons stop propagating so the bubble stays put.
    document.getElementById("andyPrev").onclick = function () { andyStepBy(-1); };
    document.getElementById("andyNext").onclick = function () { andyStepBy(1); };
  }

  function andyTargetEl(focus) {
    if (focus === "stem") { return document.getElementById("stmt"); }
    var q = DATA[cur];
    if (focus === "answer") { focus = q && q.answer; }
    if (focus) {
      var list = document.querySelectorAll(".choice");
      for (var i = 0; i < list.length; i++) {
        if (list[i].dataset.letter === focus) { return list[i]; }
      }
    }
    return document.getElementById("stmt");
  }
  function andyClearFocus() {
    document.querySelectorAll(".andy-focus").forEach(function (e) {
      e.classList.remove("andy-focus");
    });
  }
  // Andy lives in the reserved right-hand lane (body.andy-on shifts the content
  // left). He never covers the text: he only slides VERTICALLY to sit beside the
  // element he's talking about, and that element lights up (.andy-focus) so it's
  // clear what he's pointing at. The bubble docks above/below him, inside the lane.
  function andyFlyTo(el) {
    andyClearFocus();
    var laneX = window.innerWidth - 116;  // centre of the ~232px lane
    var y;
    if (el) {
      var r = el.getBoundingClientRect();
      y = r.top + r.height / 2;
      el.classList.add("andy-focus");
    } else { y = 150; }
    y = Math.max(56, Math.min(window.innerHeight - 56, y));
    // Bubble sits above Andy, unless he's near the top — then it drops below.
    andyEl.classList.toggle("below", y < 150);
    andyEl.style.left = laneX + "px";
    andyEl.style.top = y + "px";
  }

  function andyTrySpeak(text) {
    try {
      if (!window.speechSynthesis) { return; }
      window.speechSynthesis.cancel();
      var u = new SpeechSynthesisUtterance(text);
      u.rate = 1.03; u.pitch = 1.18; u.volume = 1;
      window.speechSynthesis.speak(u);
    } catch (e) {}
  }
  function andyStopSpeak() {
    try { if (window.speechSynthesis) { window.speechSynthesis.cancel(); } } catch (e) {}
  }

  function andyType(text, done) {
    var el = document.getElementById("andyText");
    andyBubble.classList.add("show");
    andyTrySpeak(text);
    if (andyReduced) { el.textContent = text; if (done) { andyLater(done, 10); } return; }
    var i = 0;
    (function tick() {
      if (!andyPlaying) { return; }
      el.innerHTML = esc(text.slice(0, i)) + "<span class='andy-caret'>▋</span>";
      if (i < text.length) { i++; andyLater(tick, 20); }
      else { el.textContent = text; if (done) { done(); } }
    })();
  }

  function andyShowNav(on) {
    var n = document.getElementById("andyNav");
    if (n) { n.style.display = on ? "flex" : "none"; }
  }
  function andyUpdateNav() {
    var p = document.getElementById("andyPrev"), nx = document.getElementById("andyNext");
    var st = document.getElementById("andyStep");
    if (st) { st.textContent = (andyIdx + 1) + " / " + andySteps.length; }
    if (p) { p.disabled = andyIdx <= 0; }
    if (nx) { nx.disabled = andyIdx >= andySteps.length - 1; }
  }
  // Render step `i`: fly Andy beside its element, type the line, and — unless the
  // student has taken manual control — auto-advance to the next after a beat.
  function andyRenderStep(i) {
    if (!andyPlaying || i < 0 || i >= andySteps.length) { return; }
    andyClearTimers();
    andyIdx = i;
    andyUpdateNav();
    var s = andySteps[i];
    var el = andyTargetEl(s.focus);
    if (el && el.scrollIntoView) { el.scrollIntoView({ block: "center", behavior: "smooth" }); }
    andyLater(function () {
      if (!andyPlaying) { return; }
      andyFlyTo(el);
      andyLater(function () {
        andyType(s.say, function () {
          if (andyManual) { return; }               // student is pacing it themselves
          if (andyIdx < andySteps.length - 1) {
            andyLater(function () { andyRenderStep(andyIdx + 1); },
              Math.min(4200, 1100 + s.say.length * 42));
          }
        });
      }, 520);
    }, 220);
  }
  // Prev/Next: the student takes the wheel (auto-advance stops) and can re-read.
  function andyStepBy(delta) {
    andyManual = true;
    andyStopSpeak();
    andyRenderStep(andyIdx + delta);
  }
  function andyPlay(steps) {
    andyMake();
    andyClearTimers();
    andyEl.classList.remove("thinking");
    andyEl.classList.add("show");
    andyPlaying = true;
    andyManual = false;
    andySteps = steps;
    andyIdx = 0;
    andyShowNav(steps.length > 1);  // no controls needed for a single-line answer
    andyRenderStep(0);
  }
  // When Andy genuinely has nothing to explain (AI unavailable AND no baked key),
  // he says so and flies off rather than faking an answer.
  function andyExcuse() {
    andyMake();
    andyClearTimers();
    andyEl.classList.remove("thinking");
    andyEl.classList.add("show");
    andyPlaying = true;
    andyManual = true;
    andySteps = [];
    andyShowNav(false);
    andyClearFocus();
    andyFlyTo(andyTargetEl("stem"));
    andyType("Hmm — I can't crack this one right now. Catch you on the next one!",
      function () { andyLater(andyStop, 2800); });  // then fly off
  }

  function stripMath(s) {
    return (s || "")
      .replace(/\\\((.+?)\\\)/g, "$1").replace(/\\\[(.+?)\\\]/g, "$1")
      .replace(/[$]/g, "").replace(/\\[a-zA-Z]+/g, "").replace(/[{}]/g, "")
      .replace(/\s+/g, " ").trim();
  }
  // Which part of the problem a sentence is about: the choice it names (or the
  // answer, if that's the letter it names), else the stem. Lets the offline
  // narration point Andy at the right place without any AI focus tags.
  function andyFocusOf(sentence, answer) {
    var m = sentence.match(/\(([A-E])\)/g);
    if (m && m.length) {
      var last = m[m.length - 1].charAt(1);
      if (m.length === 1 && last === answer) { return "answer"; }
      return last;
    }
    return "stem";
  }
  // Offline script: narrate the SAME fastest-route explanation the ⚡ card shows,
  // as if solving live — sentence by sentence. Because that text already reflects
  // the optimal method, a direct-solve route is narrated directly (no forced POE);
  // an elimination route naturally walks the choices.
  function andyFallbackSteps(q) {
    var steps = [], o = q && q.optimal, ans = q.answer;
    if (o && o.explanation) {
      stripMath(o.explanation).split(/(?<=[.!?])\s+/).forEach(function (s) {
        s = s.trim();
        if (s) { steps.push({ say: s, focus: andyFocusOf(s, ans) }); }
      });
    } else if (o && o.eliminations && o.eliminations.length) {
      o.eliminations.forEach(function (e) {
        var reason = stripMath(e[1]);
        if (reason) { steps.push({ say: "Rule out (" + e[0] + "): " + reason, focus: e[0] }); }
      });
    }
    // Always land on the answer (unless the last line already did).
    if (!steps.length || steps[steps.length - 1].focus !== "answer") {
      steps.push({ say: "So the fastest route lands on (" + ans + ").", focus: "answer" });
    }
    return steps;
  }
  function andyHasMaterial(q) {
    var o = q && q.optimal;
    return !!(o && ((o.explanation && o.explanation.trim()) ||
      (o.eliminations && o.eliminations.length)));
  }
  // Decide what to play once a result (or failure) is known: AI steps > baked
  // fastest-route narration > an honest "can't help" excuse.
  function andyResolve(res, q) {
    if (res && res.ok && res.steps && res.steps.length) { andyPlay(res.steps); }
    else if (andyHasMaterial(q)) { andyPlay(andyFallbackSteps(q)); }
    else { andyExcuse(); }
  }

  function andyExplain(q) {
    if (!q) { return; }
    andyMake();
    andyClearTimers();
    andyPlaying = true;
    document.body.classList.add("andy-on");  // reserve the right lane
    andyEl.classList.add("show", "thinking");
    andyClearFocus();
    andyFlyTo(andyTargetEl("stem"));
    andyBubble.classList.add("show");
    document.getElementById("andyText").textContent = "Let me find the fast route…";
    if (AI_ON) {
      andyPending = true;
      pycmd("explain:" + JSON.stringify({ id: q.id }));
      // Safety net: if the AI key fails / never calls back, Andy keeps "thinking"
      // this long, then narrates the baked route (or excuses himself if there's
      // nothing baked either).
      andyLater(function () {
        if (andyPending) { andyPending = false; andyResolve({ ok: false }, q); }
      }, 20000);
    } else {
      andyLater(function () { andyResolve({ ok: false }, q); }, 650);
    }
  }
  // Called from Python with Andy's AI-authored script (or ok:false to fall back).
  window.showAndySteps = function (res) {
    if (!andyPending) { return; }
    andyPending = false;
    andyResolve(res, DATA[cur]);
  };
  function andyStop() {
    andyPlaying = false; andyPending = false;
    andyClearTimers(); andyStopSpeak(); andyClearFocus();
    document.body.classList.remove("andy-on");  // release the lane, content reflows back
    if (andyEl) {
      andyEl.classList.remove("show", "thinking", "below");
      if (andyBubble) { andyBubble.classList.remove("show"); }
      andyEl.style.top = "-90px";
    }
  }

  if (!DATA.length) {
    document.getElementById("stmt").textContent = "No questions available.";
    document.getElementById("frq").style.display = "none";
  } else {
    render();
  }
})();
</script>
"""
