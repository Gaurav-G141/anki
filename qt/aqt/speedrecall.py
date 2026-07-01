# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Speed Recall (Physics GRE fork).

A latency-driven formula-drill mode. Cards from the 9 ``PGRE::<subject>`` decks
are **interleaved** (round-robin across subjects, per the Brainlift: "interleaved
formulas in drilling mode are non-negotiable") and shown one at a time; the user
recalls the formula as fast as possible.

It behaves like normal flashcards with one twist: **how long you take to recall
modulates the next interval.** A quick recall earns the full interval for the
grade you pick; a slow one shrinks it, so hard-to-recall cards come back sooner.
Example (grade = Easy): recall in a few seconds → ~1 week; recall taking over a
minute → ~12 hours.

This mode keeps its **own** schedule (in collection config), so it never touches
FSRS memory state / real card due dates — the Memory dashboard is unaffected.

The GUI-free bits (the latency→interval curve, the schedule store, and the
interleaved queue builder) live at module top and are unit-tested in
``qt/tests/test_speedrecall.py`` against a bare ``Collection``.
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from typing import Any

from anki.cards import Card, CardId
from anki.collection import Collection
from aqt import AnkiQt

# ---------------------------------------------------------------------------
# Scheduling: latency-modulated intervals (pure, testable)
# ---------------------------------------------------------------------------

#: Recall at/under this many seconds earns the full interval for the grade.
FAST_SECONDS = 5.0
#: Recall at/over this many seconds is clamped to the floor multiplier.
SLOW_SECONDS = 60.0
#: The smallest fraction of the base interval a slow recall can earn.
SLOW_FLOOR = 0.07

#: Base interval per grade, in hours. Again is fixed-short and latency-independent
#: (it always comes back within the session soon). Hard/Good/Easy scale with
#: recall latency. Easy's 168 h (1 week) × the 0.07 floor ≈ 12 h — matching the
#: product spec: fast Easy ≈ 1 week, slow (>1 min) Easy ≈ 12 hours.
BASE_HOURS: dict[int, float] = {
    1: 1.0 / 6.0,  # Again  → ~10 minutes
    2: 24.0,  # Hard   → 1 day  (fast) … ~1.7 h (slow)
    3: 72.0,  # Good   → 3 days (fast) … ~5 h  (slow)
    4: 168.0,  # Easy   → 1 week (fast) … ~12 h (slow)
}

#: Legacy collection-config key: the old single-JSON-blob schedule (still read
#: for backward compatibility / migration-on-read).
SCHED_KEY = "speedRecallSched"
#: Per-card config-key prefix, e.g. ``speedRecall:sched:<card_id>``. Each answer
#: writes one row (O(1)) instead of rewriting a growing blob (was O(n) -> O(n^2)).
SCHED_PREFIX = "speedRecall:sched:"
#: Preferred source: the dedicated formula deck (built from Conquering the
#: Physics GRE's equation index). Falls back to the ``PGRE::`` subject decks if
#: the formula deck isn't present.
SR_ROOT = "Speed Recall"
#: Deck-name prefix of the bundled subject decks (see ``aqt.pgre``).
DECK_ROOT = "PGRE"


def latency_factor(seconds: float) -> float:
    """Return the interval multiplier in ``[SLOW_FLOOR, 1.0]`` for a recall time.

    1.0 at/under :data:`FAST_SECONDS`, :data:`SLOW_FLOOR` at/over
    :data:`SLOW_SECONDS`, linear in between. Monotonically non-increasing.
    """
    if seconds <= FAST_SECONDS:
        return 1.0
    if seconds >= SLOW_SECONDS:
        return SLOW_FLOOR
    frac = (seconds - FAST_SECONDS) / (SLOW_SECONDS - FAST_SECONDS)
    return 1.0 - frac * (1.0 - SLOW_FLOOR)


def next_interval_hours(rating: int, seconds: float) -> float:
    """Next interval (hours) for a grade given how long recall took.

    ``rating`` is 1=Again, 2=Hard, 3=Good, 4=Easy. Again ignores latency.
    """
    if rating not in BASE_HOURS:
        raise ValueError(f"rating must be 1..4, got {rating!r}")
    if rating == 1:
        return BASE_HOURS[1]
    return BASE_HOURS[rating] * latency_factor(seconds)


def format_interval(hours: float) -> str:
    """Human label for a button, e.g. ``10m`` / ``12h`` / ``7d``."""
    if hours < 1.0:
        return f"{round(hours * 60)}m"
    if hours < 24.0:
        return f"{round(hours)}h"
    days = hours / 24.0
    return f"{days:.0f}d" if abs(days - round(days)) < 0.05 else f"{days:.1f}d"


# ---------------------------------------------------------------------------
# Schedule store (per-collection, in config; independent of FSRS)
# ---------------------------------------------------------------------------


def _card_key(card_id: int) -> str:
    """Per-card config key, e.g. ``speedRecall:sched:1234``."""
    return f"{SCHED_PREFIX}{int(card_id)}"


def _load_sched(col: Collection) -> dict[int, dict[str, float]]:
    """All schedule entries as ``{card_id: {"due", "ivl_h"}}``.

    Reads the per-card config keys (each written in O(1)) and merges any entries
    from the **legacy** single-blob ``speedRecallSched`` key so collections
    written by the old code keep working (migrate-on-write happens naturally as
    those cards are answered again).
    """
    out: dict[int, dict[str, float]] = {}
    legacy = col.get_config(SCHED_KEY, None)
    if isinstance(legacy, dict):
        for k, v in legacy.items():
            try:
                out[int(k)] = v
            except (ValueError, TypeError):
                continue
    prefix = SCHED_PREFIX
    for key in col.db.list("select key from config where key like ?", f"{prefix}%"):
        try:
            cid = int(key[len(prefix) :])
        except ValueError:
            continue
        rec = col.get_config(key, None)
        if isinstance(rec, dict):
            out[cid] = rec
    return out


def record_answer(
    col: Collection, card_id: int, rating: int, seconds: float, now: float | None = None
) -> float:
    """Persist the next speed-recall due time for a card. Returns interval hours.

    Writes a single per-card config row (O(1)) rather than rewriting a growing
    JSON blob, so recording N answers is O(N), not O(N^2).
    """
    now = time.time() if now is None else now
    ivl_h = next_interval_hours(rating, seconds)
    col.set_config(_card_key(card_id), {"due": now + ivl_h * 3600.0, "ivl_h": ivl_h})
    return ivl_h


def due_card_ids(col: Collection, now: float | None = None) -> set[int]:
    """Card ids whose speed-recall due time has arrived (or were never seen)."""
    now = time.time() if now is None else now
    return {cid for cid, rec in _load_sched(col).items() if rec.get("due", 0) <= now}


# ---------------------------------------------------------------------------
# Interleaved queue across the 9 PGRE subject decks
# ---------------------------------------------------------------------------


def subject_deck_names(col: Collection) -> list[str]:
    """Per-subject child deck names to interleave, in a stable order.

    Prefers the dedicated ``Speed Recall::<subject>`` formula deck; falls back to
    the ``PGRE::<subject>`` subject decks when the formula deck isn't present.
    """
    names = [
        d.name.replace("\x1f", "::")
        for d in col.decks.all_names_and_ids(skip_empty_default=True)
    ]
    for root in (SR_ROOT, DECK_ROOT):
        matches = sorted(n for n in names if n.startswith(f"{root}::"))
        if matches:
            return matches
    return []


def build_queue(
    col: Collection,
    limit: int = 60,
    now: float | None = None,
    rng: random.Random | None = None,
) -> list[CardId]:
    """Interleave due speed-recall cards round-robin across the 9 subjects.

    Cards never seen in speed-recall count as due. If nothing is due, fall back
    to all cards (free practice) so a session is never empty. Consecutive cards
    are from different subjects wherever possible.
    """
    rng = rng or random.Random()
    now = time.time() if now is None else now
    sched = _load_sched(col)
    seen = set(sched)

    def card_due(cid: int) -> bool:
        rec = sched.get(int(cid))
        return rec is None or rec.get("due", 0) <= now

    per_subject: list[list[CardId]] = []
    for name in subject_deck_names(col):
        cids = list(col.find_cards(f'deck:"{name}"'))
        rng.shuffle(cids)
        due = [c for c in cids if card_due(c)]
        per_subject.append(due if due else ([] if seen else cids))
    # If genuinely nothing is due anywhere, allow all cards for free practice.
    if not any(per_subject):
        per_subject = []
        for name in subject_deck_names(col):
            cids = list(col.find_cards(f'deck:"{name}"'))
            rng.shuffle(cids)
            per_subject.append(cids)

    # Round-robin interleave.
    out: list[CardId] = []
    idx = 0
    while len(out) < limit and any(idx < len(s) for s in per_subject):
        for s in per_subject:
            if idx < len(s):
                out.append(s[idx])
                if len(out) >= limit:
                    break
        idx += 1
    return out


# ---------------------------------------------------------------------------
# GUI screen (mirrors aqt.deckbrowser / aqt.manifold: a webview + pycmd bridge)
# ---------------------------------------------------------------------------


@dataclass
class _Current:
    card: Card
    subject: str
    shown_at: float


class SpeedRecall:
    """The Speed Recall session screen."""

    def __init__(self, mw: AnkiQt) -> None:
        self.mw = mw
        self.web = mw.web
        self._queue: list[CardId] = []
        self._pos = 0
        self._done = 0
        self._current: _Current | None = None

    def show(self) -> None:
        self.web.set_bridge_command(self._link_handler, self)
        self.mw.toolbar.redraw()
        self._queue = build_queue(self.mw.col)
        self._pos = 0
        self._done = 0
        self._init_web()
        self._next_card()

    # -- webview bootstrap (reuse Anki's card CSS + MathJax) ----------------

    def _init_web(self) -> None:
        self.web.stdHtml(
            _PAGE_HTML,
            css=["css/reviewer.css"],
            js=[
                "js/mathjax.js",
                "js/vendor/mathjax/tex-chtml-full.js",
            ],
            context=self,
        )

    # -- session flow ------------------------------------------------------

    def _subject_of(self, card: Card) -> str:
        name = self.mw.col.decks.name(card.did).replace("\x1f", "::")
        return name.split("::", 1)[1] if "::" in name else name

    def _next_card(self) -> None:
        if self._pos >= len(self._queue):
            self._finish()
            return
        cid = self._queue[self._pos]
        self._pos += 1
        try:
            card = self.mw.col.get_card(cid)
        except Exception:
            self._next_card()
            return
        card.render_output(reload=True)
        self._current = _Current(
            card=card, subject=self._subject_of(card), shown_at=time.time()
        )
        q = self.mw.prepare_card_text_for_display(card.question())
        payload = {
            "front": q,
            "subject": self._subject_of(card),
            "done": self._done,
            "remaining": len(self._queue) - self._pos + 1,
        }
        self.web.eval(f"speedShowFront({json.dumps(payload)});")

    def _reveal(self, elapsed_ms: float) -> None:
        if not self._current:
            return
        seconds = max(0.0, elapsed_ms / 1000.0)
        card = self._current.card
        a = self.mw.prepare_card_text_for_display(card.answer())
        labels = {
            r: format_interval(next_interval_hours(r, seconds)) for r in (1, 2, 3, 4)
        }
        self.web.eval(f"speedShowBack({json.dumps(a)}, {json.dumps(labels)});")

    def _rate(self, rating: int, elapsed_ms: float) -> None:
        if not self._current:
            return
        seconds = max(0.0, elapsed_ms / 1000.0)
        record_answer(self.mw.col, int(self._current.card.id), rating, seconds)
        self._done += 1
        self._current = None
        self._next_card()

    def _finish(self) -> None:
        self.web.eval(f"speedFinish({json.dumps(self._done)});")

    def _close(self) -> None:
        self.mw.moveToState("manifold")

    # -- bridge ------------------------------------------------------------

    def _link_handler(self, url: str) -> Any:
        cmd, _, arg = url.partition(":")
        if cmd == "show":
            self._reveal(float(arg or 0))
        elif cmd == "rate":
            rating_s, _, ms_s = arg.partition(":")
            self._rate(int(rating_s), float(ms_s or 0))
        elif cmd == "again":
            self._next_card()
        elif cmd == "close":
            self._close()
        return False

    def op_executed(self, changes: Any, handler: object | None, focused: bool) -> bool:
        return False


# The page is intentionally self-contained: a timer, a card area, a Show Answer
# button, and four grade buttons. Keyboard: Space = show / then Good; 1-4 = grade.
_PAGE_HTML = r"""
<style>
  #sr-wrap { max-width: 700px; margin: 0 auto; padding: 12px; text-align: center;
             font-family: var(--font, sans-serif); }
  #sr-head { display: flex; justify-content: space-between; align-items: center;
             font-size: 13px; opacity: 0.8; margin-bottom: 8px; }
  #sr-timer { font-variant-numeric: tabular-nums; font-weight: 600; }
  #sr-subject { font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em;
                opacity: 0.7; margin-bottom: 6px; }
  #sr-card { min-height: 140px; font-size: 22px; display: flex; align-items: center;
             justify-content: center; padding: 16px; }
  #sr-controls { margin-top: 18px; }
  #sr-controls button { font-size: 15px; padding: 8px 14px; margin: 0 4px; cursor: pointer; }
  .sr-grade small { display:block; opacity:0.7; font-size:11px; }
  #sr-close { position: fixed; top: 8px; right: 12px; opacity: 0.6; font-size: 12px; }
  .sr-hr { border:0; border-top:1px solid rgba(128,128,128,0.3); margin:14px 0; }
</style>
<a id="sr-close" href="#" onclick="pycmd('close');return false;">✕ Done (Esc)</a>
<div id="sr-wrap">
  <div id="sr-head">
    <span id="sr-progress"></span>
    <span>⚡ Speed Recall — recall the formula fast!</span>
    <span id="sr-timer">0.0s</span>
  </div>
  <div id="sr-subject"></div>
  <div id="sr-card">Loading…</div>
  <div id="sr-controls"></div>
</div>
<script>
let srStart = 0, srTimerId = null, srElapsedMs = 0, srRevealed = false;

function srTick() {
  const ms = performance.now() - srStart;
  document.getElementById('sr-timer').textContent = (ms/1000).toFixed(1) + 's';
}
function srStopTimer() { if (srTimerId) { clearInterval(srTimerId); srTimerId = null; } }

function srTypeset() {
  try { if (globalThis.MathJax && MathJax.typesetPromise) MathJax.typesetPromise(); } catch(e){}
}

function speedShowFront(p) {
  srRevealed = false; srElapsedMs = 0;
  document.getElementById('sr-progress').textContent =
      'done ' + p.done + ' · left ' + p.remaining;
  document.getElementById('sr-subject').textContent = p.subject;
  document.getElementById('sr-card').innerHTML = '<div class="card">' + p.front + '</div>';
  document.getElementById('sr-controls').innerHTML =
      '<button onclick="srReveal()">Show Answer <small>(space)</small></button>';
  srTypeset();
  srStart = performance.now();
  srStopTimer();
  srTimerId = setInterval(srTick, 100);
}

function srReveal() {
  if (srRevealed) return;
  srRevealed = true;
  srElapsedMs = performance.now() - srStart;
  srStopTimer();
  document.getElementById('sr-timer').textContent = (srElapsedMs/1000).toFixed(1) + 's';
  pycmd('show:' + Math.round(srElapsedMs));
}

function speedShowBack(answerHtml, labels) {
  document.getElementById('sr-card').innerHTML =
      '<div class="card">' + answerHtml + '</div>';
  const g = [[1,'Again'],[2,'Hard'],[3,'Good'],[4,'Easy']];
  let buf = '';
  for (const [n,name] of g) {
    buf += '<button class="sr-grade" onclick="srRate('+n+')">'+name+
           '<small>'+labels[n]+' ('+n+')</small></button>';
  }
  document.getElementById('sr-controls').innerHTML = buf;
  srTypeset();
}

function srRate(n) {
  if (!srRevealed) return;
  pycmd('rate:' + n + ':' + Math.round(srElapsedMs));
}

function speedFinish(done) {
  srStopTimer();
  document.getElementById('sr-subject').textContent = '';
  document.getElementById('sr-timer').textContent = '';
  document.getElementById('sr-progress').textContent = '';
  document.getElementById('sr-card').innerHTML =
      '<div><h2>Session complete ⚡</h2><p>You drilled ' + done +
      ' formula' + (done===1?'':'s') + '.</p></div>';
  document.getElementById('sr-controls').innerHTML =
      '<button onclick="pycmd(\'close\')">Back to home</button>';
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') { pycmd('close'); return; }
  if (!srRevealed) {
    if (e.code === 'Space' || e.key === 'Enter') { e.preventDefault(); srReveal(); }
    return;
  }
  if (e.key === ' ' || e.code === 'Space') { e.preventDefault(); srRate(3); }
  else if (['1','2','3','4'].includes(e.key)) { e.preventDefault(); srRate(parseInt(e.key)); }
});
</script>
"""
