#!/usr/bin/env python3
"""
Memory Instrumentation — Reports for memory operations, context construction,
influence assessment, and periodic synthesis.

Fire-and-forget NDJSON logging. Never raises to caller — instrumentation
failure must not affect agent operation.

Thread-safe: single NDJSON file per session with per-write locking.
"""

import hashlib
import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hermes_constants import get_hermes_home

logger = logging.getLogger(__name__)

# ── File locking for concurrent writes (foreground + background fork) ──
# Use fcntl on Unix; fall back to threading.Lock on Windows.
_lock_registry: Dict[str, threading.Lock] = {}
_lock_registry_lock = threading.Lock()


# ── Per-session aggregate counters for periodic_synthesis ────────────────
# Mutated under _counters_lock; safe to read for synthesis emission.
_session_counters: Dict[str, Dict[str, int]] = {}
_counters_lock = threading.Lock()


def _counters_for(session_id: str) -> Dict[str, int]:
    with _counters_lock:
        if session_id not in _session_counters:
            _session_counters[session_id] = {
                "fg_writes": 0,
                "bg_writes": 0,
                "writes_blocked": 0,
                "snapshot_reloads": 0,
                "nudge_events": 0,
                "background_review_completions": 0,
            }
        return _session_counters[session_id]


def get_session_counters(session_id: str) -> Dict[str, int]:
    """Public read-only snapshot of session counters for synthesis reports."""
    return dict(_counters_for(session_id))


def reset_session_counters(session_id: str) -> None:
    with _counters_lock:
        _session_counters.pop(session_id, None)

try:
    import fcntl

    def _acquire_file_lock(fd):
        fcntl.flock(fd, fcntl.LOCK_EX)

    def _release_file_lock(fd):
        fcntl.flock(fd, fcntl.LOCK_UN)

except ImportError:
    def _acquire_file_lock(fd):
        pass

    def _release_file_lock(fd):
        pass


# ── Entry ID computation ─────────────────────────────────────────────────

def compute_entry_id(content: str) -> str:
    """Return a content-hash entry ID: sha256:<first 16 hex chars>.

    Deterministic — same content always produces same ID. Stable across
    sessions. Self-verifying by external analyst.
    """
    if not content:
        return "sha256:empty"
    return "sha256:" + hashlib.sha256(content.strip().encode()).hexdigest()[:16]


# ── Output path ──────────────────────────────────────────────────────────

def _instrumentation_dir() -> Path:
    return get_hermes_home() / "instrumentation" / "memory"


def _session_path(session_id: str) -> Path:
    d = _instrumentation_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{session_id}.ndjson"


# ── Emit ─────────────────────────────────────────────────────────────────

def emit_report(report: dict, session_id: str) -> bool:
    """Append a report as one NDJSON line. Thread-safe via file locking.

    Returns True on success, False on failure. Never raises.
    """
    if not session_id:
        return False

    try:
        # Ensure report_id (8-byte random → 12 hex chars to keep collisions
        # negligible under sub-second bursts from foreground + fork)
        if "report_id" not in report:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            suffix = hashlib.sha256(os.urandom(8)).hexdigest()[:12]
            report["report_id"] = f"{report.get('report_type', 'unknown')}_{ts}_{suffix}"

        # Ensure timestamp
        if "timestamp" not in report:
            report["timestamp"] = datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

        line = json.dumps(report, ensure_ascii=False, default=str) + "\n"
        path = _session_path(session_id)

        # Acquire a lock for this specific file path
        with _lock_registry_lock:
            if str(path) not in _lock_registry:
                _lock_registry[str(path)] = threading.Lock()
            lock = _lock_registry[str(path)]

        with lock:
            # Open with exclusive lock
            with open(path, "a", encoding="utf-8") as f:
                _acquire_file_lock(f)
                try:
                    f.write(line)
                    f.flush()
                finally:
                    _release_file_lock(f)

        # Bump aggregate counters used by periodic_synthesis. Done after the
        # write so a failed emit doesn't leave a phantom counter increment.
        try:
            rt = report.get("report_type")
            counters = _counters_for(session_id)
            with _counters_lock:
                if rt == "memory_write":
                    src = (report.get("category_A_observed") or {}).get("source")
                    if src == "background_review":
                        counters["bg_writes"] += 1
                    else:
                        counters["fg_writes"] += 1
                elif rt == "memory_write_blocked":
                    counters["writes_blocked"] += 1
                elif rt == "memory_snapshot_reload":
                    counters["snapshot_reloads"] += 1
                elif rt == "memory_nudge_trigger":
                    counters["nudge_events"] += 1
                elif rt == "background_review_complete":
                    counters["background_review_completions"] += 1
        except Exception:
            pass

        return True

    except Exception as e:
        logger.debug("Instrumentation emit failed (non-fatal): %s", e)
        return False


# ── Report builders ──────────────────────────────────────────────────────

def build_context_construction_report(
    *,
    session_id: str,
    turn_number: int,
    iteration_number: int,
    frozen_snapshot_included: bool,
    frozen_snapshot_size_chars: int,
    frozen_snapshot_size_pct: float,
    memory_entries: List[Dict[str, str]],
    memory_entries_count: int,
    user_entries_count: int,
    external_prefetch_active: bool,
    external_prefetch_content_length: int,
    compression_active_this_turn: bool,
    compression_count_this_session: int,
) -> dict:
    return {
        "report_type": "context_construction",
        "session_id": session_id,
        "turn_number": turn_number,
        "iteration_number": iteration_number,
        "category_A_observed": {
            "frozen_snapshot_included": frozen_snapshot_included,
            "frozen_snapshot_size_chars": frozen_snapshot_size_chars,
            "frozen_snapshot_size_pct": round(frozen_snapshot_size_pct, 1),
            "memory_entries": memory_entries,
            "memory_entries_count": memory_entries_count,
            "user_entries_count": user_entries_count,
            "external_prefetch_active": external_prefetch_active,
            "external_prefetch_content_length": external_prefetch_content_length,
            "compression_active_this_turn": compression_active_this_turn,
            "compression_count_this_session": compression_count_this_session,
            "estimated_total_context_tokens": None,
            "estimated_memory_contribution_tokens": None,
        },
        "category_C_known_unknowns": {
            "unobserved": [
                "actual_token_count_of_memory_block",
                "actual_token_count_of_total_context",
                "background_review_may_have_written_during_this_turn",
                "external_provider_operations_if_active",
            ]
        },
    }


def build_memory_write_report(
    *,
    action: str,
    target: str,
    content: str,
    entry_id: str,
    content_length_chars: int,
    previous_entry_id: Optional[str],
    previous_content: Optional[str],
    result: str,
    entries_after_count: int,
    usage_after: str,
    source: str,
    session_id: str,
    write_category: str,
    predicted_utility_horizon: str,
    storage_confidence: str,
    reasoning: str,
    turn_number: Optional[int] = None,
    reasoning_method: str = "reasoning_trace",
) -> dict:
    return {
        "report_type": "memory_write",
        "session_id": session_id,
        "turn_number": turn_number,
        "category_A_observed": {
            "action": action,
            "target": target,
            "entry_id": entry_id,
            "content_full": content,
            "content_length_chars": content_length_chars,
            "previous_entry_id": previous_entry_id,
            "previous_content": previous_content,
            "result": result,
            "entries_after_count": entries_after_count,
            "usage_after": usage_after,
            "source": source,
            "write_origin_session_id": session_id,
        },
        "category_B_self_assessed": {
            "write_category": write_category,
            "predicted_utility_horizon": predicted_utility_horizon,
            "storage_confidence": storage_confidence,
            "method": reasoning_method,
            "reasoning": reasoning,
            "predicted_relevance_scope": None,
            "expected_staleness": None,
        },
        "category_C_known_unknowns": {
            "unobserved": [
                "whether_future_agent_will_use_this_entry",
                "whether_background_review_would_have_stored_this_independently",
            ]
        },
    }


def build_memory_write_blocked_report(
    *,
    action: str,
    target: str,
    block_reason: str,
    block_pattern_matched: Optional[str],
    content_attempted_first_80_chars: str,
    source: str,
    session_id: str,
    legitimacy: str,
    confidence: str,
    reasoning: str,
    turn_number: Optional[int] = None,
    reasoning_method: str = "reasoning_trace",
) -> dict:
    return {
        "report_type": "memory_write_blocked",
        "session_id": session_id,
        "turn_number": turn_number,
        "category_A_observed": {
            "action": action,
            "target": target,
            "block_reason": block_reason,
            "block_pattern_matched": block_pattern_matched,
            "content_attempted_first_80_chars": content_attempted_first_80_chars,
            "source": source,
        },
        "category_B_self_assessed": {
            "legitimacy": legitimacy,
            "confidence": confidence,
            "method": reasoning_method,
            "reasoning": reasoning,
        },
        "category_C_known_unknowns": {
            "unobserved": [
                "whether_scanner_has_false_positive_rate",
                "cumulative_false_positive_count_across_all_sessions",
                "whether_similar_legitimate_content_was_previously_blocked",
            ]
        },
    }


def build_snapshot_reload_report(
    *,
    trigger: str,
    entries_before: List[str],
    entries_after: List[str],
    entries_added: List[str],
    entries_removed: List[str],
    entries_modified: List[str],
    usage_pct_before: str,
    usage_pct_after: str,
    compression_count: int,
    session_id: str,
    surprise_assessment: str,
    confidence: str,
    reasoning: str,
    turn_number: Optional[int] = None,
) -> dict:
    return {
        "report_type": "memory_snapshot_reload",
        "session_id": session_id,
        "turn_number": turn_number,
        "category_A_observed": {
            "trigger": trigger,
            "entries_before": entries_before,
            "entries_after": entries_after,
            "entries_added_since_session_start": entries_added,
            "entries_removed_since_session_start": entries_removed,
            "entries_modified_since_session_start": entries_modified,
            "entries_before_count": len(entries_before),
            "entries_after_count": len(entries_after),
            "usage_pct_before": usage_pct_before,
            "usage_pct_after": usage_pct_after,
            "compression_count": compression_count,
        },
        "category_B_self_assessed": {
            "surprise_entries": {
                "unexpected_new_entries": [],
                "unexpected_removals": [],
                "assessment": surprise_assessment,
                "confidence": confidence,
                "method": "reasoning_trace",
                "reasoning": reasoning,
            }
        },
        "category_C_known_unknowns": {
            "unobserved": [
                "whether_background_review_wrote_entries_during_this_session",
                "provenance_of_entries_that_existed_before_session_start",
            ]
        },
    }


def build_influence_self_assessment_report(
    *,
    session_id: str,
    turn_number: int,
    response_length_chars: int,
    memory_entries_at_response_time: List[str],
    memory_entries_count: int,
    memory_block_visible: bool,
    entries_explicitly_cited: List[dict],
    entries_likely_influenced: List[dict],
    entries_present_but_unused: List[dict],
    entries_missing: List[str],
    overall_utility: str,
    overall_confidence: str,
    assessment_method: str,
    reasoning: str,
) -> dict:
    return {
        "report_type": "memory_influence_self_assessment",
        "session_id": session_id,
        "turn_number": turn_number,
        "category_A_observed": {
            "response_length_chars": response_length_chars,
            "memory_entries_at_response_time": memory_entries_at_response_time,
            "memory_entries_count": memory_entries_count,
            "memory_block_visible_in_context": memory_block_visible,
        },
        "category_B_self_assessed": {
            "entries_explicitly_cited": entries_explicitly_cited,
            "entries_likely_influenced": entries_likely_influenced,
            "entries_present_but_unused": entries_present_but_unused,
            "entries_would_have_helped_but_were_missing": entries_missing,
            "overall_memory_utility_this_turn": overall_utility,
            "overall_confidence": overall_confidence,
            "assessment_method": assessment_method,
            "reasoning": reasoning,
        },
        "category_C_known_unknowns": {
            "unobserved": [
                "subliminal_influence_of_memory_on_response_style_or_framing",
                "whether_response_would_meaningfully_differ_without_memory_block",
                "actual_attention_distribution_across_context_window",
            ]
        },
    }


def build_nudge_trigger_report(
    *,
    session_id: str,
    turn_number: int,
    turns_since_last_memory: int,
    nudge_interval: int,
    background_review_spawned: bool,
    co_triggered_with_skills: bool,
    should_probably_store: bool,
    confidence: str,
    reasoning: str,
    reasoning_method: str = "output_inference",
) -> dict:
    return {
        "report_type": "memory_nudge_trigger",
        "session_id": session_id,
        "turn_number": turn_number,
        "category_A_observed": {
            "turns_since_last_memory_operation": turns_since_last_memory,
            "nudge_interval": nudge_interval,
            "background_review_spawned": background_review_spawned,
            "co_triggered_with_skills_review": co_triggered_with_skills,
        },
        "category_B_self_assessed": {
            "should_probably_store_memory": should_probably_store,
            "confidence": confidence,
            "method": reasoning_method,
            "reasoning": reasoning,
        },
        "category_C_known_unknowns": {
            "unobserved": [
                "what_background_review_agent_will_decide_to_store",
                "whether_background_review_will_complete_successfully",
            ]
        },
    }


def build_background_review_complete_report(
    *,
    session_id: str,
    turn_number: int,
    review_agent_session_id: str,
    review_messages_count: int,
    review_completed: bool,
    review_success: bool,
    review_iterations_used: int,
    writes_performed: List[dict],
    writes_blocked: List[dict],
    review_quality_assessment: str,
    confidence: str,
    reasoning: str,
    foreground_vs_background: dict,
) -> dict:
    return {
        "report_type": "background_review_complete",
        "session_id": session_id,
        "turn_number": turn_number,
        "category_A_observed": {
            "review_agent_session_id": review_agent_session_id,
            "review_messages_count": review_messages_count,
            "review_completed": review_completed,
            "review_success": review_success,
            "review_iterations_used": review_iterations_used,
            "writes_performed": writes_performed,
            "writes_blocked": writes_blocked,
        },
        "category_B_self_assessed": {
            "review_quality_assessment": review_quality_assessment,
            "confidence": confidence,
            "method": "output_inference",
            "reasoning": reasoning,
            "foreground_vs_background": foreground_vs_background,
        },
        "category_C_known_unknowns": {
            "unobserved": [
                "whether_background_review_reasoning_was_correct",
                "whether_background_review_missed_important_facts",
                "whether_background_review_stored_stale_or_incorrect_information",
            ]
        },
    }


def build_periodic_synthesis_report(
    *,
    session_id: str,
    turns_covered: str,
    total_memory_writes_foreground: int,
    total_memory_writes_background: int,
    total_memory_writes_blocked: int,
    total_turns: int,
    compression_events: int,
    snapshot_reloads: int,
    nudge_events: int,
    background_review_completions: int,
    current_memory_entries: List[str],
    current_usage_pct: str,
    current_usage_chars: str,
    patterns_observed: List[str],
    questions_raised: List[str],
    gaps_identified: List[str],
    surprises: List[str],
    confidence: str,
    reasoning: str,
    reasoning_method: str = "output_inference",
) -> dict:
    return {
        "report_type": "periodic_synthesis",
        "session_id": session_id,
        "turns_covered": turns_covered,
        "category_A_observed": {
            "total_memory_writes_foreground": total_memory_writes_foreground,
            "total_memory_writes_background": total_memory_writes_background,
            "total_memory_writes_blocked": total_memory_writes_blocked,
            "total_turns": total_turns,
            "compression_events": compression_events,
            "snapshot_reloads": snapshot_reloads,
            "nudge_events": nudge_events,
            "background_review_completions": background_review_completions,
            "current_memory_entries": current_memory_entries,
            "current_usage": current_usage_chars,
            "current_usage_pct": current_usage_pct,
        },
        "category_B_self_assessed": {
            "patterns_observed": patterns_observed,
            "questions_raised": questions_raised,
            "gaps_identified": gaps_identified,
            "surprises": surprises,
            "confidence": confidence,
            "method": reasoning_method,
            "reasoning": reasoning,
        },
        "category_C_known_unknowns": {
            "persistent_gaps": [
                "actual_token_cost_of_memory_in_context",
                "provenance_of_pre_existing_memory_entries",
                "whether_background_review_writes_are_durable_across_sessions",
                "external_observer_would_benefit_from_knowing_attention_distribution",
                "whether_memory_entries_ever_influence_future_responses",
                "cumulative_accuracy_of_write_category_predictions",
            ]
        },
    }
