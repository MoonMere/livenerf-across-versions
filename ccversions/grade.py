"""Grade stored answers with the LiveNerf author's graders. A separate step: run it as often as you like
on the same records, and the result is the same every time (checklist C2).

For every record, in this order (the author's order, livenerf/providers/claudecode.py lines 216-237):

  error   the runner did not get a clean result (refused, timeout, launch error, minimum-version stop,
          usage limit, not on the subscription, dirty working folder; for mode api also an HTTP error,
          an error event in the stream, a cut-off stream, a network failure), or Claude Code exited
          non-zero, reported is_error, or printed no result; or the output says isUsingOverage true or an
          apiKeySource other than none (checklist E3)
  void    fallback   a model other than the one the ask named (claude-opus-5-5 unless the plan named
                     claude-fable-5-2) appears in modelUsage; for mode api, the API's reply names
                     another model than the request
          tool_ran   mode stock_blocked only (trial layer 7), checked before fallback: a tool call was
                     carried out instead of being refused, a subagent sent events, or the probe's canary
                     word came back
          server_tool  any Claude Code mode: the result line counts a web search or web fetch carried out
                     on the server (those never pass the hook; none was seen in the trial runs)
          retried    num_turns is not 1; in mode stock_blocked, num_turns is not 1 + the rounds of
                     refused tool calls (each round of calls and the answer after it is one more turn,
                     so only a turn beyond those is void, such as a continuation after the output cap)
          refusal    stop_reason is "refusal"
          max_tokens mode api only: stop_reason is "max_tokens". Claude Code goes on by itself after such
                     a stop, and that second turn makes the ask "retried" above; one API request has no
                     second turn, so the cut-off answer is void under its own name (trial layer 6)
          context    modes "author" and "api" only: context tokens above len(system) + len(prompt) +
                     2,500 (the author's context_limit(), imported from his code; mode api sends a copy
                     of mode author's request)
  scored  the author's extract_answer() on the result text, then choice_score / integer_score /
          rational_score against the target, all imported from livenerf/scorers/checks.py. The result
          text is Claude Code's `result` field; in trial layer 1's refused calls it held the text of the
          last message only, so a stock_blocked ask that tried tools is graded on its last answer, and its
          row says how many calls it tried (tool_calls, tools_tried, tool_outcomes)

Probes are never scored; they get their fields and their integrity status only. The rules for the
modes that keep the built-in system prompt are the author's rules. The trial did not change them
(checklist C9).

Outputs: graded.jsonl (local: one row per ask, no question text), summary.json, and public_table.csv
(only columns that are safe to publish: no answers, no targets, no paths, no ids of sessions).
"""

import csv
import hashlib
import json
import re
import statistics
import sys
from pathlib import Path

from . import extract

RUNNER_OK = "done"
PUBLIC_COLUMNS = ("pass", "block", "order", "version", "mode", "effort", "unit", "family", "warmup", "outcome",
                  "reason", "score", "context_tokens", "output_tokens", "thinking_tokens", "num_turns",
                  "inference_geo", "elapsed_seconds")


def import_author_graders(author_repo: Path):
    sys.dont_write_bytecode = True
    repo = str(author_repo.resolve())
    if repo not in sys.path:
        sys.path.insert(0, repo)
    from livenerf.providers import claudecode
    from livenerf.scorers import checks as author_checks

    if not str(Path(author_checks.__file__).resolve()).startswith(repo):
        raise RuntimeError(f"livenerf graders imported from {author_checks.__file__}, not from {repo}")
    return author_checks, claudecode


def integrity(record: dict, f: dict, system_prompt: str, prompt: str, context_limit) -> tuple[str, str | None]:
    api = extract.is_api(record)
    if record.get("status") != RUNNER_OK:
        return "error", record.get("status") or "unknown"
    if (not api and record.get("returncode") != 0) or not f["has_result"] or f["is_error"]:
        return "error", "refusal" if f["stop_reason"] == "refusal" else "failed"
    if extract.billing_problems(f["api_key_source"], f["is_using_overage"]):
        return "error", "not_subscription"  # checklist E3; records made before the runner stopped on it
    blocked = extract.blocks_tools(record)
    if blocked and (f["tools_ran"] or f["subagent_events"] or f["canary_hits"]):
        # trial layer 7: a call the hook should have refused was carried out (or a subagent ran, or the
        # canary word came back), so the answer may rest on what the tool brought in
        return "void", "tool_ran"
    if f.get("server_tool_requests"):
        return "void", "server_tool"
    wanted = f["requested_model"]  # claude-opus-5-5, or the model a probe-only plan named for this ask
    served = f["served_models"] or [wanted]
    if set(served) != {wanted}:
        return "void", "fallback"
    if f["num_turns"] not in (None, 1):
        # stock_blocked: every round of refused tool calls adds one turn, so num_turns = 1 + rounds is the
        # normal shape there; a turn more than that (a continuation after the output cap, a retry) is void
        if not (blocked and f["tool_rounds"] is not None and f["num_turns"] == 1 + f["tool_rounds"]):
            return "void", "retried"
    if f["stop_reason"] == "refusal":
        return "void", "refusal"
    if api and f["stop_reason"] == "max_tokens":
        return "void", "max_tokens"
    if record.get("mode") in ("author", "api") and f["context_tokens"] > context_limit(system_prompt, prompt):
        return "void", "context"
    return "ok", None


def grade_records(records: list[dict], inputs, author_checks, claudecode) -> list[dict]:
    score_fn = {"choice": author_checks.choice_score, "integer": author_checks.integer_score,
                "rational": author_checks.rational_score}
    rows = []
    for rec in sorted(records, key=lambda r: r.get("order", 0)):
        unit = inputs.unit(rec["unit"])
        f = extract.fields(rec)
        status, reason = integrity(rec, f, inputs.system_prompt, unit.text, claudecode.context_limit)
        answer = score = None
        outcome = status if status != "ok" else ("scored" if unit.kind == "item" and rec.get("scored") else "ok_unscored")
        if outcome == "scored":
            answer = author_checks.extract_answer(extract.result_text(rec) or "")
            score = score_fn[unit.scorer](answer, unit.target)
        elif unit.kind == "probe" and status == "ok":
            answer = author_checks.extract_answer(extract.result_text(rec) or "")
        rows.append({
            **{k: rec.get(k) for k in ("ask_id", "pass", "block", "order", "version", "mode", "effort", "unit",
                                       "repeat", "warmup", "scored", "started_at", "elapsed_seconds", "fingerprint",
                                       "binary_sha256", "remote_flags", "account_label", "label", "options",
                                       "config_dir", "plan", "group", "resend_of")},
            # api_key_source (the init event's apiKeySource) and is_using_overage (the usage reading's
            # isUsingOverage) come with the fields below; both are None for an output without them
            "family": unit.family, "outcome": outcome, "reason": reason, "answer": answer, "score": score,
            **{k: v for k, v in f.items() if k not in ("init",)},
            "init_tools": (f["init"] or {}).get("tools"), "init_mcp_servers": (f["init"] or {}).get("mcp_servers"),
            "init_skills": (f["init"] or {}).get("skills"), "init_plugins": (f["init"] or {}).get("plugins"),
            "init_permission_mode": (f["init"] or {}).get("permissionMode"),
            "init_api_key_source": (f["init"] or {}).get("apiKeySource"),
            "init_claude_code_version": (f["init"] or {}).get("claude_code_version"),
            "memory_files_added": rec.get("memory_files_added"),
            **{f"{name}_changes": _diff_size(rec.get(f"{name}_diff")) for name in ("config_dir", "home_dir", "tmpdir")},
        })
    return rows


def _diff_size(diff: dict | None) -> int | None:
    """How many files one ask added, removed or changed in a watched folder (None: not listed)."""
    if not diff:
        return None
    return sum(len(diff.get(k) or []) for k in ("added", "removed", "changed"))


CLASSIFIER_REASONS = ("refusal", "retried", "fallback")  # the author's classifier events (record.py)


def _count_values(values) -> dict:
    out: dict = {}
    for v in values:
        k = str(v)
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


def _spread(values) -> dict:
    """median, min, max, total and how many of a list of numbers (None left out)."""
    v = [x for x in values if x is not None]
    if not v:
        return {"n": 0, "median": None, "min": None, "max": None, "total": None}
    return {"n": len(v), "median": statistics.median(v), "min": min(v), "max": max(v), "total": round(sum(v), 3)}


def _item_part(items: list[dict]) -> dict:
    """What one group's item asks came to. Scored, accuracy and the output-token median count only the
    asks that were scored, as the author's results/daily.csv counts only the samples without an error
    (livenerf/record.py: scored, score, output_tokens_median)."""
    scored = [r for r in items if r["outcome"] == "scored"]
    correct = sum(r["score"] for r in scored)
    not_scored = [r for r in items if r["outcome"] != "scored"]
    return {
        "asks": len(items),
        "scored": len(scored),
        "correct": correct,
        "accuracy": correct / len(scored) if scored else None,
        "void": len([r for r in items if r["outcome"] == "void"]),
        "void_by_reason": _count_values(r["reason"] for r in items if r["outcome"] == "void"),
        "error": len([r for r in items if r["outcome"] == "error"]),
        "error_by_reason": _count_values(r["reason"] for r in items if r["outcome"] == "error"),
        "classifier_events": len([r for r in items if r["reason"] in CLASSIFIER_REASONS]),
        "not_scored_asks": [{"ask_id": r["ask_id"], "unit": r["unit"], "outcome": r["outcome"], "reason": r["reason"]}
                            for r in not_scored],
        "output_tokens_scored": _spread(r["output_tokens"] for r in scored),
        "thinking_tokens_scored": _spread(r["thinking_tokens"] for r in scored),
        "context_tokens_scored": _spread(r["context_tokens"] for r in scored),
    }


def _tools_part(g: list[dict]) -> dict:
    """Mode stock_blocked (trial layer 7): what the group's asks tried with tools. Only groups whose rows
    carry tool fields get it, so the summaries of other modes stay as they were."""
    tried = [r for r in g if r.get("tool_calls")]
    by_tool: dict = {}
    outcomes: dict = {}
    for r in g:
        for name in r.get("tools_tried") or []:
            by_tool[str(name)] = by_tool.get(str(name), 0) + 1
        for k, v in (r.get("tool_outcomes") or {}).items():
            outcomes[k] = outcomes.get(k, 0) + v
    return {
        "asks_that_tried_tools": len(tried),
        "items_that_tried_tools": len([r for r in tried if (r.get("unit") or "").startswith("item:")]),
        "scored_items_that_tried_tools": len([r for r in tried if r["outcome"] == "scored"]),
        "correct_among_those": sum(r["score"] or 0 for r in tried if r["outcome"] == "scored"),
        "tool_calls": sum(r.get("tool_calls") or 0 for r in g),
        "by_tool": dict(sorted(by_tool.items())),
        "outcomes": dict(sorted(outcomes.items())),
        "asks_with_a_call_not_refused_by_the_hook": sorted(r["ask_id"] for r in g if r.get("tools_not_blocked_by_hook")),
        "asks_where_a_tool_ran": sorted(r["ask_id"] for r in g if r.get("tools_ran") or r.get("subagent_events")),
        "asks_where_the_canary_came_back": sorted(r["ask_id"] for r in g if r.get("canary_hits")),
        "num_turns_of_asks_that_tried_tools": _count_values(r.get("num_turns") for r in tried),
    }


def summarise(rows: list[dict]) -> dict:
    """One entry per (mode, effort, version), and per model when an ask named another model than
    claude-opus-5-5 (the key then ends in " | <model>"; trial layer 6). Besides the old fields (asks, scored, correct, accuracy,
    outcomes, reasons, the two medians over the scored asks) each entry splits the asks into items,
    probes and warm-ups, and gives for the items: how many were void or an error and why, the
    author's classifier events, and the spread of output, thinking and input (context) tokens over
    the scored ones, per family too; and for every ask of the group: turns, wall time, Claude Code's own
    duration, stop and terminal reasons, served models, region, the usage reading at the first and the
    last ask, and the two billing fields. author_daily_row puts the item numbers into the columns of
    the author's results/daily.csv (family "all"), for trial layer 4's comparison."""
    groups: dict = {}
    for r in rows:
        model = r.get("requested_model") or extract.MODEL
        key = f"{r['mode']} | {r['effort']} | {r['version']}" + ("" if model == extract.MODEL else f" | {model}")
        groups.setdefault(key, []).append(r)
    out = {}
    for key, g in sorted(groups.items()):
        items = [r for r in g if (r.get("unit") or "").startswith("item:")]
        scored = [r for r in items if r["outcome"] == "scored"]
        by_order = sorted(g, key=lambda r: r.get("order") or 0)
        readings = [r.get("weekly_utilization") for r in by_order if r.get("weekly_utilization") is not None]
        part = _item_part(items)
        families = {}
        for fam in sorted({r.get("family") for r in items if r.get("family")}):
            fp = _item_part([r for r in items if r.get("family") == fam])
            families[fam] = {k: fp[k] for k in ("asks", "scored", "correct", "accuracy", "void", "error",
                                                "output_tokens_scored")}
        out[key] = {
            # the fields this summary always had
            "asks": len(g), "scored": len(scored), "correct": part["correct"], "accuracy": part["accuracy"],
            "outcomes": _count_values(r["outcome"] for r in g),
            "reasons": _count_values(r["reason"] for r in g if r["reason"]),
            "median_output_tokens": part["output_tokens_scored"]["median"],
            "median_context_tokens": part["context_tokens_scored"]["median"],
            # what kind of asks
            "item_asks": len(items),
            "probe_asks": len(g) - len(items),
            "warmup_asks": len([r for r in g if r.get("warmup")]),
            "items": part,
            "families": families,
            # every ask of the group, items, probes and warm-ups alike
            "all_asks": {
                "num_turns": _count_values(r.get("num_turns") for r in g),
                "elapsed_seconds": _spread(r.get("elapsed_seconds") for r in g),
                "duration_ms": _spread(r.get("duration_ms") for r in g),
                "stop_reason": _count_values(r.get("stop_reason") for r in g),
                "terminal_reason": _count_values(r.get("terminal_reason") for r in g),
                "requested_model": _count_values(r.get("requested_model") for r in g),
                "served_models": _count_values(",".join(r.get("served_models") or []) for r in g),
                "inference_geo": _count_values(r.get("inference_geo") for r in g),
                "output_format": _count_values(r.get("output_format") for r in g),
                "api_key_source": _count_values(r.get("api_key_source") for r in g),
                "is_using_overage": _count_values(r.get("is_using_overage") for r in g),
                "weekly_utilization_first": readings[0] if readings else None,
                "weekly_utilization_last": readings[-1] if readings else None,
                "asks_without_a_reading": len(g) - len(readings),
                "input_tokens": _spread(r.get("input_tokens") for r in g),
                "cache_creation_input_tokens": _spread(r.get("cache_creation_input_tokens") for r in g),
                "cache_read_input_tokens": _spread(r.get("cache_read_input_tokens") for r in g),
                "context_tokens": _spread(r.get("context_tokens") for r in g),
                "output_tokens": _spread(r.get("output_tokens") for r in g),
                "fingerprints": _count_values(r.get("fingerprint") for r in g),
                **({"api_cost_usd": _spread(r.get("api_cost_usd") for r in g),
                    "api_http_status": _count_values(r.get("api_http_status") for r in g),
                    "api_beta_set": _count_values(r.get("beta_set") for r in g)}
                   if any(r.get("transport") == "api" for r in g) else {}),
            },
            **({"tools": _tools_part(g)} if any(r.get("tool_calls") is not None for r in g) else {}),
            "author_daily_row": {
                "samples": len(items), "scored": len(scored), "errors": len(items) - len(scored),
                "classifier_events": part["classifier_events"],
                "score": round(part["accuracy"], 4) if part["accuracy"] is not None else None,
                "output_tokens_median": part["output_tokens_scored"]["median"],
                "cli_version": ",".join(sorted({r["version"] for r in g})),
                "harness_hash": ",".join(sorted({str(r.get("fingerprint")) for r in g})),
            },
        }
    return out


def rows_digest(rows: list[dict]) -> str:
    return hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


PUBLIC_BAD = re.compile(r"/Users/|/private/|/Volumes/|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def write_outputs(rows: list[dict], out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "graded.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary = {"asks": len(rows), "graded_digest": rows_digest(rows), "groups": summarise(rows)}
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n")
    lines = []
    for r in rows:
        lines.append({k: r.get(k) for k in PUBLIC_COLUMNS})
    with open(out_dir / "public_table.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PUBLIC_COLUMNS)
        w.writeheader()
        w.writerows(lines)
    text = (out_dir / "public_table.csv").read_text()
    leaks = sorted(set(PUBLIC_BAD.findall(text)))
    if leaks:  # checklist H3: never let a path or an e-mail address into the public table
        (out_dir / "public_table.csv").unlink()
        raise RuntimeError(f"public table held paths or addresses {leaks[:5]}; it was deleted")
    return summary


def load_records(run_dir: Path) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted((run_dir / "asks").glob("*.json"))]
