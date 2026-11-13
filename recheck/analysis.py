"""The three tests and the reported numbers of the two groups added on 13 November 2026
(PREREGISTRATION.md, change log, entry "two groups sent after the reports were opened").

    python -B analysis.py --settings <settings .toml> --out <folder>

It grades the asks that are on disk with the LiveNerf author's graders (ccversions.grade, unchanged)
and writes report.json and report.txt. It runs whatever is complete: test 1 when the five passes of
xhigh_recheck are complete, test 2 when stage 1 of high_recheck is, test 3 when stage 2 was sent and is
complete. A part that is cut short is still computed and marked as cut short.

Everything below `main()` works on plain rows, so test_analysis.py can run it on made-up rows.

The unit of each test is the version. For each of the ten versions: each question's mean over that
version's scored asks, then the mean of those over the questions. T is the mean of the later five minus
the mean of the earlier five. p is the share of the 252 splits of the ten values into five and five whose
difference is at least as far from zero as T. Declared when p <= 0.05.

Which asks count: outcome "scored" (section 3 of the registration, as for main). In each pass, a question
counts only where all ten versions have a record of it (a record of any outcome), so a pass that was cut
short takes the same questions from every version. A question for which one of the ten versions then has
no scored ask is left out for all ten and named in the report.
"""

import argparse
import json
import math
import sys
from itertools import combinations
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

EARLIER = ("2.1.311", "2.1.312", "2.1.314", "2.1.315", "2.1.316")
LATER = ("2.1.317", "2.1.318", "2.1.319", "2.1.321", "2.1.322")
TEN = EARLIER + LATER
ELEVENTH = "2.1.323"
SEED = 20261111
DRAWS = 10_000
ALPHA = 0.05
SPLITS = np.array([[i in c for i in range(10)] for c in combinations(range(10), 5)])  # 252 rows


# ---------------------------------------------------------------- values of one ask

def lthink(r: dict) -> float:
    return math.log(float(r["thinking_tokens"]) + 1.0)


def correct(r: dict) -> float:
    return float(r["score"])


# ---------------------------------------------------------------- which asks count

def counted(rows: list[dict], group: str, passes=None, units=None) -> tuple[list[dict], dict]:
    """The scored asks of a group that count, and what was left out.

    A (pass, question) cell counts only when each of the ten versions has a record in it. Resend rows
    carry the pass of the ask they replace, so they sit in the same cell.
    """
    mine = [r for r in rows if r.get("group") == group and (passes is None or r["pass"] in passes)
            and (units is None or r["unit"] in units)]
    have: dict = {}
    for r in mine:
        have.setdefault((r["pass"], r["unit"]), set()).add(r["version"])
    full = {c for c, vs in have.items() if all(v in vs for v in TEN)}
    out = [r for r in mine if (r["pass"], r["unit"]) in full and r.get("outcome") == "scored"]
    outcomes: dict = {}
    for r in mine:
        o = outcomes.setdefault(r["version"], {})
        o[r.get("outcome")] = o.get(r.get("outcome"), 0) + 1
    info = {"records": len(mine), "cells": len(have), "cells_with_all_ten_versions": len(full),
            "scored_asks_that_count": len(out), "records_by_version_and_outcome": outcomes}
    return out, info


def cell_means(asks: list[dict], value) -> dict:
    """{version: {question: mean of value over that version's asks of the question}}"""
    acc: dict = {}
    for r in asks:
        acc.setdefault(r["version"], {}).setdefault(r["unit"], []).append(value(r))
    return {v: {u: sum(x) / len(x) for u, x in d.items()} for v, d in acc.items()}


def common_units(means: dict, versions=TEN) -> tuple[list[str], list[str]]:
    """The questions every one of `versions` has a value for, and the questions left out."""
    every = set().union(*(set(means.get(v, {})) for v in versions)) if versions else set()
    ok = sorted(u for u in every if all(u in means.get(v, {}) for v in versions))
    return ok, sorted(every - set(ok))


# ---------------------------------------------------------------- the test

def split_test(values: dict) -> dict:
    """values: {version: value} for the ten versions. T = mean(later five) - mean(earlier five); p over
    the 252 splits, two-sided, the true split included."""
    x = np.array([values[v] for v in TEN], dtype=float)
    t = x[5:].mean() - x[:5].mean()
    a = (SPLITS * x).sum(1) / 5
    b = (~SPLITS * x).sum(1) / 5
    p = float((np.abs(a - b) >= abs(t) - 1e-12).mean())
    return {"T": float(t), "p": p, "declared": bool(p <= ALPHA), "splits": int(len(SPLITS)),
            "splits_at_least_as_far": int(round(p * len(SPLITS)))}


def question_range(means: dict, units: list[str], draws: int = DRAWS, seed: int = SEED) -> dict:
    """T again as the mean over questions of (later five's mean - earlier five's mean), with the middle
    95% over `draws` redraws of the questions (with replacement)."""
    d = np.array([np.mean([means[v][u] for v in LATER]) - np.mean([means[v][u] for v in EARLIER]) for u in units])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(draws, len(d)))
    stats = d[idx].mean(1)
    return {"T": float(d.mean()), "low": float(np.percentile(stats, 2.5)), "high": float(np.percentile(stats, 97.5)),
            "questions": len(d)}


def ask_shuffle_p(asks: list[dict], value, units: list[str], draws: int = DRAWS, seed: int = SEED) -> dict:
    """The registered kind of shuffle, for comparison only: in each (question, pass) cell the values of
    the ten versions (missing ones included) are dealt to the ten versions at random. Two-sided p of T.
    It treats the spread between versions as noise between asks (point 4 of the entry)."""
    ui = {u: i for i, u in enumerate(units)}
    vi = {v: i for i, v in enumerate(TEN)}
    passes = sorted({r["pass"] for r in asks})
    pi = {p: i for i, p in enumerate(passes)}
    arr = np.full((len(units), len(passes), 10), np.nan)
    for r in asks:
        if r["unit"] in ui and r["version"] in vi:
            arr[ui[r["unit"]], pi[r["pass"]], vi[r["version"]]] = value(r)

    def stat(a):  # a: (..., questions, passes, 10)
        with np.errstate(invalid="ignore"):
            per = np.nanmean(a, axis=-2)  # (..., questions, 10): each version's mean over its asks of the question
        v = np.nanmean(per, axis=-2)      # (..., 10): mean over questions
        return v[..., 5:].mean(-1) - v[..., :5].mean(-1)

    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        t = float(stat(arr))
        rng = np.random.default_rng(seed)
        hits, done = 0, 0
        while done < draws:
            n = min(500, draws - done)
            order = np.argsort(rng.random((n,) + arr.shape), axis=-1)
            s = stat(np.take_along_axis(np.broadcast_to(arr, (n,) + arr.shape), order, axis=-1))
            hits += int((np.abs(s) >= abs(t) - 1e-12).sum())
            done += n
    return {"T": t, "p": (hits + 1) / (draws + 1), "draws": draws}


def one_comparison(asks: list[dict], value, kind: str, is_test: bool = False) -> dict:
    """kind: "thinking" (value is ln(tokens + 1); reported as a per cent) or "accuracy" (0/1; points).
    Only one of the three tests carries a declaration (is_test); every other comparison gives its T,
    range and p with "declared": None."""
    means = cell_means(asks, value)
    units, left_out = common_units(means)
    if not units:
        return {"no_data": True, "questions_left_out": left_out}
    values = {v: float(np.mean([means[v][u] for u in units])) for v in TEN}
    test = split_test(values)
    if not is_test:
        test["declared"] = None
    rng = question_range(means, units)
    if kind == "thinking":
        shown = {"change_in_geometric_mean_per_cent": (math.exp(test["T"]) - 1) * 100,
                 "range_per_cent": [(math.exp(rng["low"]) - 1) * 100, (math.exp(rng["high"]) - 1) * 100]}
    else:
        shown = {"difference_points": test["T"] * 100, "range_points": [rng["low"] * 100, rng["high"] * 100]}
    return {"kind": kind, "questions": len(units), "questions_left_out": left_out,
            "version_values": values, **test, **shown,
            "direction": "later five lower" if test["T"] < 0 else "later five higher" if test["T"] > 0 else "equal",
            "ask_shuffle_for_comparison_only": ask_shuffle_p(asks, value, units)}


# ---------------------------------------------------------------- per-version rows and per-question differences

def version_rows(asks: list[dict], info: dict, versions=TEN + (ELEVENTH,), units=None) -> dict:
    """One row per version over the questions all of TEN have (2.1.323 over the same questions it has)."""
    lt = cell_means(asks, lthink)
    units = units if units is not None else common_units(lt)[0]
    uset = set(units)
    out = {}
    for v in versions:
        mine = [r for r in asks if r["version"] == v and r["unit"] in uset]
        if not mine:
            out[v] = {"scored_asks": 0}
            continue
        per_q = lambda f, rows_: cell_means(rows_, f).get(v, {})  # noqa: E731
        a_lt, a_ok = per_q(lthink, mine), per_q(correct, mine)
        a_zero = per_q(lambda r: float(r["thinking_tokens"] == 0), mine)
        a_tool = per_q(lambda r: float(bool(r.get("tool_calls"))), mine)
        pos = [r for r in mine if r["thinking_tokens"] > 0]
        a_pos = per_q(lthink, pos)
        mean = lambda d: float(np.mean(list(d.values()))) if d else None  # noqa: E731
        out[v] = {"scored_asks": len(mine), "questions": len(a_lt),
                  "thinking_geometric_mean_tokens": math.exp(mean(a_lt)) - 1,
                  "mean_ln_thinking": mean(a_lt),
                  "share_zero_thinking_per_cent": mean(a_zero) * 100,
                  "thinking_geometric_mean_over_asks_above_zero": (math.exp(mean(a_pos)) - 1) if a_pos else None,
                  "questions_with_an_ask_above_zero": len(a_pos),
                  "accuracy_per_cent": mean(a_ok) * 100,
                  "share_that_tried_a_tool_per_cent": mean(a_tool) * 100,
                  "records_by_outcome": info["records_by_version_and_outcome"].get(v, {})}
    return out


def eleventh(rows_by_version: dict) -> dict:
    """2.1.323 beside the two sets of five: its figures, the two means, and its rank among the eleven."""
    if not all(rows_by_version.get(v, {}).get("scored_asks") for v in TEN + (ELEVENTH,)):
        return {"no_data": True}
    out = {}
    for key in ("mean_ln_thinking", "accuracy_per_cent", "share_zero_thinking_per_cent"):
        x = rows_by_version[ELEVENTH][key]
        e = float(np.mean([rows_by_version[v][key] for v in EARLIER]))
        l = float(np.mean([rows_by_version[v][key] for v in LATER]))
        allv = sorted(rows_by_version[v][key] for v in TEN + (ELEVENTH,))
        out[key] = {"2.1.323": x, "earlier_five_mean": e, "later_five_mean": l,
                    "rank_among_eleven_from_lowest": allv.index(x) + 1,
                    "nearer_to": "later five" if abs(x - l) < abs(x - e) else "earlier five"}
    return out


def question_differences(asks: list[dict]) -> dict:
    lt, ok = cell_means(asks, lthink), cell_means(asks, correct)
    units, _ = common_units(lt)
    diff = lambda m, u: float(np.mean([m[v][u] for v in LATER]) - np.mean([m[v][u] for v in EARLIER]))  # noqa: E731
    return {u: {"thinking_ln_difference": diff(lt, u), "accuracy_difference_points": diff(ok, u) * 100} for u in units}


# ---------------------------------------------------------------- the two groups

def xhigh_report(rows: list[dict], kinds: dict, expected_passes=(1, 2, 3, 4, 5), expected_units: int = 78) -> dict:
    asks, info = counted(rows, "xhigh_recheck")
    complete = info["cells_with_all_ten_versions"] == len(expected_passes) * expected_units
    rep = {"group": "xhigh_recheck", "counted": info, "complete": complete,
           "test_1_thinking_at_xhigh": one_comparison(asks, lthink, "thinking", is_test=True),
           "accuracy_all_questions_no_declaration": one_comparison(asks, correct, "accuracy")}
    for name, units in kinds.items():
        sub = [r for r in asks if r["unit"] in units]
        rep[f"on_{name}_no_declaration"] = {"thinking": one_comparison(sub, lthink, "thinking"),
                                            "accuracy": one_comparison(sub, correct, "accuracy")}
    rep["versions"] = version_rows(asks, info)
    rep["version_2_1_323"] = eleventh(rep["versions"])
    return rep


def high_report(rows: list[dict], stage1=tuple(range(1, 13)), stage2=tuple(range(13, 25)), expected_units: int = 24) -> dict:
    a1, i1 = counted(rows, "high_recheck", passes=set(stage1))
    rep = {"group": "high_recheck",
           "stage_1": {"counted": i1, "complete": i1["cells_with_all_ten_versions"] == len(stage1) * expected_units,
                       "test_2_thinking_at_high_stage_1": one_comparison(a1, lthink, "thinking", is_test=True),
                       "D1_accuracy_stage_1": one_comparison(a1, correct, "accuracy"),
                       "versions": version_rows(a1, i1), "question_differences": question_differences(a1)}}
    rep["stage_1"]["version_2_1_323"] = eleventh(rep["stage_1"]["versions"])
    a2, i2 = counted(rows, "high_recheck", passes=set(stage2))
    if not i2["records"]:
        rep["stage_2_sent"] = False
        return rep
    both, ib = counted(rows, "high_recheck", passes=set(stage1) | set(stage2))
    rep["stage_2_sent"] = True
    rep["both_stages"] = {"counted": ib,
                          "complete": ib["cells_with_all_ten_versions"] == (len(stage1) + len(stage2)) * expected_units,
                          "test_3_accuracy_at_high_both_stages": one_comparison(both, correct, "accuracy", is_test=True),
                          "thinking_both_stages_no_declaration": one_comparison(both, lthink, "thinking"),
                          "versions": version_rows(both, ib), "question_differences": question_differences(both)}
    rep["both_stages"]["version_2_1_323"] = eleventh(rep["both_stages"]["versions"])
    rep["stage_2_alone_no_declaration"] = {"counted": i2, "accuracy": one_comparison(a2, correct, "accuracy"),
                                           "thinking": one_comparison(a2, lthink, "thinking")}
    return rep


def main_beside(main_rows: list[dict], units: set) -> dict:
    """The registered run's own figures (group main, effort high, three passes) for the same versions on
    the same questions. For the reader to hold beside the new ones. No test."""
    asks = [r for r in main_rows if r.get("group") == "main" and r.get("outcome") == "scored"
            and r["unit"] in units and r["version"] in TEN]
    info = {"records_by_version_and_outcome": {}}
    return {"versions": version_rows(asks, info, versions=TEN),
            "thinking": one_comparison(asks, lthink, "thinking"), "accuracy": one_comparison(asks, correct, "accuracy")}


# ---------------------------------------------------------------- output

def _fmt_cmp(name: str, c: dict) -> list[str]:
    if c.get("no_data"):
        return [f"{name}: no data"]
    if c["kind"] == "thinking":
        size = f"{c['change_in_geometric_mean_per_cent']:+.1f}% ({c['range_per_cent'][0]:+.1f}% to {c['range_per_cent'][1]:+.1f}%)"
    else:
        size = f"{c['difference_points']:+.2f} points ({c['range_points'][0]:+.2f} to {c['range_points'][1]:+.2f})"
    return [f"{name}: {size}; p = {c['p']:.4f} ({c['splits_at_least_as_far']} of {c['splits']} splits); "
            f"{'no declaration' if c['declared'] is None else 'DECLARED' if c['declared'] else 'not declared'}; {c['direction']}; questions {c['questions']}"
            + (f", left out {len(c['questions_left_out'])}" if c["questions_left_out"] else "")
            + f"; shuffle of asks, for comparison only: p = {c['ask_shuffle_for_comparison_only']['p']:.4f}"]


def _fmt_versions(rows: dict) -> list[str]:
    left = {v: {k: n for k, n in (r.get("records_by_outcome") or {}).items() if k != "scored"} for v, r in rows.items()}
    out = ["  records that are not scored, by version: " + json.dumps({v: x for v, x in left.items() if x})]
    out += ["  version   asks  thinking(geo mean)  zero%   geo mean above zero  accuracy%  tried a tool%"]
    for v, r in rows.items():
        if not r.get("scored_asks"):
            out.append(f"  {v}   no scored ask")
            continue
        above = r["thinking_geometric_mean_over_asks_above_zero"]
        out.append(f"  {v}  {r['scored_asks']:5d}  {r['thinking_geometric_mean_tokens']:10.1f}  {r['share_zero_thinking_per_cent']:13.1f}"
                   f"  {above if above is None else round(above, 1)!s:>12}  {r['accuracy_per_cent']:15.1f}  {r['share_that_tried_a_tool_per_cent']:9.1f}")
    return out


def text_report(rep: dict) -> str:
    L = ["Two groups sent after the reports were opened (decided after the registered results were seen).", ""]
    x = rep.get("xhigh_recheck")
    if x:
        L += [f"== xhigh_recheck: complete = {x['complete']}, scored asks that count = {x['counted']['scored_asks_that_count']} =="]
        L += _fmt_cmp("TEST 1, thinking at xhigh, 78 questions", x["test_1_thinking_at_xhigh"])
        L += _fmt_cmp("accuracy at xhigh, all questions (no declaration)", x["accuracy_all_questions_no_declaration"])
        for k in [k for k in x if k.startswith("on_")]:
            L += _fmt_cmp(f"{k}: thinking", x[k]["thinking"]) + _fmt_cmp(f"{k}: accuracy", x[k]["accuracy"])
        L += _fmt_versions(x["versions"]) + ["  2.1.323: " + json.dumps(x["version_2_1_323"])] + [""]
    h = rep.get("high_recheck")
    if h:
        s1 = h["stage_1"]
        L += [f"== high_recheck, stage 1: complete = {s1['complete']}, scored asks that count = {s1['counted']['scored_asks_that_count']} =="]
        L += _fmt_cmp("TEST 2, thinking at high on the 24 questions, stage 1", s1["test_2_thinking_at_high_stage_1"])
        L += _fmt_cmp("D1, accuracy on stage 1 (decides stage 2; no declaration)", s1["D1_accuracy_stage_1"])
        L += _fmt_versions(s1["versions"]) + ["  2.1.323: " + json.dumps(s1["version_2_1_323"])] + [""]
        if h["stage_2_sent"]:
            b = h["both_stages"]
            L += [f"== high_recheck, both stages: complete = {b['complete']}, scored asks that count = {b['counted']['scored_asks_that_count']} =="]
            L += _fmt_cmp("TEST 3, accuracy at high on the 24 questions, both stages", b["test_3_accuracy_at_high_both_stages"])
            L += _fmt_cmp("thinking on both stages (no declaration)", b["thinking_both_stages_no_declaration"])
            L += _fmt_versions(b["versions"]) + ["  2.1.323: " + json.dumps(b["version_2_1_323"])] + [""]
        else:
            L += ["stage 2 was not sent: test 3 is not run.", ""]
    for k in ("main_on_the_78", "main_on_the_24"):
        if rep.get(k):
            L += [f"== {k}: the registered run's own asks of the same versions (effort high), beside the new figures =="]
            L += _fmt_cmp("thinking", rep[k]["thinking"]) + _fmt_cmp("accuracy", rep[k]["accuracy"])
            L += _fmt_versions(rep[k]["versions"]) + [""]
    return "\n".join(L) + "\n"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main(argv=None) -> int:
    from ccversions import formal, settings as settings_mod

    ap = argparse.ArgumentParser()
    ap.add_argument("--settings", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--main-graded", action="append", default=[],
                    help="a graded.jsonl of the registered run, for the figures beside; give it once per pass")
    a = ap.parse_args(argv)
    s = settings_mod.load(a.settings)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    more = json.loads((HERE / "items_think_more_24.json").read_text())["items"]
    less = json.loads((HERE / "items_think_less_19.json").read_text())["items"]
    rep: dict = {"what": "two groups sent after the reports were opened"}

    dx = formal.Driver(s, HERE / "run_x.json")
    xrows = []
    for f in dx.graded([f"X{n}{suffix}" for n in range(1, 6) for suffix in ("", "r")]):
        xrows += load_jsonl(f)
    if xrows:
        all_units = {r["unit"] for r in xrows}
        kinds = {"the_24_first_kind": {"item:" + i for i in more}, "the_19_second_kind": {"item:" + i for i in less}}
        kinds["the_other_35"] = all_units - kinds["the_24_first_kind"] - kinds["the_19_second_kind"]
        rep["xhigh_recheck"] = xhigh_report(xrows, kinds)

    dh = formal.Driver(s, HERE / "run_h.json")
    hrows = []
    for f in dh.graded([f"H{n}{suffix}" for n in range(1, 25) for suffix in ("", "r")]):
        hrows += load_jsonl(f)
    if hrows:
        rep["high_recheck"] = high_report(hrows)

    if a.main_graded:
        mrows = []
        for f in a.main_graded:
            mrows += load_jsonl(Path(f))
        rep["main_on_the_78"] = main_beside(mrows, {r["unit"] for r in mrows})
        rep["main_on_the_24"] = main_beside(mrows, {"item:" + i for i in more})

    (out / "report.json").write_text(json.dumps(rep, indent=1) + "\n")
    (out / "report.txt").write_text(text_report(rep))
    print(text_report(rep), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
