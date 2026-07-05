# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Tests for the network-free paths of the Stage-2 AI heuristic coach.

Covers "Explain with Andy" (the spoken step-by-step solver narration): the
prompt is faithful, the model output is parsed robustly, and the whole thing
degrades to ``ok=False`` with no key — all without touching the network (the
one model call, ``_chat_json``, is stubbed)."""

from __future__ import annotations

from aqt import heuristic_coach


def _question() -> dict:
    return {
        "id": "GR9277#1",
        "statement": "A particle moves in a circle of radius R at speed v.",
        "choices": [
            ["A", "0"],
            ["B", "v^2/R"],
            ["C", "v/R"],
            ["D", "mv^2/R"],
            ["E", "mvR"],
        ],
        "answer": "B",
    }


# -- _parse_steps: robust normalisation of the model's steps ------------------


def test_parse_steps_objects_and_strings():
    out = {
        "steps": [
            {"say": "First, check the units.", "focus": "stem"},
            {"say": "Only (B) has units of acceleration.", "focus": "B"},
            "So it's (B).",  # bare string is accepted; focus defaults to ""
        ]
    }
    steps = heuristic_coach._parse_steps(out)
    assert [s["say"] for s in steps] == [
        "First, check the units.",
        "Only (B) has units of acceleration.",
        "So it's (B).",
    ]
    assert [s["focus"] for s in steps] == ["stem", "B", ""]


def test_parse_steps_drops_empty_and_bad_focus():
    out = {
        "steps": [
            {"say": "   ", "focus": "stem"},  # empty say -> dropped
            {"say": "Real step.", "focus": "Z"},  # bad focus -> coerced to ""
            {"say": "Answer.", "focus": "answer"},
        ]
    }
    steps = heuristic_coach._parse_steps(out)
    assert len(steps) == 2
    assert steps[0] == {"say": "Real step.", "focus": ""}
    assert steps[1]["focus"] == "answer"


def test_parse_steps_empty_when_missing():
    assert heuristic_coach._parse_steps({}) == []
    assert heuristic_coach._parse_steps({"steps": []}) == []


# -- _explain_messages: the prompt carries the problem + the answer -----------


def test_explain_messages_are_faithful():
    msgs = heuristic_coach._explain_messages(_question())
    system = next(m["content"] for m in msgs if m["role"] == "system")
    user = next(m["content"] for m in msgs if m["role"] == "user")
    assert "Andy" in system
    assert "A particle moves in a circle" in user
    assert "(B) v^2/R" in user
    assert "CORRECT ANSWER: B" in user
    # Grounded in the validated optimal-approach key.
    assert "OPTIMAL APPROACH" in user


# -- explain_steps: degrades with no key; parses a stubbed success ------------


def test_explain_steps_no_key_is_unavailable(monkeypatch):
    monkeypatch.setattr(heuristic_coach, "get_api_key", lambda: None)
    res = heuristic_coach.explain_steps(_question())
    assert res == {"ok": False, "steps": []}


def test_explain_steps_parses_model_output(monkeypatch):
    monkeypatch.setattr(heuristic_coach, "get_api_key", lambda: "sk-test")
    monkeypatch.setattr(
        heuristic_coach,
        "_chat_json",
        lambda messages, key, timeout=30: {
            "steps": [
                {"say": "Units only work for (B).", "focus": "B"},
                {"say": "So it's (B).", "focus": "answer"},
            ]
        },
    )
    res = heuristic_coach.explain_steps(_question())
    assert res["ok"] is True
    assert len(res["steps"]) == 2
    assert res["steps"][0] == {"say": "Units only work for (B).", "focus": "B"}


def test_explain_steps_empty_output_falls_back(monkeypatch):
    # A well-formed call that yields no usable steps must report unavailable, so
    # the quiz narrates the precomputed key instead of an empty script.
    monkeypatch.setattr(heuristic_coach, "get_api_key", lambda: "sk-test")
    monkeypatch.setattr(
        heuristic_coach, "_chat_json", lambda messages, key, timeout=30: {"steps": []}
    )
    assert heuristic_coach.explain_steps(_question()) == {"ok": False, "steps": []}


def test_explain_steps_network_error_falls_back(monkeypatch):
    import urllib.error

    def boom(messages, key, timeout=30):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(heuristic_coach, "get_api_key", lambda: "sk-test")
    monkeypatch.setattr(heuristic_coach, "_chat_json", boom)
    assert heuristic_coach.explain_steps(_question()) == {"ok": False, "steps": []}
