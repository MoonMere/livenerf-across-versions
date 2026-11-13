"""Made-up data for the self-tests of extra_numbers.py. Nothing here reads the registered run, and no model is
asked.

make_rows()     graded rows of group main (39 versions, 78 items, three passes) and of groups api and author on
                2.1.322, shaped like the rows grade.py writes: the fields analyze.py and extra_numbers.py read.
                Every answer is made up with a form that LiveNerf's graders can or cannot read, and the score
                follows from it (a right answer only when the form can be read). Differences between versions
                can be put in: accuracy points, a factor on thinking, errors, zero thinking, answers that can't
                be read, tool attempts and an accuracy change for asks that tried a tool. The generator also
                returns what it put in, so that the tests can count it back without the program's own code.
make_raw()      raw records of group main shaped like run.py writes them, with a stream-json stdout: one or two
                assistant messages (each sent as two lines, the first carrying a smaller output count) and a
                result line whose output count is the sum, or the last message alone, or off by a few tokens.
reports()       the registered program's own final and interim reports on those rows (analyze.analyze).
panel()         an item file with ids, families and graders only (no question text, no keys).
"""

import json
import math
import random

import extra_numbers as xn
from ccversions import analyze

VERSIONS = [f"2.1.{n}" for n in range(280, 323) if n not in (297, 298, 313, 320)]
FAMILIES = ["mmlupro"] * 59 + ["gpqa"] * 12 + ["aime"] * 3 + ["comps"] * 4
SCORER = {"mmlupro": "choice", "gpqa": "choice", "aime": "integer", "comps": "rational"}
UNITS = [f"item:{FAMILIES[i]}-{i:02d}" for i in range(78)]
MODEL = "claude-opus-5-5"


def panel() -> dict:
    return {"format": "ccversions-items-v1",
            "items": [{"id": u.split(":", 1)[1], "family": FAMILIES[i], "scorer": SCORER[FAMILIES[i]]}
                      for i, u in enumerate(UNITS)]}


def key_of(i: int) -> str:
    fam = FAMILIES[i]
    if fam == "mmlupro":
        return "ABCDEFGHIJ"[i % 10]
    if fam == "gpqa":
        return "ABCD"[i % 4]
    if fam == "aime":
        return str(100 + i)
    return f"{i % 5 + 1}/{i % 7 + 8}"


def answer(i: int, right: bool, readable: bool, rng: random.Random):
    """An answer in a form the item's grader reads (right or wrong), or in a form it can't read."""
    fam, key = FAMILIES[i], key_of(i)
    if SCORER[fam] == "choice":
        letters = "ABCDEFGHIJ" if fam == "mmlupro" else "ABCD"
        other = letters[(letters.index(key) + 1) % len(letters)]
        if not readable:
            return rng.choice([None, f"{key} or {other}", f"The answer is {key}", "", "AB"])
        x = key if right else other
        return rng.choice([x, f"({x})", f" {x.lower()} ", f"( {x} )"])
    if SCORER[fam] == "integer":
        if not readable:
            return rng.choice([None, f"x = {key}", f"{key}.5", "about 100"])
        x = key if right else str(int(key) + 1)
        return rng.choice([x, f"{x[0]},{x[1:]}", f" {x} "])
    a, b = (int(t) for t in key.split("/"))
    if not readable:
        return rng.choice([None, f"{a / b:.4f}", "a/b", f"{a}/0"])
    if right:
        return rng.choice([key, f"\\frac{{{a}}}{{{b}}}", f"{2 * a}/{2 * b}"])
    return f"{a + 1}/{b}"


def make_rows(seed: int = 1, *, passes: int = 3, acc_shift=None, pass_acc_shift=None, think_mult=None,
              error_by_version=None, error_rate: float = 0.005, void_rate: float = 0.003, zero_by_version=None,
              zero_share: float = 0.02, unread_by_version=None, unread_share: float = 0.02, tool_by_version=None,
              tool_share: float = 0.1, tool_acc_shift: float = 0.0, missing=(), with_small: bool = True,
              think_sd: float = 0.6):
    """acc_shift {version index: points}; pass_acc_shift {pass: {version index: points}}; think_mult {version
    index: factor}; *_by_version {version index: share} in place of the share for all versions; tool_acc_shift:
    points added for an ask that tried a tool; missing: (pass, version index, item index) left out.
    Returns (rows, truth) where truth[(pass, version, unit)] holds what was put in for an ask of group main."""
    acc_shift, pass_acc_shift, think_mult = acc_shift or {}, pass_acc_shift or {}, think_mult or {}
    error_by_version, zero_by_version = error_by_version or {}, zero_by_version or {}
    unread_by_version, tool_by_version = unread_by_version or {}, tool_by_version or {}
    missing = set(missing)
    rng = random.Random(seed)
    chance = [min(0.95, max(0.1, rng.gauss(0.62, 0.25))) for _ in range(78)]
    level = [rng.gauss(6.3, 1.0) for _ in range(78)]
    rows, truth = [], {}
    for p in range(1, passes + 1):
        order_units = list(range(78))
        rng.shuffle(order_units)
        order = 0
        for bi, chunk in enumerate(order_units[b:b + 3] for b in range(0, 78, 3)):
            arms = [(i, "main", v, "stock_blocked") for i in chunk for v in VERSIONS]
            if with_small and p <= 2:
                arms += [(i, g, "2.1.322", g) for i in chunk for g in ("api", "author")]
            rng.shuffle(arms)
            for i, g, v, mode in arms:
                k = VERSIONS.index(v)
                if g == "main" and (p, k, i) in missing:
                    continue
                order += 1
                main = g == "main"
                tried = main and rng.random() < tool_by_version.get(k, tool_share)
                readable = not (main and rng.random() < unread_by_version.get(k, unread_share))
                shift = (acc_shift.get(k, 0.0) + pass_acc_shift.get(p, {}).get(k, 0.0)) if main else 0.0
                shift += tool_acc_shift if tried else 0.0
                right = rng.random() < min(1.0, max(0.0, chance[i] + shift / 100))
                mult = think_mult.get(k, 1.0) if main else (1.2 if g == "api" else 1.0)
                tokens = int(max(0.0, math.exp(level[i] + rng.gauss(0, think_sd) + math.log(mult)) - 1))
                zero = main and rng.random() < zero_by_version.get(k, zero_share)
                if zero:
                    tokens = 0
                u = rng.random()
                er = error_by_version.get(k, error_rate) if main else error_rate
                outcome, reason = ("error", "failed") if u < er else (("void", "retried") if u < er + void_rate
                                                                       else ("scored", None))
                ans = answer(i, right, readable, rng) if outcome == "scored" else None
                score = float(readable and right) if outcome == "scored" else None
                calls = rng.choice([1, 2]) if tried else 0
                row = {
                    "plan": f"F{p}", "ask_id": f"p{p}b{bi:03d}o{order:05d}", "group": g, "pass": p, "block": bi,
                    "order": order, "version": v, "mode": mode, "effort": "high", "unit": UNITS[i],
                    "family": FAMILIES[i], "repeat": 1, "warmup": False, "scored": True, "resend_of": None,
                    "outcome": outcome, "reason": reason, "answer": ans, "score": score,
                    "thinking_tokens": tokens if outcome != "error" else None,
                    "output_tokens": tokens + 150 + rng.randint(0, 500) if outcome != "error" else None,
                    "tool_calls": calls if mode == "stock_blocked" else None,
                    "tool_rounds": (1 if tried else 0) if mode == "stock_blocked" else None,
                    "num_turns": 2 if tried else 1, "elapsed_seconds": round(5 + tokens / 80 + rng.random(), 3),
                    "started_at": f"2026-11-1{p}T{bi % 24:02d}:{order % 60:02d}:00.000+00:00",
                    "first_request_input_tokens": 15000 + 40 * (k // 3) + i if main else 9000 + i,
                    "context_tokens": 15100 + i, "requested_model": MODEL, "remote_flags": "off",
                    "inference_geo": "global",
                }
                rows.append(row)
                if main:
                    truth[(p, v, UNITS[i])] = {"tried": tried, "readable": readable, "zero": zero,
                                               "outcome": outcome}
    return rows, truth


def make_raw(rows: list[dict], *, last_only=(), off_by=()) -> dict:
    """{plan: [records]} for the rows of group main. Versions in last_only report the last message alone on
    the result line of an ask that tried a tool. Versions in off_by report seven tokens more on every ask."""
    out: dict = {}
    for r in rows:
        if r["group"] != "main":
            continue
        rec = {"format": "ccversions-record-v2", "ask_id": r["ask_id"], "plan": r["plan"], "pass": r["pass"],
               "block": r["block"], "order": r["order"], "version": r["version"], "mode": r["mode"],
               "unit": r["unit"], "group": r["group"], "resend_of": r.get("resend_of"),
               "argv": ["claude", "-p", "--model", MODEL, "--output-format", "stream-json", "--verbose"],
               "status": "done" if r["outcome"] != "error" else "timeout", "returncode": 0}
        lines = [{"type": "system", "subtype": "init", "tools": ["Read"], "apiKeySource": "none"}]
        if r["outcome"] != "error":
            total = r["output_tokens"]
            tried = (r.get("tool_calls") or 0) > 0
            parts = [total // 3, total - total // 3] if tried else [total]
            for m, n in enumerate(parts):
                mid = f"msg_{r['ask_id']}_{m}"
                second = {"type": "tool_use", "id": f"tu_{m}", "name": "Read", "input": {}} \
                    if tried and m == 0 else {"type": "text", "text": "..."}
                for block, count in (({"type": "thinking", "thinking": "", "signature": "x"}, max(1, n // 10)),
                                     (second, n)):
                    lines.append({"type": "assistant", "parent_tool_use_id": None,
                                  "message": {"id": mid, "model": MODEL, "role": "assistant", "content": [block],
                                              "usage": {"input_tokens": 3, "output_tokens": count}}})
                if tried and m == 0:
                    lines.append({"type": "user", "parent_tool_use_id": None,
                                  "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "tu_0",
                                                                           "is_error": True, "content": "refused"}]}})
            reported = total
            if tried and r["version"] in last_only:
                reported = parts[-1]
            if r["version"] in off_by:
                reported = total + 7
            lines.append({"type": "result", "subtype": "success", "is_error": False,
                          "num_turns": len(parts), "result": "<answer>...</answer>",
                          "usage": {"input_tokens": 3, "output_tokens": reported,
                                    "output_tokens_details": {"thinking_tokens": r["thinking_tokens"]}},
                          "modelUsage": {MODEL: {"outputTokens": reported}}})
        rec["stdout"] = "\n".join(json.dumps(x) for x in lines) + "\n"
        out.setdefault(r["plan"], []).append(rec)
    return out


def write_raw(raw: dict, base) -> list:
    """Write make_raw()'s records as base/<plan>/asks/<ask_id>.json; returns the plan folders."""
    dirs = []
    for plan, recs in sorted(raw.items()):
        d = base / plan
        (d / "asks").mkdir(parents=True, exist_ok=True)
        for rec in recs:
            (d / "asks" / f"{rec['ask_id']}.json").write_text(json.dumps(rec), encoding="utf-8")
        dirs.append(d)
    return dirs


def as_file(rep: dict) -> dict:
    """What a report looks like once analyze.write_outputs has written it and it is read back."""
    return json.loads(json.dumps(rep))


def reports(rows: list[dict], shuffles: int = 1000) -> tuple[dict, dict]:
    """The registered final report (all passes) and interim report (passes 1 and 2), as analyze.analyze writes
    them, on the given rows."""
    final, _ = analyze.analyze(rows, versions=list(VERSIONS), shuffles=shuffles)
    interim, _ = analyze.analyze([r for r in rows if r["pass"] in (1, 2)], versions=list(VERSIONS),
                                 shuffles=shuffles, interim=True)
    return as_file(final), as_file(interim)


def context(rows, final, interim, is_read, **kw) -> "xn.Context":
    pn = {f"item:{it['id']}": {"family": it["family"], "scorer": it["scorer"]} for it in panel()["items"]}
    return xn.Context(rows, final, interim, pn, is_read, **kw)
