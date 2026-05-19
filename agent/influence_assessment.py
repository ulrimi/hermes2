"""Memory influence self-assessment via auxiliary LLM call.

Two entry points, both fire-and-forget:

- :func:`assess_influence_inline` — synchronous call on the foreground thread,
  used by Story 002's inline path. Adds latency to the user turn.
- :func:`spawn_influence_assessment_thread` — daemon thread, used by Story 003's
  background path. Zero foreground latency; report may land after the next turn
  has started (analyst tooling handles this via `turn_number` in the report).

Both paths share :func:`build_influence_assessment_prompt` and
:func:`parse_influence_assessment_response` for prompt construction and JSON
parsing. The shared helpers are pure (no I/O, no LLM dependency) so they can be
unit-tested without mocks.

Failure modes degrade safely: any error in the aux call, parsing, or emit path
results in a `memory_influence_self_assessment` report with
``assessment_method="error_fallback"`` and a reasoning string naming the error
class. The foreground turn is never affected.
"""

from __future__ import annotations

import json
import logging
import re
import threading
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Hard ceilings so a single malformed turn cannot blow up token budget. Both
# can be loosened later if assessment quality is insufficient.
MAX_ENTRY_CHARS = 400
MAX_RESPONSE_CHARS = 4000
DEFAULT_TIMEOUT_SECONDS = 5.0
DEFAULT_MAX_TOKENS = 800


SYSTEM_PROMPT = (
    "You are a memory-utility analyst. The agent just produced a response. "
    "Your job is to judge whether each stored memory entry actually influenced "
    "that response, or whether it was dead weight. "
    "Respond with valid JSON only — no prose, no markdown fences."
)


USER_PROMPT_TEMPLATE = """For each memory entry below, classify its influence on the response:

- "cited": text or facts from the entry appear in the response, exactly or paraphrased.
- "likely_influenced": the response references the topic, framing, or fact without quoting,
  in a way that suggests the entry shaped it.
- "unused": the response shows no sign of using this entry.

Also rate the OVERALL utility of the memory block this turn:
- "high": at least one entry was clearly cited or strongly shaped the response.
- "medium": at least one entry likely influenced the response.
- "low": entries were present but did not meaningfully shape the response.
- "none": no entries existed or none influenced anything.

Memory entries (numbered):
{entries_block}

Response that the agent just produced:
\"\"\"
{response}
\"\"\"

Output strictly this JSON shape (no surrounding text):
{{
  "entries": [
    {{"index": <int>, "verdict": "cited|likely_influenced|unused", "reasoning": "<one short sentence>"}}
  ],
  "overall": "high|medium|low|none",
  "overall_reasoning": "<one short sentence>"
}}
"""


def _truncate(s: str, limit: int) -> str:
    if len(s) <= limit:
        return s
    return s[: limit - 3] + "..."


def build_influence_assessment_prompt(
    entries: List[str], response: str
) -> Tuple[str, str]:
    """Return ``(system_prompt, user_prompt)`` for the aux LLM call.

    Deterministic for given inputs. Entries are truncated to ``MAX_ENTRY_CHARS``
    and the response to ``MAX_RESPONSE_CHARS`` so a single oversized turn cannot
    blow up token usage.
    """
    if not entries:
        entries_block = "(none)"
    else:
        entries_block = "\n".join(
            f"{i + 1}. {_truncate(entry, MAX_ENTRY_CHARS)}"
            for i, entry in enumerate(entries)
        )
    user_prompt = USER_PROMPT_TEMPLATE.format(
        entries_block=entries_block,
        response=_truncate(response, MAX_RESPONSE_CHARS),
    )
    return SYSTEM_PROMPT, user_prompt


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json_object(raw: str) -> Optional[dict]:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        pass
    # Strip code fences if the model wrapped its output despite instructions.
    stripped = raw.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\n?", "", stripped)
        stripped = re.sub(r"\n?```$", "", stripped)
        try:
            return json.loads(stripped)
        except Exception:
            pass
    # Last resort: grab the first {...} block via greedy regex.
    m = _JSON_OBJECT_RE.search(raw)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


_VERDICT_TO_LIST = {
    "cited": "entries_explicitly_cited",
    "likely_influenced": "entries_likely_influenced",
    "unused": "entries_present_but_unused",
}

_OVERALL_VALUES = {"high", "medium", "low", "none"}


def parse_influence_assessment_response(
    raw: str,
    entries: List[str],
    entry_ids: List[str],
) -> Optional[Dict[str, Any]]:
    """Parse the aux LLM response into report-builder kwargs.

    Returns ``None`` on unrecoverable parse failure. Returns a dict with
    ``entries_explicitly_cited``, ``entries_likely_influenced``,
    ``entries_present_but_unused``, and ``overall_utility`` on success.

    Robust to: malformed JSON, missing fields, out-of-range indices, unknown
    verdicts, fewer or more entries returned than expected.
    """
    obj = _extract_json_object(raw)
    if not isinstance(obj, dict):
        return None

    overall_raw = str(obj.get("overall", "")).strip().lower()
    overall = overall_raw if overall_raw in _OVERALL_VALUES else "low"
    overall_reasoning = str(obj.get("overall_reasoning", "")).strip()

    entries_cited: List[Dict[str, Any]] = []
    entries_likely: List[Dict[str, Any]] = []
    entries_unused: List[Dict[str, Any]] = []

    # Track which 1-based indices the model accounted for; everything missing
    # gets recorded as "unused" with a parse-recovery reason so the report
    # remains exhaustive.
    seen_indices: set[int] = set()

    raw_entries = obj.get("entries", [])
    if not isinstance(raw_entries, list):
        raw_entries = []

    for item in raw_entries:
        if not isinstance(item, dict):
            continue
        idx = item.get("index")
        try:
            idx_int = int(idx)
        except (TypeError, ValueError):
            continue
        if idx_int < 1 or idx_int > len(entries):
            continue
        if idx_int in seen_indices:
            continue
        seen_indices.add(idx_int)

        verdict = str(item.get("verdict", "")).strip().lower()
        bucket_key = _VERDICT_TO_LIST.get(verdict)
        if bucket_key is None:
            verdict = "unused"
            bucket_key = "entries_present_but_unused"

        entry_text = entries[idx_int - 1]
        entry_id = entry_ids[idx_int - 1]
        first_80 = entry_text[:80] + ("..." if len(entry_text) > 80 else "")

        item_dict = {
            "entry_id": entry_id,
            "first_80_chars": first_80,
            "influence_assessment": verdict,
            "confidence": "medium",
            "method": "output_inference",
            "reasoning": str(item.get("reasoning", "")).strip()
            or "(no reasoning provided)",
        }
        if bucket_key == "entries_explicitly_cited":
            entries_cited.append(item_dict)
        elif bucket_key == "entries_likely_influenced":
            entries_likely.append(item_dict)
        else:
            entries_unused.append(item_dict)

    # Account for any entries the model omitted: treat as unused with a
    # parse-recovery reason. Keeps the report exhaustive.
    for i, entry_text in enumerate(entries, start=1):
        if i in seen_indices:
            continue
        first_80 = entry_text[:80] + ("..." if len(entry_text) > 80 else "")
        entries_unused.append({
            "entry_id": entry_ids[i - 1],
            "first_80_chars": first_80,
            "influence_assessment": "unused",
            "confidence": "low",
            "method": "output_inference",
            "reasoning": "Model omitted this entry from its verdict list; recorded as unused",
        })

    return {
        "entries_explicitly_cited": entries_cited,
        "entries_likely_influenced": entries_likely,
        "entries_present_but_unused": entries_unused,
        "overall_utility": overall,
        "overall_reasoning": overall_reasoning,
    }


def _run_aux_call(
    entries: List[str],
    response: str,
    timeout_seconds: float,
) -> Tuple[Optional[str], Optional[str]]:
    """Issue the aux LLM call. Returns ``(raw_response, error_class_name)``.

    On success: ``(raw, None)``. On any failure: ``(None, "ExceptionClassName")``.
    """
    try:
        from agent.auxiliary_client import (
            get_auxiliary_extra_body,
            get_text_auxiliary_client,
        )
    except Exception as exc:
        return None, f"import_failed:{type(exc).__name__}"

    try:
        client, model = get_text_auxiliary_client("influence_assessment")
    except Exception as exc:
        return None, f"client_resolve_failed:{type(exc).__name__}"

    if client is None or not model:
        return None, "no_auxiliary_client_configured"

    system_prompt, user_prompt = build_influence_assessment_prompt(entries, response)

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=DEFAULT_MAX_TOKENS,
            timeout=timeout_seconds,
            extra_body=get_auxiliary_extra_body() or None,
        )
    except Exception as exc:
        return None, f"api_call_failed:{type(exc).__name__}"

    try:
        raw = resp.choices[0].message.content or ""
    except Exception as exc:
        return None, f"response_unparseable:{type(exc).__name__}"

    return raw, None


def assess_influence_inline(
    entries: List[str],
    entry_ids: List[str],
    response: str,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Synchronously assess influence via aux LLM. Returns ``(parsed, error)``.

    On success: ``(parsed_dict, None)``. On failure: ``(None, error_string)``.
    Callers map the error string into an ``error_fallback`` report.
    """
    if not entries:
        return {
            "entries_explicitly_cited": [],
            "entries_likely_influenced": [],
            "entries_present_but_unused": [],
            "overall_utility": "none",
            "overall_reasoning": "no entries in memory at response time",
        }, None

    raw, err = _run_aux_call(entries, response, timeout_seconds)
    if err is not None:
        return None, err
    parsed = parse_influence_assessment_response(raw or "", entries, entry_ids)
    if parsed is None:
        return None, "parse_failed_unrecoverable_json"
    return parsed, None


def spawn_influence_assessment_thread(
    *,
    agent: Any,
    final_response: str,
    entries_snapshot: List[str],
    entry_ids_snapshot: List[str],
    turn_number: int,
    session_id: str,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    memory_block_visible: bool = False,
) -> threading.Thread:
    """Spawn a daemon thread that runs the aux assessment + emits the report.

    Returns the started thread. Caller does NOT join — the thread runs to
    completion independently. ``entries_snapshot`` and ``entry_ids_snapshot``
    must already be copies (caller's responsibility) so post-spawn mutations to
    ``agent._memory_store`` do not corrupt the assessment.
    """

    def _run():
        from agent.memory_instrumentation import (
            emit_report,
            build_influence_self_assessment_report,
        )

        parsed, err = assess_influence_inline(
            entries=entries_snapshot,
            entry_ids=entry_ids_snapshot,
            response=final_response,
            timeout_seconds=timeout_seconds,
        )

        if parsed is None:
            report = build_influence_self_assessment_report(
                session_id=session_id,
                turn_number=turn_number,
                response_length_chars=len(final_response),
                memory_entries_at_response_time=entry_ids_snapshot,
                memory_entries_count=len(entry_ids_snapshot),
                memory_block_visible=memory_block_visible,
                entries_explicitly_cited=[],
                entries_likely_influenced=[],
                entries_present_but_unused=[],
                entries_missing=[],
                overall_utility="unassessed",
                overall_confidence="low",
                assessment_method="error_fallback",
                reasoning=f"Background aux assessment failed: {err}",
            )
        else:
            report = build_influence_self_assessment_report(
                session_id=session_id,
                turn_number=turn_number,
                response_length_chars=len(final_response),
                memory_entries_at_response_time=entry_ids_snapshot,
                memory_entries_count=len(entry_ids_snapshot),
                memory_block_visible=memory_block_visible,
                entries_explicitly_cited=parsed["entries_explicitly_cited"],
                entries_likely_influenced=parsed["entries_likely_influenced"],
                entries_present_but_unused=parsed["entries_present_but_unused"],
                entries_missing=[],
                overall_utility=parsed["overall_utility"],
                overall_confidence="medium",
                assessment_method="output_inference",
                reasoning=(
                    parsed.get("overall_reasoning")
                    or "Aux LLM assessed per-entry influence; see entries lists for details"
                ),
            )

        try:
            emit_report(report, session_id)
        except Exception as exc:
            logger.warning(
                "background influence assessment emit failed (turn %s): %s",
                turn_number,
                exc,
            )

    thread = threading.Thread(
        target=_run,
        name=f"influence_assessment_t{turn_number}",
        daemon=True,
    )
    thread.start()
    return thread


__all__ = [
    "MAX_ENTRY_CHARS",
    "MAX_RESPONSE_CHARS",
    "DEFAULT_TIMEOUT_SECONDS",
    "build_influence_assessment_prompt",
    "parse_influence_assessment_response",
    "assess_influence_inline",
    "spawn_influence_assessment_thread",
]
