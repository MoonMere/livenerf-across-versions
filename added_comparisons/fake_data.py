"""Made-up data for the self-tests of the two comparisons. Nothing here reads the registered run or the
Desktop group's records, and no model is asked.

make_main_rows()   graded rows of group main, 39 versions, shaped like the rows grade.py writes (the fields the
                   two comparisons and analyze.py read). Each pass asks the items in blocks of 3 in a shuffled
                   order, 23 minutes a block, from a start time that puts about 63 per cent of pass 1 and 49 per
                   cent of pass 2 inside US working hours and none of pass 3 (section 15). A difference inside
                   those hours can be put in: inside_points (accuracy) and inside_think (a share of thinking).
make_exact_rows()  the same layout with every ask of a cell sent at one time and the number of right answers in
                   a cell set exactly: item level + pass level + d_count * (1 if inside), out of 39.
desktop_record()   one record shaped like those dq.py writes (its stdout rebuilt by dq.rebuild_stdout from a
                   made-up session), for the real item file, right or wrong as asked.
"""

import math
import random
import sys
from datetime import datetime, timedelta, timezone

import common

sys.path.insert(0, str(common.PROGRAM / "Desktop组"))
import dq  # noqa: E402

from ccversions import modes  # noqa: E402

VERSIONS = [f"2.1.{n}" for n in range(280, 323) if n not in (297, 298, 313, 320)]
PASS_START = {1: datetime(2026, 11, 11, 10, 18, tzinfo=timezone.utc),   # 10:18 to 20:16 UTC: 63% inside
              2: datetime(2026, 11, 11, 20, 6, tzinfo=timezone.utc),    # 20:06 to 06:04 UTC: 49% inside
              3: datetime(2026, 11, 12, 1, 30, tzinfo=timezone.utc)}    # 01:30 to 11:28 UTC: none inside
BLOCK_MINUTES = 23
BLOCK_UNITS = 3
MODEL = "claude-opus-5-5"


def fake_units(n: int = 78) -> list[str]:
    return [f"item:fake-{i:02d}" for i in range(n)]


def iso(t: datetime) -> str:
    return t.isoformat(timespec="milliseconds")


def schedule(units, passes, rng, *, start=None, versions=VERSIONS, one_time_per_cell=False, blocks_of_pass=None):
    """{(pass, unit, version): time}. blocks_of_pass: {pass: how many blocks are sent} for a pass that stopped."""
    start = {**PASS_START, **(start or {})}
    out = {}
    for p in passes:
        order = list(units)
        rng.shuffle(order)
        blocks = [order[b:b + BLOCK_UNITS] for b in range(0, len(order), BLOCK_UNITS)]
        if blocks_of_pass and p in blocks_of_pass:
            blocks = blocks[:blocks_of_pass[p]]
        for bi, chunk in enumerate(blocks):
            t0 = start[p] + timedelta(minutes=BLOCK_MINUTES * bi)
            asks = [(u, v) for u in chunk for v in versions]
            rng.shuffle(asks)
            step = BLOCK_MINUTES * 60 / len(asks)
            for k, (u, v) in enumerate(asks):
                out[(p, u, v)] = (t0 if one_time_per_cell else t0 + timedelta(seconds=k * step), bi)
    return out


def _row(p, u, v, t, bi, n, *, score, thinking, outcome="scored", reason=None):
    return {"plan": f"F{p}", "ask_id": f"p{p}o{n:06d}", "group": "main", "pass": p, "block": bi, "order": n,
            "version": v, "mode": "stock_blocked", "effort": "high", "unit": u, "family": u.split(":")[1].split("-")[0],
            "repeat": 1, "warmup": False, "scored": True, "resend_of": None, "outcome": outcome, "reason": reason,
            "score": score, "thinking_tokens": thinking,
            "output_tokens": None if thinking is None else thinking + 200, "tool_calls": 0, "tool_rounds": 0,
            "num_turns": 1, "elapsed_seconds": 10.0, "started_at": iso(t), "requested_model": MODEL}


def make_main_rows(units, *, passes=(1, 2, 3), seed=1, inside_points=0.0, inside_think=0.0,
                   pass_points=None, error_share=0.0, versions=VERSIONS, start=None, blocks_of_pass=None):
    rng = random.Random(seed)
    pass_points = pass_points if pass_points is not None else {1: 0.0, 2: -0.01, 3: 0.005}
    chance = {u: min(0.95, max(0.08, rng.gauss(0.62, 0.22))) for u in units}
    level = {u: rng.gauss(6.0, 1.3) for u in units}
    rows = []
    times = schedule(units, passes, rng, start=start, versions=versions, blocks_of_pass=blocks_of_pass)
    for n, ((p, u, v), (t, bi)) in enumerate(sorted(times.items(), key=lambda kv: kv[1][0]), 1):
        inside = common.in_us_hours(iso(t))
        pr = chance[u] + pass_points.get(p, 0.0) + (inside_points if inside else 0.0)
        think = level[u] + rng.gauss(0, 0.9) + (math.log(1 + inside_think) if inside else 0.0)
        if rng.random() < error_share:
            rows.append(_row(p, u, v, t, bi, n, score=None, thinking=None, outcome="error", reason="failed"))
        else:
            rows.append(_row(p, u, v, t, bi, n, score=float(rng.random() < pr),
                             thinking=int(max(0.0, math.exp(think) - 1))))
    return rows


def make_exact_rows(units, *, d_count=3, pass_counts=None, versions=VERSIONS, seed=2):
    """Right answers in a cell = 10 + (item number * 7) % 20 + pass_counts[pass] + d_count * inside, so the cell
    means follow item + pass + d * share exactly, with d = d_count / 39. Thinking is 100 tokens everywhere."""
    rng = random.Random(seed)
    pass_counts = pass_counts if pass_counts is not None else {1: 0, 2: -1, 3: 1}
    times = schedule(units, (1, 2, 3), rng, versions=versions, one_time_per_cell=True)
    rows = []
    for n, ((p, u, v), (t, bi)) in enumerate(sorted(times.items(), key=lambda kv: kv[1][0]), 1):
        i = units.index(u)
        right = 10 + (i * 7) % 20 + pass_counts[p] + d_count * common.in_us_hours(iso(t))
        rows.append(_row(p, u, v, t, bi, n, score=float(versions.index(v) < right), thinking=100))
    return rows


def desktop_record(inputs, unit, rnd, n, order, *, correct, thinking, started, version="2.1.321", status="done",
                   text_ok=True, effort_ok=True, tool_round=False):
    """One Desktop record as dq.write_record() lays it out, from a made-up session file. With tool_round the
    model first calls Bash, the hook refuses it with the same sentence as mode stock_blocked, then it answers."""
    u = inputs.unit(unit)
    answer = u.target if correct else "ZZZ"
    stamp = lambda t: t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"  # noqa: E731
    first = {"type": "user", "message": {"role": "user", "content": "(made up)"}, "cwd": "/private/tmp/wd",
             "version": version, "permissionMode": "default", "entrypoint": "claude-desktop", "timestamp": stamp(started)}
    entries, assistants, t = [first], [], started
    if tool_round:
        t += timedelta(seconds=4)
        a1 = {"type": "assistant", "timestamp": stamp(t), "message": {
            "id": f"msg_{order}_a", "model": MODEL, "role": "assistant", "stop_reason": "tool_use",
            "content": [{"type": "tool_use", "id": f"toolu_{order}", "name": "Bash", "input": {"command": "true"}}],
            "usage": {"input_tokens": 3, "output_tokens": 40, "output_tokens_details": {"thinking_tokens": 0}}}}
        entries.append(a1)
        assistants.append(a1)
        t += timedelta(seconds=1)
        entries.append({"type": "user", "timestamp": stamp(t), "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": f"toolu_{order}", "is_error": True,
             "content": f"PreToolUse:Bash hook error: [{modes.BLOCK_HOOK_COMMAND}]: {modes.BLOCK_MESSAGE}"}]}})
    t += timedelta(seconds=8)
    a2 = {"type": "assistant", "timestamp": stamp(t), "message": {
        "id": f"msg_{order}_b", "model": MODEL, "role": "assistant", "stop_reason": "end_turn",
        "content": [{"type": "text", "text": f"Worked it out.\n<answer>{answer}</answer>"}],
        "usage": {"input_tokens": 3, "output_tokens": thinking + 30, "output_tokens_details": {"thinking_tokens": thinking}}}}
    entries.append(a2)
    assistants.append(a2)
    sess = {"entries": entries, "first_user": first, "first_text": "(made up)", "assistants": assistants,
            "last_stop": "end_turn", "ended": True, "sidechain": 0}
    stdout, info = dq.rebuild_stdout(sess)
    return {
        "format": "ccversions-record-v1", "ask_id": f"d{rnd}q{n:02d}", "plan": "DQ", "fingerprint": None, "pass": rnd,
        "block": None, "order": order, "version": version, "mode": "stock_blocked", "effort": "high",
        "effort_asked_for": "high", "effort_ok": effort_ok, "unit": unit, "repeat": rnd, "warmup": False,
        "scored": True, "label": "desktop", "group": "desktop", "resend_of": None, "model": MODEL,
        "account_label": "second-account", "login_method": "desktop app", "parallel": 1, "cwd": "/private/tmp/wd",
        "argv": ["--output-format", "stream-json", "--model", MODEL, "--effort", "high", "--permission-mode", "default"],
        "argv_rebuilt": True, "stdout_rebuilt": True, "text_ok": text_ok, "wrapper_ok": text_ok, "timeout_seconds": 900,
        "status": status, "problems": [], "started_at": first["timestamp"], "ended_at": a2["timestamp"],
        "elapsed_seconds": (t - started).total_seconds(), "returncode": 0 if status == "done" else None,
        "timed_out": status == "timeout", "stdout": stdout, "stderr": "",
        "desktop": {"session_file": f"made-up-{order}.jsonl", "attempt": 1, **info},
    }
