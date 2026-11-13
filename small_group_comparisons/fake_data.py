"""Made-up data for the self-tests of small_group_comparisons.py. Nothing here reads a record of the experiment.

A World is a list of made-up asks, each with what its answer is (right, wrong, no <answer> block, an answer in a
form the grader does not accept, or a void), its thinking and output tokens and when it was sent. From the same
list the World writes what the program reads in the real run:

  graded/F1 ... F3r/graded.jsonl   graded rows of the registered run (main on 39 versions, flags_on and author on
                                   passes 1 and 2), as grade.py writes them
  final/report.json                made by the registered analysis itself (analyze.analyze) from those rows
  S3/, NS1/ ... NS3r/, A3/         raw records of the added plans (stream-json output as Claude Code prints it),
                                   for grade.py to grade with the stand-in graders below
  daily.csv                        a made-up copy of LiveNerf's results/daily.csv

The tests work out every expected number from the list of asks directly, without the program, grade.py or
analyze.py.
"""

import csv
import json
import random
import re
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

from ccversions import analyze

try:
    from ccversions import items as items_mod
except ImportError:
    # The public repository holds only the modules that read and judge answers. ccversions/items.py, which
    # loads the item file, is not among them. These two classes have the fields and the two methods of
    # items.Unit and items.Inputs that grade.py and the program use, so the tests run there too.
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class _Unit:
        key: str
        kind: str
        id: str
        text: str
        scorer: str | None = None
        target: str | None = None
        family: str | None = None

    @dataclass(frozen=True)
    class _Inputs:
        system_prompt: str
        items: dict
        probes: dict
        item_file_sha256: str
        probe_file_sha256: str

        def unit(self, key: str):
            kind, _, uid = key.partition(":")
            return {"item": self.items, "probe": self.probes}[kind][uid]

        def item_keys(self) -> list:
            return [u.key for u in self.items.values()]

    items_mod = SimpleNamespace(Unit=_Unit, Inputs=_Inputs, stand_in=True)

VERSIONS =[f"2.1.{n}" for n in range(280, 323) if n not in (297, 298, 313, 320)]  # 39, as the registered run
FLAGS_VERSIONS = ("2.1.280", "2.1.299", "2.1.308", "2.1.322")
NOSENT_VERSIONS = ("2.1.280", "2.1.322")
MODEL = "claude-opus-5-5"
MARK = "zq-made-up-answer-text-zq"   # in every answer text, and it must never reach an output
SYSTEM = "(made-up system prompt)"
UTC = timezone.utc

# 78 made-up items with the item file's mix of graders: 59 + 12 choice, 3 integer, 4 rational
FAMILIES = [("mmlupro", "choice")] * 59 + [("gpqa", "choice")] * 12 + [("aime", "integer")] * 3 + [("comps", "rational")] * 4
UNITS = [f"item:fake-{i:03d}" for i in range(78)]


def target(i: int) -> str:
    scorer = FAMILIES[i][1]
    if scorer == "choice":
        return "ABCDEFGHIJ"[i % 10]
    if scorer == "integer":
        return str(100 + i)
    return f"{i}/{i + 7}"


def answer_for(i: int, kind: str) -> str | None:
    """The text inside <answer> for an answer of this kind. None stands for no block at all."""
    scorer, t = FAMILIES[i][1], target(i)
    if kind == "right":
        return t
    if kind == "wrong":
        if scorer == "choice":
            return "B" if t != "B" else "(C)"
        return str(int(t) + 1) if scorer == "integer" else "1/1000"
    if kind == "bad_form":   # a block, but not the form the grader accepts
        return {"choice": f"{t} or B", "integer": f"about {t}", "rational": "0.75"}[scorer]
    if kind == "none":
        return None
    raise ValueError(kind)


def fake_inputs() -> items_mod.Inputs:
    items = {}
    for i, u in enumerate(UNITS):
        uid = u.split(":", 1)[1]
        items[uid] = items_mod.Unit(key=u, kind="item", id=uid, text=f"(made-up question {i})", scorer=FAMILIES[i][1],
                                    target=target(i), family=FAMILIES[i][0])
    return items_mod.Inputs(system_prompt=SYSTEM, items=items, probes={}, item_file_sha256="0" * 64,
                            probe_file_sha256="0" * 64)


# ------------------------------------------------------------------ stand-ins for LiveNerf's graders and parser

_ANSWER_RE = re.compile(r"<answer>(.*?)</answer>", re.DOTALL | re.IGNORECASE)


def rational(text):
    """An integer, a/b or \\frac{a}{b} as a Fraction, and None for anything else (the behaviour of LiveNerf's
    rational(), written again here so that the tests need no copy of LiveNerf)."""
    t = re.sub(r"[\s$]", "", str(text)).replace("\\dfrac", "\\frac").replace("\\tfrac", "\\frac")
    m = re.fullmatch(r"(-?)\\frac\{(-?\d+)\}\{(\d+)\}", t)
    if m:
        return Fraction(int(m.group(2)), int(m.group(3))) * (-1 if m.group(1) else 1)
    m = re.fullmatch(r"(-?\d+)(?:/(\d+))?", t)
    if m and (m.group(2) is None or int(m.group(2)) != 0):
        return Fraction(int(m.group(1)), int(m.group(2) or 1))
    return None


def _extract(text):
    found = _ANSWER_RE.findall(text or "")
    return found[-1].strip() if found else None


def _choice(answer, t):
    return 0.0 if answer is None else float(answer.strip().strip("()").strip().upper() == t)


def _integer(answer, t):
    if answer is None:
        return 0.0
    c = re.sub(r"[\s,]", "", answer)
    return float(re.fullmatch(r"-?\d+", c) is not None and int(c) == int(t))


def _rational(answer, t):
    if answer is None:
        return 0.0
    a, b = rational(answer), rational(t)
    return float(a is not None and a == b)


AUTHOR_CHECKS = SimpleNamespace(extract_answer=_extract, choice_score=_choice, integer_score=_integer,
                                rational_score=_rational)
CLAUDECODE = SimpleNamespace(context_limit=lambda system, prompt: len(system) + len(prompt) + 2500)


def fake_grader(module):
    """The program's Grader with the made-up items and the stand-in graders."""
    return module.Grader(fake_inputs(), AUTHOR_CHECKS, CLAUDECODE, rational)


# ------------------------------------------------------------------ the made-up asks

def _r(*key) -> float:
    return random.Random("|".join(map(str, key))).random()


def iso(t: datetime) -> str:
    return t.astimezone(UTC).isoformat(timespec="seconds")


class World:
    """nosent: "same" (every nosent ask is main's ask of the same version, pass and item: no difference) or
    "planted" (on 2.1.280: twelve items that main gets right in every pass are wrong in every pass, and every
    ask thinks twice as much, counting tokens + 1. On 2.1.322: six answers no grader can read and one void).
    flags: "flat" (flags_on answers the same on its four versions) or "planted_322" (on 2.1.322, fifteen items
    it gets right elsewhere in every pass are wrong, and it thinks half as much, counting tokens + 1)."""

    def __init__(self, *, nosent: str = "planted", flags: str = "planted_322"):
        self.nosent_mode, self.flags_mode = nosent, flags
        self.asks = []   # one dict per ask as it counts in the end (a resent ask carries its resend's values)
        self._main()
        self._flags()
        self._author()
        self._nosent()

    # every ask: source (plan), group, version, pass, unit, i, kind, thinking, output, started, resent
    def _add(self, source, group, version, p, i, kind, thinking, output, started, *, resent=False):
        self.asks.append({"source": source, "group": group, "version": version, "pass": p, "unit": UNITS[i], "i": i,
                          "kind": kind, "thinking": thinking, "output": output, "started": started, "resent": resent})

    def _main(self):
        for p in (1, 2, 3):
            t0 = datetime(2026, 11, 10 + p, 9, 0, tzinfo=UTC)
            for vi, v in enumerate(VERSIONS):
                for i in range(78):
                    kind = "right" if _r("main", v, p, i) < 0.65 else "wrong"
                    th = 80 + int(_r("main-think", v, p, i) * 400)
                    out = th + 200 + int(_r("main-out", v, p, i) * 100)
                    resent = (p == 1 and vi == 20 and i == 0)   # one ask of the registered run is resent
                    self._add(f"F{p}", "main", v, p, i, kind, th, out, t0 + timedelta(seconds=vi * 78 + i),
                              resent=resent)

    def main_ask(self, v, p, i):
        return next(a for a in self.asks if a["group"] == "main" and a["version"] == v and a["pass"] == p and a["i"] == i)

    def _flags(self):
        right = {(p, i): _r("flags", p, i) < 0.75 for p in (1, 2, 3) for i in range(78)}
        self.Q = [i for i in range(78) if all(right[(p, i)] for p in (1, 2, 3))][:15]
        for p in (1, 2, 3):
            t0 = datetime(2026, 11, 10 + p, 12, 0, tzinfo=UTC)
            for v in FLAGS_VERSIONS:
                for i in range(78):
                    kind = "right" if right[(p, i)] else "wrong"
                    th = 2 * (40 + int(_r("flags-think", p, i) * 200)) + 1      # odd, so that (th + 1) / 2 - 1 is whole
                    if self.flags_mode == "planted_322" and v == "2.1.322":
                        th = (th + 1) // 2 - 1
                        if i in self.Q:
                            kind = "wrong"
                    out = th + 250
                    self._add("S3" if p == 3 else f"F{p}", "flags_on", v, p, i, kind, th, out,
                              t0 + timedelta(seconds=FLAGS_VERSIONS.index(v) * 78 + i))

    def _author(self):
        for v in ("2.1.280", "2.1.322"):
            for p in (1, 2, 3):
                for i in range(78):
                    kind = "right" if _r("author", v, p, i) < 0.7 else "wrong"
                    th = 50 + int(_r("author-think", v, p, i) * 300)
                    out = th + 150 + int(_r("author-out", v, p, i) * 400)
                    if p == 1:
                        t = datetime(2026, 11, 11, 10, 0, tzinfo=UTC) + timedelta(minutes=i)
                    elif p == 2:   # pass 2 runs over midnight UTC: 50 asks on 11 November, 28 on 12 November
                        t = datetime(2026, 11, 11, 23, 0, tzinfo=UTC) + timedelta(minutes=i if i < 50 else i + 20)
                    else:
                        t = datetime(2026, 11, 13, 1, 0, tzinfo=UTC) + timedelta(minutes=i)
                    source = f"F{p}" if p < 3 else ("S3" if v == "2.1.280" else "A3")
                    self._add(source, "author", v, p, i, kind, th, out, t)

    def _nosent(self):
        m280 = [i for i in range(78) if all(self.main_ask("2.1.280", p, i)["kind"] == "right" for p in (1, 2, 3))]
        self.P = m280[:12] if self.nosent_mode == "planted" else []
        self.unread = {}
        for p in (1, 2, 3):
            t0 = datetime(2026, 11, 13, 3, 0, tzinfo=UTC) + timedelta(hours=2 * (p - 1))
            for v in NOSENT_VERSIONS:
                for i in range(78):
                    m = self.main_ask(v, p, i)
                    kind, th, out = m["kind"], m["thinking"], m["output"]
                    if self.nosent_mode == "planted":
                        if v == "2.1.280":
                            th = 2 * (th + 1) - 1
                            if i in self.P:
                                kind = "wrong"
                        elif (p, i) in ((1, 20), (1, 21), (1, 22), (2, 20), (2, 21), (3, 72)):
                            kind = "none" if (p + i) % 2 == 0 else "bad_form"
                        elif (p, i) == (2, 30):
                            kind = "void"
                    k = NOSENT_VERSIONS.index(v) * 78 + i
                    started = t0 + timedelta(seconds=20 * k) + (timedelta(hours=6) if p == 2 and k >= 78 else timedelta())
                    resent = (p == 1 and (v, i) in (("2.1.280", 3), ("2.1.322", 4)))
                    self._add(f"NS{p}", "nosent", v, p, i, kind, th, out, started, resent=resent)

    # -------------------------------------------------------------- what the tests compare with

    def side(self, group, versions, passes) -> list[dict]:
        return [a for a in self.asks if a["group"] == group and a["version"] in versions and a["pass"] in passes]


def outcome(a) -> str:
    return "void" if a["kind"] == "void" else "scored"


def score(a) -> float | None:
    return None if a["kind"] == "void" else float(a["kind"] == "right")


def is_read(a) -> bool:
    return a["kind"] in ("right", "wrong")


# ------------------------------------------------------------------ graded rows of the registered run

def graded_row(a, *, ask_id, order, plan=None, outcome_=None, reason=None, resend_of=None):
    i = a["i"]
    o = outcome_ or outcome(a)
    ans = answer_for(i, a["kind"]) if o == "scored" else None
    mode = {"main": "stock_blocked", "flags_on": "stock_blocked", "author": "author"}[a["group"]]
    return {"ask_id": ask_id, "plan": plan or a["source"], "group": a["group"], "pass": a["pass"], "block": order // 15,
            "order": order, "version": a["version"], "mode": mode, "effort": "high", "unit": a["unit"],
            "family": FAMILIES[i][0], "repeat": a["pass"], "warmup": False, "scored": True,
            "remote_flags": "on" if a["group"] == "flags_on" else "off", "started_at": iso(a["started"]),
            "elapsed_seconds": 9.0, "resend_of": resend_of, "outcome": o, "reason": reason, "answer": ans,
            "score": score(a) if o == "scored" else None, "thinking_tokens": a["thinking"] if o != "error" else None,
            "output_tokens": a["output"] if o != "error" else None, "num_turns": 1, "tool_rounds": 0, "tool_calls": 0,
            "context_tokens": 120, "first_request_input_tokens": 15000 + 30 * VERSIONS.index(a["version"]) + i}


def formal_rows(world: World) -> dict:
    """{plan: graded rows} of the registered run: F1, F1r, F2, F3."""
    out = {"F1": [], "F1r": [], "F2": [], "F3": []}
    n = {}
    for a in world.asks:
        if not a["source"].startswith("F"):
            continue
        plan = a["source"]
        n[plan] = n.get(plan, 0) + 1
        ask_id = f"p{a['pass']}b{n[plan] // 15:03d}o{n[plan]:05d}"
        if a["resent"]:
            out[plan].append(graded_row(a, ask_id=ask_id, order=n[plan], outcome_="error", reason="launch_error"))
            out[f"{plan}r"].append(graded_row(a, ask_id=f"r{a['pass']}b000o{len(out[plan + 'r']) + 1:05d}", order=1,
                                              plan=f"{plan}r", resend_of={"plan": plan, "ask_id": ask_id}))
        else:
            out[plan].append(graded_row(a, ask_id=ask_id, order=n[plan]))
    return out


def final_report(rows_by_plan: dict) -> dict:
    """The registered analysis of the made-up registered run (few shuffles: only small_groups is compared)."""
    rows = [r for rs in rows_by_plan.values() for r in rs]
    rep, _ = analyze.analyze(rows, versions=VERSIONS, shuffles=50)
    return json.loads(json.dumps(rep, ensure_ascii=False))


# ------------------------------------------------------------------ raw records of the added plans

def raw_record(a, *, plan, ask_id, order, status="done", resend_of=None, num_turns=1):
    i, mode = a["i"], ("author" if a["group"] == "author" else "stock_blocked")
    stdout = ""
    if status == "done":
        ans = answer_for(i, a["kind"]) if a["kind"] != "void" else answer_for(i, "right")
        text = f"Made-up working, {MARK}." + ("" if ans is None else f"\n<answer>{ans}</answer>")
        usage = {"input_tokens": 120, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
                 "output_tokens": a["output"], "output_tokens_details": {"thinking_tokens": a["thinking"]}}
        events = [
            {"type": "system", "subtype": "init", "apiKeySource": "none", "model": MODEL, "tools": [],
             "claude_code_version": a["version"]},
            {"type": "assistant", "parent_tool_use_id": None,
             "message": {"id": f"msg_{plan}_{ask_id}", "model": MODEL, "role": "assistant", "stop_reason": "end_turn",
                         "content": [{"type": "text", "text": text}], "usage": usage}},
            {"type": "result", "subtype": "success", "is_error": False, "num_turns": num_turns, "result": text,
             "stop_reason": "end_turn", "usage": usage, "modelUsage": {MODEL: {"outputTokens": a["output"]}}},
        ]
        stdout = "\n".join(json.dumps(e) for e in events) + "\n"
    return {"format": "ccversions-record-v1", "ask_id": ask_id, "plan": plan, "pass": a["pass"], "block": order // 15,
            "order": order, "version": a["version"], "mode": mode, "effort": "high", "unit": a["unit"],
            "repeat": a["pass"], "warmup": False, "scored": True, "group": a["group"], "label": "", "options": {},
            "resend_of": resend_of, "remote_flags": "on" if a["group"] == "flags_on" else "off",
            "argv": ["claude", "-p", "--output-format", "stream-json", "--model", MODEL, "--effort", "high"],
            "status": status, "returncode": 0 if status == "done" else None, "stdout": stdout, "stderr": "",
            "started_at": iso(a["started"]), "elapsed_seconds": 9.0}


def raw_plans(world: World) -> dict:
    """{plan: records} of S3, NS1 to NS3 and A3, with a resend plan wherever an ask is resent."""
    out, n = {}, {}
    for a in world.asks:
        plan = a["source"]
        if plan.startswith("F"):
            continue
        n[plan] = n.get(plan, 0) + 1
        ask_id = f"p{a['pass']}b{n[plan] // 15:03d}o{n[plan]:05d}"
        recs = out.setdefault(plan, [])
        if a["resent"]:
            recs.append(raw_record(a, plan=plan, ask_id=ask_id, order=n[plan], status="launch_error"))
            rr = out.setdefault(f"{plan}r", [])
            rr.append(raw_record(a, plan=f"{plan}r", ask_id=f"r{a['pass']}b000o{len(rr) + 1:05d}", order=len(rr) + 1,
                                 resend_of={"plan": plan, "ask_id": ask_id}))
        else:
            recs.append(raw_record(a, plan=plan, ask_id=ask_id, order=n[plan], num_turns=2 if a["kind"] == "void" else 1))
    return out


# ------------------------------------------------------------------ LiveNerf's daily numbers

DAILY_COLUMNS = ("series_day", "date_utc", "run_start_utc", "model", "arm", "family", "samples", "scored", "errors",
                 "classifier_events", "score", "output_tokens_median", "cli_version", "harness_hash", "funding_source",
                 "runner")


def daily_values() -> dict:
    """{date: (score, output_tokens_median)} of the made-up measured arm, 20 October to 13 November."""
    out = {}
    d = datetime(2026, 10, 20, tzinfo=UTC)
    for k in range(25):
        day = (d + timedelta(days=k)).date().isoformat()
        if day < "2026-11-03":
            out[day] = (round(0.55 + 0.03 * (k % 6), 4), 900.0 + 25 * (k % 5))
        else:
            out[day] = (round(0.58 + 0.02 * (k % 4), 4), 540.0 + 15 * (k % 6))
    out["2026-11-11"] = (0.7051, 600.0)
    out["2026-11-12"] = (0.5, 610.0)
    out["2026-11-13"] = (0.3, 620.0)
    return out


def write_daily(path: Path, values: dict | None = None) -> None:
    values = values or daily_values()
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=DAILY_COLUMNS)
        w.writeheader()
        for k, (day, (s, med)) in enumerate(sorted(values.items()), 1):
            base = {"series_day": k, "date_utc": day, "run_start_utc": "00:07", "samples": 78, "scored": 78,
                    "errors": 0, "classifier_events": 0, "cli_version": "2.1.280 (Claude Code)",
                    "harness_hash": "0123456789abcdef", "funding_source": "max", "runner": "host"}
            w.writerow({**base, "model": "claudecode/claude-opus-5-5", "arm": "measured", "family": "all", "score": s,
                        "output_tokens_median": med})
            w.writerow({**base, "model": "claudecode/claude-opus-5-5", "arm": "measured", "family": "gpqa",
                        "samples": 12, "scored": 12, "score": 0.99, "output_tokens_median": 9999.0})
            w.writerow({**base, "model": "claudecode/claude-opus-5", "arm": "control", "family": "all", "score": 0.01,
                        "output_tokens_median": 1.0})


# ------------------------------------------------------------------ all of it in one folder

def desktop_prompt_report() -> dict:
    m = {"effect": "diff", "items": 78, "a_passes": [1, 2], "b_passes": [1, 2, 3], "computable": True, "a_mean": 0.61,
         "b_mean": 0.64, "diff": -0.03, "diff_shown": -0.03, "range_95": [-0.08, 0.02], "range_95_shown": [-0.08, 0.02],
         "draws": 10000, "p": 0.2}
    t = {**m, "effect": "ratio", "a_mean": 5.0, "b_mean": 5.1, "diff": -0.1, "diff_shown": -0.0952,
         "range_95": [-0.2, 0.0], "range_95_shown": [-0.1813, 0.0]}
    return {"format": "made-up", "comparisons": [
        {"id": 1, "name": "B minus A", "metrics": {}},
        {"id": 5, "name": "E minus main on 2.1.321", "metrics": {"accuracy": m, "accuracy_bad_as_wrong": m,
                                                                  "log_thinking": t},
         "reminder_check": {"computable": True, "accuracy_both_ways": "otherwise"}}]}


def write_world(world: World, root: Path, *, final: dict | None = None, with_desktop: bool = True) -> dict:
    """Everything the program reads, under root. Returns the paths and the parts written."""
    root = Path(root)
    graded = formal_rows(world)
    for plan, rows in graded.items():
        d = root / "graded" / plan
        d.mkdir(parents=True, exist_ok=True)
        with open(d / "graded.jsonl", "w") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    final = final if final is not None else final_report(graded)
    (root / "final").mkdir(parents=True, exist_ok=True)
    (root / "final" / "report.json").write_text(json.dumps(final, ensure_ascii=False, indent=1) + "\n")
    raw = raw_plans(world)
    places = {"S3": root / "s3raw", "A3": root / "a3raw"}
    for plan, recs in raw.items():
        base = places.get(plan.rstrip("r"), root / "nosentraw")
        d = base / plan / "asks"
        d.mkdir(parents=True, exist_ok=True)
        for r in recs:
            (d / f"{r['ask_id']}.json").write_text(json.dumps(r, ensure_ascii=False))
    write_daily(root / "daily.csv")
    if with_desktop:
        (root / "dsp_report.json").write_text(json.dumps(desktop_prompt_report()))
    return {"graded": graded, "final": final, "raw": raw}


def argv(root: Path, *extra) -> list[str]:
    root = Path(root)
    files = sorted(str(p) for p in (root / "graded").glob("*/graded.jsonl"))
    out = []
    for f in files:
        out += ["--graded", f]
    return out + ["--final-report", str(root / "final" / "report.json"), "--s3-raw-root", str(root / "s3raw"),
                  "--nosent-raw-root", str(root / "nosentraw"), "--a3-raw-root", str(root / "a3raw"),
                  "--desktop-prompt-report", str(root / "dsp_report.json"), "--livenerf-daily", str(root / "daily.csv"),
                  "--out", str(root / "out"), *extra]
