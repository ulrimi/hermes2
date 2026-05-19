"""Tests for memory influence assessment helpers and AIAgent dispatch paths.

Covers:

- Pure helpers in ``agent.influence_assessment``: prompt builder, response parser.
- ``AIAgent._emit_influence_assessment_inline`` (Story 002): inline aux LLM path.
- ``AIAgent._emit_influence_assessment_background`` (Story 003): daemon-thread path.
- ``AIAgent._emit_influence_assessment`` dispatcher precedence (AC7 of Story 003).

The aux LLM client is mocked at ``agent.auxiliary_client.get_text_auxiliary_client``
so no real API calls are made.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from agent import influence_assessment as ia
from agent.memory_instrumentation import compute_entry_id
from hermes_constants import get_hermes_home
from run_agent import AIAgent


# ── Shared helpers ──────────────────────────────────────────────────────────


def _make_agent_stub(
    memory_entries: list[str],
    session_id: str,
    *,
    inline: bool = False,
    background: bool = False,
    timeout: float = 5.0,
):
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
        _instr_inline_llm_assessment=inline,
        _instr_background_influence_assessment=background,
        _instr_precedence_logged=False,
        _instr_assessment_timeout_seconds=timeout,
    )
    for name in (
        "_emit_influence_assessment_heuristic",
        "_emit_influence_assessment_inline",
        "_emit_influence_assessment_background",
    ):
        setattr(agent, name, getattr(AIAgent, name).__get__(agent))
    return agent


def _read_reports(session_id: str) -> list[dict]:
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
        for r in _read_reports(session_id)
        if r.get("report_type") == "memory_influence_self_assessment"
    ]
    assert reports, f"No influence reports for {session_id}"
    return reports[-1]


def _make_aux_client_mock(payload_dict: dict | str):
    """Build a MagicMock that mimics ``client.chat.completions.create(...)``."""
    if isinstance(payload_dict, dict):
        payload = json.dumps(payload_dict)
    else:
        payload = payload_dict
    message = MagicMock(content=payload)
    choice = MagicMock(message=message)
    response = MagicMock(choices=[choice])
    client = MagicMock()
    client.chat.completions.create.return_value = response
    return client


# ── Pure-helper tests (shared between Stories 002 and 003) ──────────────────


def test_prompt_builder_deterministic_for_same_inputs():
    entries = ["alpha entry", "beta entry"]
    response = "an example response"
    sys1, user1 = ia.build_influence_assessment_prompt(entries, response)
    sys2, user2 = ia.build_influence_assessment_prompt(entries, response)
    assert sys1 == sys2
    assert user1 == user2


def test_prompt_builder_truncates_oversized_entries():
    long_entry = "x" * (ia.MAX_ENTRY_CHARS + 200)
    _, user = ia.build_influence_assessment_prompt([long_entry], "resp")
    assert len(user) < len(long_entry) + 4000
    assert "..." in user


def test_prompt_builder_truncates_oversized_response():
    long_resp = "y" * (ia.MAX_RESPONSE_CHARS + 500)
    _, user = ia.build_influence_assessment_prompt(["entry"], long_resp)
    assert "y" * ia.MAX_RESPONSE_CHARS not in user or "..." in user


def test_prompt_builder_handles_empty_entries():
    _, user = ia.build_influence_assessment_prompt([], "resp")
    assert "(none)" in user


def test_parser_well_formed_json():
    entries = ["use pytest-xdist", "user prefers dark mode"]
    entry_ids = [compute_entry_id(e) for e in entries]
    raw = json.dumps({
        "entries": [
            {"index": 1, "verdict": "cited", "reasoning": "phrase appears"},
            {"index": 2, "verdict": "unused", "reasoning": "no preference mentioned"},
        ],
        "overall": "medium",
        "overall_reasoning": "one entry shaped the response",
    })
    parsed = ia.parse_influence_assessment_response(raw, entries, entry_ids)
    assert parsed is not None
    assert len(parsed["entries_explicitly_cited"]) == 1
    assert len(parsed["entries_present_but_unused"]) == 1
    assert parsed["overall_utility"] == "medium"


def test_parser_strips_code_fences():
    entries = ["entry-a"]
    entry_ids = [compute_entry_id(e) for e in entries]
    raw = '```json\n{"entries":[{"index":1,"verdict":"cited","reasoning":"r"}],"overall":"high","overall_reasoning":"r"}\n```'
    parsed = ia.parse_influence_assessment_response(raw, entries, entry_ids)
    assert parsed is not None
    assert parsed["overall_utility"] == "high"


def test_parser_extracts_json_from_surrounding_prose():
    entries = ["entry-a"]
    entry_ids = [compute_entry_id(e) for e in entries]
    raw = (
        "Sure! Here is the assessment:\n"
        '{"entries":[{"index":1,"verdict":"likely_influenced","reasoning":"r"}],'
        '"overall":"low","overall_reasoning":"slight"}\n'
        "Hope that helps."
    )
    parsed = ia.parse_influence_assessment_response(raw, entries, entry_ids)
    assert parsed is not None
    assert len(parsed["entries_likely_influenced"]) == 1


def test_parser_returns_none_on_unrecoverable_garbage():
    entries = ["entry-a"]
    entry_ids = [compute_entry_id(e) for e in entries]
    assert (
        ia.parse_influence_assessment_response("not json at all", entries, entry_ids)
        is None
    )


def test_parser_accounts_for_omitted_entries():
    entries = ["entry-a", "entry-b", "entry-c"]
    entry_ids = [compute_entry_id(e) for e in entries]
    raw = json.dumps({
        "entries": [{"index": 1, "verdict": "cited", "reasoning": "r"}],
        "overall": "low",
        "overall_reasoning": "partial",
    })
    parsed = ia.parse_influence_assessment_response(raw, entries, entry_ids)
    assert parsed is not None
    omitted_count = sum(
        1
        for e in parsed["entries_present_but_unused"]
        if "omitted" in e["reasoning"].lower()
    )
    assert omitted_count == 2


def test_parser_rejects_out_of_range_indices():
    entries = ["entry-a"]
    entry_ids = [compute_entry_id(e) for e in entries]
    raw = json.dumps({
        "entries": [
            {"index": 1, "verdict": "cited", "reasoning": "r"},
            {"index": 99, "verdict": "cited", "reasoning": "bogus"},
        ],
        "overall": "high",
        "overall_reasoning": "r",
    })
    parsed = ia.parse_influence_assessment_response(raw, entries, entry_ids)
    assert len(parsed["entries_explicitly_cited"]) == 1


def test_parser_unknown_verdict_treated_as_unused():
    entries = ["entry-a"]
    entry_ids = [compute_entry_id(e) for e in entries]
    raw = json.dumps({
        "entries": [{"index": 1, "verdict": "mystery", "reasoning": "r"}],
        "overall": "medium",
        "overall_reasoning": "r",
    })
    parsed = ia.parse_influence_assessment_response(raw, entries, entry_ids)
    assert len(parsed["entries_present_but_unused"]) == 1


def test_parser_unknown_overall_defaults_to_low():
    entries = []
    entry_ids = []
    raw = json.dumps({"entries": [], "overall": "stellar", "overall_reasoning": "r"})
    parsed = ia.parse_influence_assessment_response(raw, entries, entry_ids)
    assert parsed["overall_utility"] == "low"


# ── Story 002: inline path ──────────────────────────────────────────────────


def test_inline_empty_memory_short_circuits_no_llm_call():
    """AC6: empty memory does not invoke the aux client."""
    agent = _make_agent_stub([], session_id="s2_empty", inline=True)
    with patch("agent.auxiliary_client.get_text_auxiliary_client") as gtac:
        AIAgent._emit_influence_assessment(agent, "any response")
        gtac.assert_not_called()
    cb = _last_influence("s2_empty")["category_B_self_assessed"]
    assert cb["assessment_method"] == "output_inference"
    assert cb["overall_memory_utility_this_turn"] == "none"


def test_inline_populates_output_inference_on_success():
    """AC1+AC2: aux returns valid JSON → output_inference, medium confidence."""
    agent = _make_agent_stub(
        ["use pytest-xdist for parallel tests"],
        session_id="s2_success",
        inline=True,
    )
    client = _make_aux_client_mock({
        "entries": [{"index": 1, "verdict": "cited", "reasoning": "phrase appears"}],
        "overall": "high",
        "overall_reasoning": "entry shaped the response",
    })
    with patch(
        "agent.auxiliary_client.get_text_auxiliary_client",
        return_value=(client, "claude-haiku-4-5"),
    ):
        with patch(
            "agent.auxiliary_client.get_auxiliary_extra_body", return_value=None
        ):
            AIAgent._emit_influence_assessment(
                agent, "use pytest-xdist for parallel tests now"
            )

    cb = _last_influence("s2_success")["category_B_self_assessed"]
    assert cb["assessment_method"] == "output_inference"
    assert cb["overall_confidence"] == "medium"
    assert cb["overall_memory_utility_this_turn"] == "high"
    assert len(cb["entries_explicitly_cited"]) == 1


def test_inline_api_error_emits_error_fallback():
    """AC3: aux call raising emits error_fallback report."""
    agent = _make_agent_stub(["entry-a"], session_id="s2_apierr", inline=True)
    client = MagicMock()
    client.chat.completions.create.side_effect = RuntimeError("upstream 503")
    with patch(
        "agent.auxiliary_client.get_text_auxiliary_client",
        return_value=(client, "model"),
    ):
        with patch(
            "agent.auxiliary_client.get_auxiliary_extra_body", return_value=None
        ):
            AIAgent._emit_influence_assessment(agent, "response")

    cb = _last_influence("s2_apierr")["category_B_self_assessed"]
    assert cb["assessment_method"] == "error_fallback"
    assert cb["overall_memory_utility_this_turn"] == "unassessed"
    assert "RuntimeError" in cb["reasoning"]


def test_inline_no_aux_client_configured_emits_error_fallback():
    """AC3: aux client returning None falls through to error_fallback."""
    agent = _make_agent_stub(["entry-a"], session_id="s2_noclient", inline=True)
    with patch(
        "agent.auxiliary_client.get_text_auxiliary_client",
        return_value=(None, None),
    ):
        AIAgent._emit_influence_assessment(agent, "response")

    cb = _last_influence("s2_noclient")["category_B_self_assessed"]
    assert cb["assessment_method"] == "error_fallback"
    assert "no_auxiliary_client_configured" in cb["reasoning"]


def test_inline_parse_failure_emits_error_fallback():
    """AC3: garbage response → parse failure → error_fallback."""
    agent = _make_agent_stub(["entry-a"], session_id="s2_garbage", inline=True)
    client = _make_aux_client_mock("not json")
    with patch(
        "agent.auxiliary_client.get_text_auxiliary_client",
        return_value=(client, "model"),
    ):
        with patch(
            "agent.auxiliary_client.get_auxiliary_extra_body", return_value=None
        ):
            AIAgent._emit_influence_assessment(agent, "response")

    cb = _last_influence("s2_garbage")["category_B_self_assessed"]
    assert cb["assessment_method"] == "error_fallback"
    assert "parse_failed" in cb["reasoning"]


def test_inline_flag_off_falls_back_to_heuristic():
    """AC4: with flag off, dispatcher routes to heuristic (pattern_matching) path."""
    agent = _make_agent_stub(
        ["entry text long enough to be considered cited from"],
        session_id="s2_flagoff",
        inline=False,
    )
    with patch("agent.auxiliary_client.get_text_auxiliary_client") as gtac:
        AIAgent._emit_influence_assessment(
            agent, "entry text long enough to be considered cited from now"
        )
        gtac.assert_not_called()
    cb = _last_influence("s2_flagoff")["category_B_self_assessed"]
    assert cb["assessment_method"] == "pattern_matching"


# ── Story 003: background path ──────────────────────────────────────────────


def _wait_for_thread_completion(predicate, timeout: float = 3.0):
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def test_background_thread_spawned_foreground_returns_fast():
    """AC1: background flag spawns daemon thread; foreground does not block."""

    started = threading.Event()
    release = threading.Event()

    def slow_client_factory(*_a, **_kw):
        class _SlowClient:
            class chat:
                class completions:
                    @staticmethod
                    def create(**kwargs):
                        started.set()
                        release.wait(timeout=2.0)
                        msg = MagicMock(
                            content=json.dumps({
                                "entries": [
                                    {"index": 1, "verdict": "cited", "reasoning": "r"}
                                ],
                                "overall": "high",
                                "overall_reasoning": "r",
                            })
                        )
                        choice = MagicMock(message=msg)
                        return MagicMock(choices=[choice])

        return _SlowClient(), "model"

    agent = _make_agent_stub(
        ["entry-a long enough to test"],
        session_id="s3_async",
        background=True,
    )
    with patch(
        "agent.auxiliary_client.get_text_auxiliary_client",
        side_effect=slow_client_factory,
    ):
        with patch(
            "agent.auxiliary_client.get_auxiliary_extra_body", return_value=None
        ):
            start = time.time()
            AIAgent._emit_influence_assessment(agent, "response text")
            foreground_elapsed = time.time() - start
            assert foreground_elapsed < 0.3, (
                f"foreground should not block — took {foreground_elapsed:.3f}s"
            )
            assert started.wait(timeout=1.0), "background thread did not start"
            release.set()

    assert _wait_for_thread_completion(
        lambda: any(
            r.get("report_type") == "memory_influence_self_assessment"
            for r in _read_reports("s3_async")
        ),
        timeout=3.0,
    ), "background report did not arrive"

    cb = _last_influence("s3_async")["category_B_self_assessed"]
    assert cb["assessment_method"] == "output_inference"


def test_background_snapshot_semantics():
    """AC3: assessment uses entries snapshotted at spawn, not live mutations."""
    initial_entries = ["original entry text long enough for testing"]
    agent = _make_agent_stub(
        initial_entries,
        session_id="s3_snapshot",
        background=True,
    )
    expected_entry_id = compute_entry_id(initial_entries[0])

    client = _make_aux_client_mock({
        "entries": [{"index": 1, "verdict": "cited", "reasoning": "r"}],
        "overall": "medium",
        "overall_reasoning": "r",
    })
    with patch(
        "agent.auxiliary_client.get_text_auxiliary_client",
        return_value=(client, "model"),
    ):
        with patch(
            "agent.auxiliary_client.get_auxiliary_extra_body", return_value=None
        ):
            AIAgent._emit_influence_assessment(agent, "response")
            agent._memory_store.memory_entries.clear()
            agent._memory_store.memory_entries.append("DIFFERENT entry post-spawn")

    assert _wait_for_thread_completion(
        lambda: any(
            r.get("report_type") == "memory_influence_self_assessment"
            for r in _read_reports("s3_snapshot")
        ),
        timeout=3.0,
    )

    report = _last_influence("s3_snapshot")
    assert report["category_A_observed"]["memory_entries_at_response_time"] == [
        expected_entry_id
    ]


def test_background_api_error_emits_error_fallback():
    """AC4: capacity / API failure → error_fallback report from the thread."""
    agent = _make_agent_stub(
        ["entry-a long enough"], session_id="s3_err", background=True
    )
    client = MagicMock()
    client.chat.completions.create.side_effect = RuntimeError("capacity exhausted")
    with patch(
        "agent.auxiliary_client.get_text_auxiliary_client",
        return_value=(client, "model"),
    ):
        with patch(
            "agent.auxiliary_client.get_auxiliary_extra_body", return_value=None
        ):
            AIAgent._emit_influence_assessment(agent, "response")

    assert _wait_for_thread_completion(
        lambda: any(
            r.get("report_type") == "memory_influence_self_assessment"
            for r in _read_reports("s3_err")
        ),
        timeout=3.0,
    )
    cb = _last_influence("s3_err")["category_B_self_assessed"]
    assert cb["assessment_method"] == "error_fallback"
    assert "RuntimeError" in cb["reasoning"]


def test_background_precedence_over_inline(caplog):
    """AC7: when both flags on, background path wins and inline is skipped."""
    import logging

    caplog.set_level(logging.INFO)
    agent = _make_agent_stub(
        ["entry-a"],
        session_id="s3_prec",
        inline=True,
        background=True,
    )
    client = _make_aux_client_mock({
        "entries": [{"index": 1, "verdict": "cited", "reasoning": "r"}],
        "overall": "low",
        "overall_reasoning": "r",
    })
    with patch(
        "agent.auxiliary_client.get_text_auxiliary_client",
        return_value=(client, "model"),
    ):
        with patch(
            "agent.auxiliary_client.get_auxiliary_extra_body", return_value=None
        ):
            AIAgent._emit_influence_assessment(agent, "response")

    assert _wait_for_thread_completion(
        lambda: any(
            r.get("report_type") == "memory_influence_self_assessment"
            for r in _read_reports("s3_prec")
        ),
        timeout=3.0,
    )

    # Exactly one report this turn — not two.
    reports = [
        r
        for r in _read_reports("s3_prec")
        if r.get("report_type") == "memory_influence_self_assessment"
    ]
    assert len(reports) == 1
    assert (
        reports[0]["category_B_self_assessed"]["assessment_method"]
        == "output_inference"
    )

    # Precedence INFO log fired (caplog captures it).
    prec_logs = [
        r
        for r in caplog.records
        if "background path takes precedence" in r.getMessage()
    ]
    assert len(prec_logs) == 1


def test_concurrent_emits_produce_valid_ndjson(tmp_path, monkeypatch):
    """AC5: 50 concurrent emits across simulated threads keep NDJSON parseable."""
    from agent import memory_instrumentation as mi

    session = "s3_stress"
    n_threads = 50

    client = _make_aux_client_mock({
        "entries": [{"index": 1, "verdict": "cited", "reasoning": "r"}],
        "overall": "low",
        "overall_reasoning": "r",
    })
    threads = []
    with patch(
        "agent.auxiliary_client.get_text_auxiliary_client",
        return_value=(client, "model"),
    ):
        with patch(
            "agent.auxiliary_client.get_auxiliary_extra_body", return_value=None
        ):
            for i in range(n_threads):
                agent = _make_agent_stub(
                    [f"entry text number {i} long enough for testing"],
                    session_id=session,
                    background=True,
                )
                agent._user_turn_count = i

                def _go(a=agent):
                    AIAgent._emit_influence_assessment(
                        a, f"response {a._user_turn_count}"
                    )

                t = threading.Thread(target=_go)
                t.start()
                threads.append(t)
            for t in threads:
                t.join(timeout=3.0)

    # Wait for daemon threads to finish writing
    assert _wait_for_thread_completion(
        lambda: len([
            r
            for r in _read_reports(session)
            if r.get("report_type") == "memory_influence_self_assessment"
        ])
        == n_threads,
        timeout=10.0,
    ), f"expected {n_threads} reports"

    reports = [
        r
        for r in _read_reports(session)
        if r.get("report_type") == "memory_influence_self_assessment"
    ]
    assert all(
        r["category_B_self_assessed"]["assessment_method"] == "output_inference"
        for r in reports
    )
