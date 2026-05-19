"""Tests for memory-influence self-assessment derivation (Story 001).

Covers ``AIAgent._emit_influence_assessment`` derivation of the
``overall_memory_utility_this_turn`` field from per-entry cited counts.

The emit function is exercised via ``AIAgent._emit_influence_assessment(stub, response)``
with a SimpleNamespace stub instead of a full agent. This keeps the test focused on
the derivation logic — the rest of the emit machinery (entry-id hashing, NDJSON
append, file locking) is covered transitively when the report file is parsed back.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

from hermes_constants import get_hermes_home
from run_agent import AIAgent


def _make_agent_stub(memory_entries: list[str], session_id: str = "test_session"):
    """Minimal stub mirroring the AIAgent attributes ``_emit_influence_assessment`` reads.

    Binds the three private path helpers so the dispatcher can call
    ``self._emit_influence_assessment_heuristic`` etc. without a full AIAgent.
    """

    class _FakeMemoryStore:
        def __init__(self, entries: list[str]):
            self.memory_entries = entries

        def format_for_system_prompt(self, target: str) -> Optional[str]:
            if target == "memory" and self.memory_entries:
                return "\n".join(self.memory_entries)
            return None

    agent = SimpleNamespace(
        _memory_store=_FakeMemoryStore(memory_entries),
        session_id=session_id,
        _user_turn_count=1,
        _instr_background_influence_assessment=False,
        _instr_inline_llm_assessment=False,
        _instr_precedence_logged=False,
        _instr_assessment_timeout_seconds=5.0,
    )
    agent._emit_influence_assessment_heuristic = (
        AIAgent._emit_influence_assessment_heuristic.__get__(agent)
    )
    agent._emit_influence_assessment_inline = (
        AIAgent._emit_influence_assessment_inline.__get__(agent)
    )
    agent._emit_influence_assessment_background = (
        AIAgent._emit_influence_assessment_background.__get__(agent)
    )
    return agent


def _read_influence_reports(session_id: str) -> list[dict]:
    path: Path = (
        get_hermes_home() / "instrumentation" / "memory" / f"{session_id}.ndjson"
    )
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _last_influence(session_id: str) -> dict:
    reports = [
        r
        for r in _read_influence_reports(session_id)
        if r.get("report_type") == "memory_influence_self_assessment"
    ]
    assert reports, f"No influence reports found for session {session_id}"
    return reports[-1]


def test_overall_utility_some_heuristic_evidence_when_entry_cited():
    """AC1: ≥1 cited entry → 'some_heuristic_evidence'."""
    entry = "use pytest-xdist convention for parallel test execution"
    agent = _make_agent_stub([entry], session_id="ac1_session")
    response = "I ran with use pytest-xdist convention for parallel test execution mode"

    AIAgent._emit_influence_assessment(agent, response)

    report = _last_influence("ac1_session")
    cb = report["category_B_self_assessed"]
    assert cb["overall_memory_utility_this_turn"] == "some_heuristic_evidence"
    assert cb["assessment_method"] == "pattern_matching"
    assert cb["overall_confidence"] == "low"
    assert len(cb["entries_explicitly_cited"]) == 1
    assert len(cb["entries_present_but_unused"]) == 0


def test_overall_utility_no_heuristic_evidence_when_entries_unmatched():
    """AC2: entries present but none cited → 'no_heuristic_evidence'."""
    agent = _make_agent_stub(
        ["completely unrelated entry about Railway deployment URLs"],
        session_id="ac2_session",
    )
    response = (
        "Let me explain memory instrumentation architecture and dead-weight analysis"
    )

    AIAgent._emit_influence_assessment(agent, response)

    report = _last_influence("ac2_session")
    cb = report["category_B_self_assessed"]
    assert cb["overall_memory_utility_this_turn"] == "no_heuristic_evidence"
    assert cb["assessment_method"] == "pattern_matching"
    assert cb["overall_confidence"] == "low"
    assert len(cb["entries_explicitly_cited"]) == 0
    assert len(cb["entries_present_but_unused"]) == 1


def test_overall_utility_n_a_when_memory_empty():
    """AC3: empty memory → 'n_a_no_entries' and empty per-entry lists."""
    agent = _make_agent_stub([], session_id="ac3_session")

    AIAgent._emit_influence_assessment(agent, "any response text")

    report = _last_influence("ac3_session")
    cb = report["category_B_self_assessed"]
    assert cb["overall_memory_utility_this_turn"] == "n_a_no_entries"
    assert cb["assessment_method"] == "pattern_matching"
    assert cb["overall_confidence"] == "low"
    assert cb["entries_explicitly_cited"] == []
    assert cb["entries_present_but_unused"] == []
    assert report["category_A_observed"]["memory_entries_count"] == 0


def test_reasoning_contains_cited_counts():
    """AC4 supporting: reasoning string surfaces the X-of-N cited count."""
    entries = [
        "alpha entry about deploying to railway and waiting for completion",
        "beta entry about completely different topic with enough characters",
    ]
    agent = _make_agent_stub(entries, session_id="ac4_session")
    response = (
        "alpha entry about deploying to railway and waiting for completion happens here"
    )

    AIAgent._emit_influence_assessment(agent, response)

    cb = _last_influence("ac4_session")["category_B_self_assessed"]
    assert "1 of 2" in cb["reasoning"]
    assert "pattern_matching" in cb["reasoning"]


def test_epistemic_tagging_unchanged_across_outcomes():
    """AC4: assessment_method and overall_confidence stay constant regardless of outcome."""
    cases = [
        ([], "no memory case", "ac5a_session"),
        (
            ["matched entry text that is long enough to cite from"],
            "matched entry text that is long enough to cite from is here",
            "ac5b_session",
        ),
        (
            ["unmatched entry text long enough to be considered for citation"],
            "unrelated response",
            "ac5c_session",
        ),
    ]
    for entries, response, session in cases:
        agent = _make_agent_stub(entries, session_id=session)
        AIAgent._emit_influence_assessment(agent, response)
        cb = _last_influence(session)["category_B_self_assessed"]
        assert cb["assessment_method"] == "pattern_matching", session
        assert cb["overall_confidence"] == "low", session


def test_report_schema_shape_unchanged():
    """AC5: existing schema keys remain present (no breaking change for analysts)."""
    agent = _make_agent_stub(
        ["a memory entry long enough to be considered cited"], session_id="ac6_session"
    )
    AIAgent._emit_influence_assessment(
        agent, "a memory entry long enough to be considered cited yes"
    )

    report = _last_influence("ac6_session")
    assert report["report_type"] == "memory_influence_self_assessment"
    assert "category_A_observed" in report
    assert "category_B_self_assessed" in report
    assert "category_C_known_unknowns" in report

    cb = report["category_B_self_assessed"]
    expected_keys = {
        "entries_explicitly_cited",
        "entries_likely_influenced",
        "entries_present_but_unused",
        "entries_would_have_helped_but_were_missing",
        "overall_memory_utility_this_turn",
        "overall_confidence",
        "assessment_method",
        "reasoning",
    }
    assert expected_keys.issubset(cb.keys())
