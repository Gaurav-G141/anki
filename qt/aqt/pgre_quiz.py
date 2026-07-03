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
        self.setWindowTitle("Practice MCQs — Physics GRE")
        disable_help_button(self)
        self.setMinimumSize(600, 560)
        restoreGeom(self, self.name, default_size=(860, 780))

        try:
            questions = load_questions()
        except Exception:
            questions = []

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
        """Bridge handler: JS asks us to grade a typed approach."""
        if msg.startswith("grade:"):
            self._grade(msg[len("grade:") :])
        return False

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
_QUIZ_PAGE = """
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
  shuffle(DATA);
  var idx = 0, answered = 0, correct = 0, locked = false;

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
    if (idx >= DATA.length) { return done(); }
    locked = false;
    var q = DATA[idx];
    document.getElementById("summary").style.display = "none";
    document.getElementById("feedback").innerHTML = "";
    document.getElementById("frq").style.display = "block";
    document.getElementById("frqLabel").textContent =
      AI_ON ? "How would you solve this? (type your approach — you'll get AI coaching on it)"
            : "How would you solve this? (jot your approach, then check it against the fastest route)";
    var ta = document.getElementById("reason");
    ta.value = ""; ta.disabled = false;
    document.getElementById("progress").textContent = "Q " + (idx + 1) + " / " + DATA.length;
    var pf = document.getElementById("progressFill");
    if (pf) { pf.style.width = (DATA.length ? ((idx + 1) / DATA.length) * 100 : 0) + "%"; }
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
    var q = DATA[idx];
    var reasoning = document.getElementById("reason").value.trim();
    document.getElementById("reason").disabled = true;
    var ok = letter === q.answer;
    answered++; if (ok) { correct++; }
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
    html += "<button class='pg-btn pg-btn--primary' id='nextBtn'>Next question →</button>";
    var fb = document.getElementById("feedback");
    fb.innerHTML = html;
    document.getElementById("nextBtn").onclick = function () { idx++; render(); };
    typeset(fb);
    if (AI_ON && reasoning) {
      pycmd("grade:" + JSON.stringify({ id: q.id, chosen: letter, reasoning: reasoning }));
    }
  }
  // Called from Python (heuristic_coach.grade) with the coaching result.
  window.showCoach = function (res) {
    var coach = document.getElementById("coach");
    if (!coach) { return; }
    if (!res || !res.ok) {
      coach.parentNode.removeChild(coach);  // fall back to the fastest-approach card above
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
      shuffle(DATA); idx = 0; answered = 0; correct = 0; render();
    };
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
