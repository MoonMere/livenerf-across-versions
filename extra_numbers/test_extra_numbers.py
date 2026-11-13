"""Self-tests of extra_numbers.py, on made-up data only (fake_data.py). Nothing here reads the registered run,
and no model is asked. The registered program's own reports for the made-up data are made with
analyze.analyze, so the declared differences the tests rely on come from the registered code.

    CCV_AUTHOR_REPO=<LiveNerf repository> python -B -m unittest test_extra_numbers

Every item has at least one number that is counted here again by plain Python loops over the rows (or over
what fake_data.py says it put in), without the arrays and functions of extra_numbers.py, and compared.
"""

import json
import math
import os
import statistics
import tempfile
import unittest
from pathlib import Path

import numpy as np

import extra_numbers as xn
import fake_data as fd

AUTHOR_REPO = os.environ.get("CCV_AUTHOR_REPO")
if not AUTHOR_REPO:
    raise unittest.SkipTest("set CCV_AUTHOR_REPO to LiveNerf's repository: item 2 needs its rational() parser")
RATIONAL = xn.author_parsers(Path(AUTHOR_REPO))
IS_READ = xn.make_is_read(RATIONAL)

R = range
VI = {v: k for k, v in enumerate(fd.VERSIONS)}
UNITS_SORTED = sorted(fd.UNITS)
REPORT_SHUFFLES = 500
KW = dict(draws=2000, placement_draws=400, scan_shuffles=2000)

SCENARIOS = {
    "null": dict(seed=1, missing={(1, 5, 7), (2, 30, 40), (3, 0, 0)}),
    "accuracy_drop": dict(seed=2, acc_shift={k: -10 for k in R(22, 39)}),
    "thinking_drop_with_zeros": dict(seed=3, think_mult={k: 0.55 for k in R(30, 39)},
                                     zero_by_version={k: 0.2 for k in R(30, 39)}),
    "two_ways_differ_same_sign": dict(seed=4, acc_shift={k: -8 for k in R(21, 39)},
                                      error_by_version={k: 0.3 for k in R(5, 10)}),
    "two_ways_opposite_signs": dict(seed=5, acc_shift={k: -6 for k in R(21, 39)},
                                    error_by_version={k: 0.25 for k in R(0, 21)}),
    "unreadable_answers": dict(seed=16, unread_by_version={k: 0.45 for k in R(25, 39)}),
    "tool_attempts": dict(seed=7, tool_by_version={k: 0.6 for k in R(15, 39)}, tool_acc_shift=-30),
    "high_in_the_middle": dict(seed=8, acc_shift={k: 15 for k in R(10, 16)}),
    "not_confirmed": dict(seed=9, pass_acc_shift={1: {k: -10 for k in R(22, 39)}, 2: {k: -10 for k in R(22, 39)},
                                                  3: {k: 8 for k in R(22, 39)}}),
    "only_p_on_two_passes": dict(seed=10, pass_acc_shift={1: {k: -20 for k in R(22, 39)}, 2: {k: 4 for k in R(22, 39)},
                                                          3: {k: -20 for k in R(22, 39)}}),
    "cut_at_2_1_303": dict(seed=12, acc_shift={k: -2.5 for k in R(21, 39)}, think_mult={k: 0.96 for k in R(21, 39)}),
}
RAW = {"null": dict(last_only={"2.1.300"}, off_by={"2.1.301"})}
_CACHE: dict = {}


def scenario(name: str) -> dict:
    """rows, truth, the registered reports, the context and the computed numbers of one scenario (cached)."""
    if name not in _CACHE:
        rows, truth = fd.make_rows(**SCENARIOS[name])
        final, interim = fd.reports(rows, shuffles=REPORT_SHUFFLES)
        ctx = fd.context(rows, final, interim, IS_READ, **KW)
        raw = None
        if name in RAW:
            tmp = tempfile.mkdtemp()
            raw = xn.read_raw(fd.write_raw(fd.make_raw(rows, **RAW[name]), Path(tmp)))
        _CACHE[name] = {"rows": rows, "truth": truth, "final": final, "interim": interim, "ctx": ctx,
                        "checks": xn.check_reports(ctx), "rep": xn.compute(ctx, raw)}
    return _CACHE[name]


# ------------------------------------------------------------------------------ the plain Python counts

def scored(r):
    return r["outcome"] == "scored"


def tried(r):
    return (r.get("tool_calls") or 0) > 0


VALUE = {
    "accuracy": lambda r: r["score"] if scored(r) else None,
    "accuracy_bad_as_wrong": lambda r: r["score"] if scored(r) else (0.0 if r["outcome"] in ("error", "void") else None),
    "log_thinking": lambda r: math.log(r["thinking_tokens"] + 1) if scored(r) else None,
    "tried": lambda r: (1.0 if tried(r) else 0.0) if scored(r) else None,
    "accuracy_not_tried": lambda r: r["score"] if scored(r) and not tried(r) else None,
    "log_thinking_not_tried": lambda r: math.log(r["thinking_tokens"] + 1) if scored(r) and not tried(r) else None,
}


def cells(rows, value) -> dict:
    """{(unit, pass): {version index: value}} over the cells where every version of group main has a record."""
    by: dict = {}
    for r in rows:
        if r["group"] == "main":
            by.setdefault((r["unit"], r["pass"]), {})[VI[r["version"]]] = r
    out = {}
    for cell, recs in by.items():
        if len(recs) == len(fd.VERSIONS):
            vals = {k: value(r) for k, r in recs.items()}
            out[cell] = {k: v for k, v in vals.items() if v is not None}
    return out


def residual_lists(cs, a, b, passes=None, units=None):
    ins, outs = [], []
    for (u, p), vals in cs.items():
        if (passes and p not in passes) or (units is not None and u not in units) or not vals:
            continue
        m = sum(vals.values()) / len(vals)
        for k, v in vals.items():
            (ins if a <= k <= b else outs).append(v - m)
    return ins, outs


def py_diff(cs, a, b, **kw):
    ins, outs = residual_lists(cs, a, b, **kw)
    return sum(ins) / len(ins) - sum(outs) / len(outs)


def py_part(cs, lo, hi):
    """Mean residual of versions lo..hi - 1 (all passes)."""
    vals = []
    for (u, p), cell in cs.items():
        if cell:
            m = sum(cell.values()) / len(cell)
            vals += [v - m for k, v in cell.items() if lo <= k < hi]
    return sum(vals) / len(vals) if vals else None


def raw_side(rows, a, b, value):
    """Raw values of the counted cells inside and outside a..b."""
    cs = cells(rows, value)
    ins = [v for c in cs.values() for k, v in c.items() if a <= k <= b]
    outs = [v for c in cs.values() for k, v in c.items() if not a <= k <= b]
    return ins, outs


class Base(unittest.TestCase):
    def assertNear(self, a, b, places=10):
        self.assertIsNotNone(a)
        self.assertIsNotNone(b)
        self.assertAlmostEqual(float(a), float(b), places=places)


# ------------------------------------------------------------------------------ the made-up data itself

class FakeData(Base):
    def test_scores_follow_the_author_graders(self):
        """A made-up answer scores 1 exactly when LiveNerf's own grader gives it 1 against the made-up key, and
        the answers fake_data.py made unreadable are the ones is_read() calls unreadable."""
        import sys
        sys.path.insert(0, AUTHOR_REPO)
        from livenerf.scorers import checks
        fn = {"choice": checks.choice_score, "integer": checks.integer_score, "rational": checks.rational_score}
        s = scenario("unreadable_answers")
        idx = {u: i for i, u in enumerate(fd.UNITS)}
        n = 0
        for r in s["rows"]:
            if r["group"] != "main" or not scored(r):
                continue
            i = idx[r["unit"]]
            self.assertEqual(r["score"], fn[fd.SCORER[fd.FAMILIES[i]]](r["answer"], fd.key_of(i)))
            self.assertEqual(IS_READ(r["answer"], fd.SCORER[fd.FAMILIES[i]]),
                             s["truth"][(r["pass"], r["version"], r["unit"])]["readable"])
            n += 1
        self.assertGreater(n, 8000)

    def test_is_read_by_hand(self):
        cases = [("B", "choice", True), (" (c) ", "choice", True), ("( D )", "choice", True), ("AB", "choice", False),
                 ("B or C", "choice", False), ("", "choice", False), (None, "choice", False),
                 ("1,234", "integer", True), (" -12 ", "integer", True), ("12.5", "integer", False),
                 ("x = 5", "integer", False), ("3/4", "rational", True), ("\\frac{1}{2}", "rational", True),
                 ("$-7$", "rational", True), ("0.75", "rational", False), ("3/0", "rational", False)]
        for answer, scorer, want in cases:
            self.assertEqual(IS_READ(answer, scorer), want, (answer, scorer))


# ------------------------------------------------------------------------------ registered reports

class AgainstTheRegisteredReports(Base):
    def test_every_scenario_matches_its_reports(self):
        for name in SCENARIOS:
            c = scenario(name)["checks"]
            self.assertTrue(c["ok"], (name, c["problems"]))
            self.assertEqual(len(c["compared"]), 7, name)

    def test_a_changed_report_is_caught(self):
        s = scenario("accuracy_drop")
        final = json.loads(json.dumps(s["final"]))
        final["accuracy"]["best_start"] += 1
        ctx = fd.context(s["rows"], final, s["interim"], IS_READ, **KW)
        c = xn.check_reports(ctx)
        self.assertFalse(c["ok"])
        self.assertTrue(any("best_start" in p for p in c["problems"]))

    def test_declared_states_of_the_scenarios(self):
        want = {"null": (False, False), "accuracy_drop": (True, False), "thinking_drop_with_zeros": (False, True),
                "two_ways_differ_same_sign": (True, False), "two_ways_opposite_signs": (False, False),
                "unreadable_answers": (True, False), "tool_attempts": (True, False),
                "high_in_the_middle": (True, False), "not_confirmed": (False, False),
                "only_p_on_two_passes": (False, False), "cut_at_2_1_303": (False, False)}
        for name, (acc, th) in want.items():
            f = scenario(name)["final"]
            self.assertEqual((f["accuracy_difference_declared"], f["thinking_difference_declared"]), (acc, th), name)


# ------------------------------------------------------------------------------ items

class Item1BlockedTools(Base):
    def test_holds_when_the_drop_sits_in_asks_that_tried_a_tool(self):
        s = scenario("tool_attempts")
        e = s["rep"]["items"]["1"]["for_each_declared_difference"][0]
        a, b = e["start"], e["end"]
        self.assertEqual(e["segment"], "2.1.295 to 2.1.322")
        ins, outs = raw_side(s["rows"], a, b, VALUE["tried"])
        self.assertNear(e["a_tried_a_tool"]["share_inside"], sum(ins) / len(ins))
        self.assertNear(e["a_tried_a_tool"]["share_outside"], sum(outs) / len(outs))
        self.assertEqual(e["a_tried_a_tool"]["asks_inside"], len(ins))
        self.assertNear(e["a_tried_a_tool"]["difference"], py_diff(cells(s["rows"], VALUE["tried"]), a, b))
        self.assertNear(e["b_asks_that_did_not_try_a_tool"]["difference"],
                        py_diff(cells(s["rows"], VALUE["accuracy_not_tried"]), a, b))
        self.assertNear(e["b_asks_that_did_not_try_a_tool"]["declared_difference_same_asks_as_the_scan"],
                        s["final"]["accuracy"]["diff"])
        self.assertTrue(e["a_tried_a_tool"]["range_leaves_out_zero"])
        self.assertEqual(e["case"], "may come from the blocked tools")
        self.assertEqual(e["sentence_to_add"], xn.SENTENCES["item_1"])

    def test_does_not_hold_for_a_plain_drop(self):
        s = scenario("accuracy_drop")
        e = s["rep"]["items"]["1"]["for_each_declared_difference"][0]
        self.assertEqual(e["case"], "does not hold")
        self.assertIsNone(e["sentence_to_add"])
        self.assertGreater(e["b_asks_that_did_not_try_a_tool"]["share_of_the_declared_difference"], 0.5)

    def test_thinking_difference_uses_log_thinking(self):
        s = scenario("thinking_drop_with_zeros")
        e = s["rep"]["items"]["1"]["for_each_declared_difference"][0]
        self.assertEqual(e["test"], "thinking")
        self.assertNear(e["b_asks_that_did_not_try_a_tool"]["difference"],
                        py_diff(cells(s["rows"], VALUE["log_thinking_not_tried"]), e["start"], e["end"]))

    def test_nothing_declared(self):
        self.assertTrue(scenario("null")["rep"]["items"]["1"]["nothing_declared"])


class Item2UnreadAnswers(Base):
    def test_format_changed(self):
        s = scenario("unreadable_answers")
        it = s["rep"]["items"]["2"]
        e = it["for_each_declared_accuracy_difference"][0]
        self.assertEqual(e["segment"], "2.1.307 to 2.1.322")
        self.assertEqual(e["case"], "the format of the answers changed")
        self.assertEqual(e["sentence"], xn.SENTENCES["item_2"])
        truth = s["truth"]
        read_only = cells(s["rows"], lambda r: r["score"] if scored(r) and truth[(r["pass"], r["version"], r["unit"])]
                          ["readable"] else None)
        self.assertNear(e["difference_over_read_answers"], py_diff(read_only, e["start"], e["end"]))
        self.assertLess(e["share_left"], 0.5)
        self.assertEqual(it["scan_of_the_share_not_read"]["segment"], "2.1.307 to 2.1.322")

    def test_per_version_shares_count_back(self):
        for name in ("unreadable_answers", "null"):
            s = scenario(name)
            truth = s["truth"]
            cs = cells(s["rows"], lambda r: (0.0 if truth[(r["pass"], r["version"], r["unit"])]["readable"] else 1.0)
                       if scored(r) else None)
            for k, e in enumerate(s["rep"]["items"]["2"]["per_version"]):
                vals = [c[k] for c in cs.values() if k in c]
                self.assertEqual(e["scored_asks"], len(vals), (name, e["version"]))
                self.assertEqual(e["not_read"], int(sum(vals)), (name, e["version"]))

    def test_plain_drop_is_not_a_format_change(self):
        e = scenario("accuracy_drop")["rep"]["items"]["2"]["for_each_declared_accuracy_difference"][0]
        self.assertEqual(e["case"], "does not hold")


class Item3ZeroThinking(Base):
    def test_numbers_count_back(self):
        s = scenario("thinking_drop_with_zeros")
        e = s["rep"]["items"]["3"]["for_each_declared_thinking_difference"][0]
        a, b = e["start"], e["end"]
        self.assertEqual(e["segment"], "2.1.312 to 2.1.322")
        ins, outs = raw_side(s["rows"], a, b, lambda r: r["thinking_tokens"] if scored(r) else None)
        self.assertEqual(e["asks_inside"], len(ins))
        self.assertNear(e["share_zero_inside"], sum(1 for x in ins if x == 0) / len(ins))
        self.assertNear(e["share_zero_outside"], sum(1 for x in outs if x == 0) / len(outs))
        self.assertNear(e["ratio_of_medians"], statistics.median(ins) / statistics.median(outs))
        self.assertNear(e["ratio_of_totals_per_ask"], (sum(ins) / len(ins)) / (sum(outs) / len(outs)))
        self.assertNear(e["total_inside"], sum(ins))
        pos = cells(s["rows"], lambda r: math.log(r["thinking_tokens"] + 1) if scored(r) and r["thinking_tokens"] > 0
                    else None)
        self.assertNear(e["ratio_over_asks_above_zero"], math.exp(py_diff(pos, a, b)))
        self.assertGreater(e["share_zero_inside"], 0.15)
        self.assertLess(e["share_zero_outside"], 0.05)
        self.assertIn("geometric mean of thinking tokens plus one", e["sentence"])
        self.assertIn(f"{abs(100 * (math.exp(s['final']['thinking']['diff']) - 1)):.1f}% lower", e["sentence"])


class Item4PassThreeAlone(Base):
    def test_pass_three_alone_counts_back(self):
        for name in ("null", "accuracy_drop"):
            s = scenario(name)
            for key, metric in (("accuracy", "accuracy"), ("accuracy_errors_and_voids_as_wrong", "accuracy_bad_as_wrong"),
                                ("thinking", "log_thinking")):
                e = s["rep"]["items"]["4"]["scans"][key]
                ir = s["interim"][key]
                self.assertEqual((e["start"], e["end"]), (ir["best_start"], ir["best_end"]))
                self.assertNear(e["difference"], py_diff(cells(s["rows"], VALUE[metric]), e["start"], e["end"],
                                                         passes={3}))
                lo, hi = e["range_95_shown"]
                self.assertLessEqual(lo, xn.shown(e["difference"], xn.RUNS[key]["effect"]) + 1e-9)
                self.assertGreaterEqual(hi, xn.shown(e["difference"], xn.RUNS[key]["effect"]) - 1e-9)


class Item5ItemsAndFamilies(Base):
    def test_leave_one_out_and_families(self):
        for name, metric in (("accuracy_drop", "accuracy"), ("thinking_drop_with_zeros", "log_thinking")):
            s = scenario(name)
            e = s["rep"]["items"]["5"]["for_each_declared_difference"][0]
            a, b = e["start"], e["end"]
            cs = cells(s["rows"], VALUE[metric])
            self.assertNear(e["difference"], py_diff(cs, a, b))
            loo = {x["item"]: x["difference"] for x in e["each_item_left_out"]}
            for u in (UNITS_SORTED[0], UNITS_SORTED[40], UNITS_SORTED[77]):
                self.assertNear(loo[u], py_diff(cs, a, b, units=set(UNITS_SORTED) - {u}))
            self.assertNear(e["smallest_with_one_item_left_out"]["difference"], min(loo.values()))
            self.assertNear(e["largest_with_one_item_left_out"]["difference"], max(loo.values()))
            for fam, f in e["by_family"].items():
                us = {u for i, u in enumerate(fd.UNITS) if fd.FAMILIES[i] == fam}
                self.assertEqual(f["items"], len(us))
                self.assertNear(f["difference"], py_diff(cs, a, b, units=us))

    def test_one_item_that_carries_the_difference_is_named(self):
        """Only one item differs between versions: leaving it out removes the whole difference."""
        rows, _ = fd.make_rows(seed=31, with_small=False)
        for r in rows:  # item 0 is right in versions 0..19 and wrong from version 20 on; every other item is
            if r["outcome"] != "scored":  # the same in every version, so it has no residual at all
                continue
            i = fd.UNITS.index(r["unit"])
            r["score"] = (1.0 if VI[r["version"]] < 20 else 0.0) if i == 0 else float(i % 2)
        ctx = fd.context(rows, {"versions": list(fd.VERSIONS)}, None, IS_READ, draws=200, placement_draws=50,
                         scan_shuffles=200)
        d = {"test": "accuracy", "start": 20, "end": 38, "named_by": ["accuracy"], "segment": "x", "diff": -0.1,
             "effect": "diff"}
        e = xn.item_5_items_and_families(ctx, [d])["for_each_declared_difference"][0]
        named = [x["item"] for x in e["items_whose_removal_halves_it"]]
        self.assertIn(fd.UNITS[0], named)


class Item6WhereItStartsAndEnds(Base):
    def test_redraws_against_a_brute_force_scan(self):
        s = scenario("thinking_drop_with_zeros")
        val = s["ctx"].array("log_thinking")
        got = xn.placement(val, draws=4)
        cs = cells(s["rows"], VALUE["log_thinking"])
        # per item and version: sum and number of residuals, all passes
        sums = {u: [0.0] * 39 for u in UNITS_SORTED}
        ns = {u: [0] * 39 for u in UNITS_SORTED}
        for (u, p), cell in cs.items():
            m = sum(cell.values()) / len(cell)
            for k, v in cell.items():
                sums[u][k] += v - m
                ns[u][k] += 1
        pick = np.random.default_rng(xn.SEED).integers(0, 78, size=(4, 78))
        for d in range(4):
            S, N = [0.0] * 39, [0] * 39
            for j in pick[d]:
                u = UNITS_SORTED[j]
                for k in range(39):
                    S[k] += sums[u][k]
                    N[k] += ns[u][k]
            best, best_z = None, -1.0
            for a in range(39):
                for b in range(a, 39):
                    if a == 0 and b == 38:
                        continue
                    nin, sin = sum(N[a:b + 1]), sum(S[a:b + 1])
                    nout, sout = sum(N) - nin, sum(S) - sin
                    z = abs((sin / nin - sout / nout) * math.sqrt(nin * nout / (nin + nout)))
                    if z > best_z + 1e-12:
                        best, best_z = (a, b), z
            if best[0] == 0:
                best = (best[1] + 1, 38)
            self.assertEqual((int(got["first"][d]), int(got["last"][d])), best)

    def test_wording(self):
        s = scenario("accuracy_drop")
        e = s["rep"]["items"]["6"]["scans"]["accuracy"]
        self.assertEqual(e["segment_ranked_first"], "2.1.304 to 2.1.322")
        if e["case"] == "single versions":
            self.assertEqual(e["wording"], "starts at 2.1.304 and ends at 2.1.322")
        else:
            self.assertIn("a version from", e["wording"])
        self.assertEqual(e["last_version_middle_95"][1], "2.1.322")
        lo, hi = (VI[v] for v in e["first_version_middle_95"])
        self.assertLessEqual(lo, hi)
        self.assertTrue(0.0 <= e["share_of_draws_with_the_same_segment"] <= 1.0)
        n = s["rep"]["items"]["6"]["scans"]["accuracy"]
        self.assertEqual(n["wording_goes_into_the_summary"], n["case"] == "a span")
        self.assertFalse(scenario("null")["rep"]["items"]["6"]["scans"]["accuracy"]["wording_goes_into_the_summary"])

    def test_middle_95(self):
        self.assertEqual(xn.middle_95(np.array([3] * 100)), (3, 3))
        self.assertEqual(xn.middle_95(np.array([1] * 2 + [3] * 96 + [9] * 2)), (3, 3))
        self.assertEqual(xn.middle_95(np.array([1] * 3 + [3] * 94 + [9] * 3)), (1, 9))


class Item7TwoWaysOfCounting(Base):
    def check_sizes(self, s, label):
        e = s["rep"]["items"]["7"]["reports"][label]
        passes = set(s["final" if label == "final" else "interim"]["passes"])
        for sg in e["segments"]:
            for metric, field in (("accuracy", "difference_errors_and_voids_left_out"),
                                  ("accuracy_bad_as_wrong", "difference_errors_and_voids_as_wrong")):
                self.assertNear(sg[field], py_diff(cells(s["rows"], VALUE[metric]), sg["start"], sg["end"],
                                                   passes=passes))
        return e

    def test_different_segments_both_declared(self):
        s = scenario("two_ways_differ_same_sign")
        e = self.check_sizes(s, "final")
        self.assertEqual(e["case"], "both declare a difference, on different segments")
        self.assertTrue(e["registered_line_declares"])
        self.assertIn("2.1.303 to 2.1.322", e["sentence"])
        self.assertIn("2.1.285 to 2.1.289", e["sentence"])
        dec = s["rep"]["declared"]["differences"]
        self.assertEqual(sorted(d["segment"] for d in dec), ["2.1.285 to 2.1.289", "2.1.303 to 2.1.322"])
        self.assertEqual(len(s["rep"]["items"]["5"]["for_each_declared_difference"]), 2)

    def test_opposite_signs(self):
        s = scenario("two_ways_opposite_signs")
        e = self.check_sizes(s, "final")
        self.assertEqual(e["case"], "both declare a difference, with opposite signs")
        self.assertFalse(e["registered_line_declares"])
        self.assertNotIn("no difference was seen", e["sentence"])
        self.assertIn("declares none here", e["sentence"])

    def test_same_and_different_segments_without_both_declaring(self):
        s = scenario("null")
        self.assertEqual(self.check_sizes(s, "final")["case"], "same segment")
        e = self.check_sizes(s, "interim")
        self.assertEqual(e["case"], "different segments")
        self.assertIn("name different segments", e["sentence"])


class Item8CutAt2_1_303(Base):
    def test_numbers_and_wording(self):
        s = scenario("cut_at_2_1_303")
        e = s["rep"]["items"]["8"]
        k = VI["2.1.303"]
        self.assertNear(e["accuracy"]["difference"], py_diff(cells(s["rows"], VALUE["accuracy"]), k, 38))
        self.assertNear(e["accuracy"]["difference"],
                        s["final"]["secondary"]["before_and_after_2_1_303"]["difference_after_item_difficulty"])
        self.assertNear(e["thinking"]["ratio"], math.exp(py_diff(cells(s["rows"], VALUE["log_thinking"]), k, 38)))
        ins, outs = raw_side(s["rows"], k, 38, VALUE["accuracy"])
        self.assertNear(e["accuracy"]["accuracy_from_on"], sum(ins) / len(ins))
        self.assertNear(e["accuracy"]["accuracy_before"], sum(outs) / len(outs))
        self.assertTrue(e["thinking"]["range_leaves_out_one"])
        self.assertEqual(e["thinking"]["case"], "range leaves out zero while the scan declares nothing")
        self.assertIn("779 segments", e["thinking"]["sentence"])
        acc = e["accuracy"]
        self.assertEqual(acc["case"] == "range leaves out zero while the scan declares nothing",
                         bool(acc["range_leaves_out_zero"]) and not acc["scan_declares"])

    def test_no_wording_when_the_scan_declares(self):
        e = scenario("accuracy_drop")["rep"]["items"]["8"]["accuracy"]
        self.assertTrue(e["scan_declares"])
        self.assertEqual(e["case"], "no special wording")


class Item13ThirdPass(Base):
    def test_cases_in_the_scenarios(self):
        want = {("not_confirmed", "accuracy"): "not confirmed by the third pass",
                ("only_p_on_two_passes", "accuracy"): "two passes had only p < 0.05",
                ("accuracy_drop", "accuracy"): "declared on two passes and on all passes",
                ("null", "accuracy"): "declared on neither",
                ("cut_at_2_1_303", "thinking"): "not confirmed by the third pass"}
        for (name, test), case in want.items():
            e = scenario(name)["rep"]["items"]["13"]["tests"][test]
            self.assertEqual(e["case"], case, name)
        e = scenario("not_confirmed")["rep"]["items"]["13"]["tests"]["accuracy"]
        self.assertIn("not confirmed by the third pass", e["sentence"])
        self.assertEqual(e["passes_1_and_2"]["ways"]["accuracy"]["p"], scenario("not_confirmed")["interim"]["accuracy"]["p"])
        e = scenario("only_p_on_two_passes")["rep"]["items"]["13"]["tests"]["accuracy"]
        self.assertIn("p < 0.05", e["sentence"])

    def test_every_branch(self):
        self.assertEqual(xn.third_pass_wording(True, True, ["x"])[0], "declared on two passes and on all passes")
        self.assertEqual(xn.third_pass_wording(True, False, ["x"])[0], "not confirmed by the third pass")
        self.assertEqual(xn.third_pass_wording(False, True, ["x"])[0], "two passes had only p < 0.05")
        self.assertIn("It is declared on all passes", xn.third_pass_wording(False, True, ["x"])[1])
        self.assertEqual(xn.third_pass_wording(False, True, [])[0], "declared on all passes only")
        self.assertEqual(xn.third_pass_wording(False, False, [])[0], "declared on neither")


class Item14BothSides(Base):
    def test_high_in_the_middle(self):
        s = scenario("high_in_the_middle")
        e = s["rep"]["items"]["14"]["scans"]["accuracy"]
        self.assertEqual(e["segment"], "2.1.290 to 2.1.295")
        cs = cells(s["rows"], VALUE["accuracy"])
        self.assertNear(e["before"], py_part(cs, 0, 10))
        self.assertNear(e["segment_part"], py_part(cs, 10, 16))
        self.assertNear(e["after"], py_part(cs, 16, 39))
        self.assertNear(e["gap_before_after"], abs(py_part(cs, 0, 10) - py_part(cs, 16, 39)))
        self.assertEqual(e["case"], "higher than both sides, which are at about the same level")
        self.assertEqual(e["sentence"], xn.SENTENCES["item_14"])

    def test_always_given_and_no_sentence_for_a_drop(self):
        s = scenario("null")
        for key in xn.RUNS:
            e = s["rep"]["items"]["14"]["scans"][key]
            self.assertIsNone(e["sentence"])
            self.assertIn("before", e)
        self.assertIsNone(scenario("accuracy_drop")["rep"]["items"]["14"]["scans"]["accuracy"]["sentence"])


class Item15UnchangedRequest(Base):
    def test_drop_inside_a_group(self):
        s = scenario("accuracy_drop")
        it = s["rep"]["items"]["15"]
        e = it["for_each_declared_difference"][0]
        self.assertEqual(e["boundaries"]["start"]["between"], ["2.1.303", "2.1.304"])
        self.assertTrue(e["boundaries"]["start"]["inside_a_group"])
        self.assertEqual(e["boundaries"]["start"]["nearest_versions_where_the_request_changed"], ["2.1.303"])
        self.assertIsNone(e["boundaries"]["end"]["boundary"])
        self.assertEqual(e["sentence"], xn.SENTENCES["item_15"].format(x="2.1.304"))
        self.assertIsNone(e["adapted_sentence"])
        self.assertTrue(it["scans_over_groups"]["accuracy"]["registered_and_rebuilt_agree"])

    def test_high_segment_ends_inside_a_group(self):
        s = scenario("high_in_the_middle")
        e = s["rep"]["items"]["15"]["for_each_declared_difference"][0]
        self.assertEqual(e["drop_starts_at"], "2.1.296")
        self.assertTrue(e["boundaries"]["end"]["inside_a_group"])
        self.assertEqual(e["sentence"], xn.SENTENCES["item_15"].format(x="2.1.296"))

    def test_thinking_gets_its_own_scan_over_groups(self):
        e = scenario("thinking_drop_with_zeros")["rep"]["items"]["15"]["for_each_declared_difference"][0]
        g = e["scan_over_groups"]["computed_here"]
        self.assertEqual(g["last_version"], "2.1.322")

    def test_boundaries_by_hand(self):
        versions = [f"v{i}" for i in range(8)]
        groups = [["v0", "v1"], ["v2", "v3", "v4", "v5"], ["v6", "v7"]]
        b = xn.boundaries(groups, versions, 4, 6)
        self.assertEqual(b["start"]["between"], ["v3", "v4"])
        self.assertTrue(b["start"]["inside_a_group"])
        self.assertEqual(b["start"]["nearest_versions_where_the_request_changed"], ["v2", "v6"])  # a tie
        self.assertTrue(b["end"]["inside_a_group"])
        self.assertEqual(b["end"]["nearest_versions_where_the_request_changed"], ["v6"])
        b = xn.boundaries(groups, versions, 2, 7)
        self.assertFalse(b["start"]["inside_a_group"])
        self.assertIsNone(b["end"]["boundary"])

    def test_adapted_sentence_for_a_low_segment_in_the_middle(self):
        s = scenario("accuracy_drop")
        d = {"test": "accuracy", "start": 22, "end": 30, "diff": -0.1, "drop_named": True,
             "segment": "2.1.304 to 2.1.312", "effect": "diff", "named_by": ["accuracy"]}
        e = xn.item_15_unchanged_request(s["ctx"], [d])["for_each_declared_difference"][0]
        self.assertIsNotNone(e["sentence"])
        self.assertIn("Versions 2.1.304 to 2.1.312 are lower", e["adapted_sentence"])


class Item18HowThinkingIsCounted(Base):
    def test_counts_back(self):
        s = scenario("null")
        it = s["rep"]["items"]["18"]
        truth = s["truth"]
        cs = cells(s["rows"], lambda r: r if scored(r) else None)
        for k, e in enumerate(it["per_version"]):
            v = e["version"]
            rows = [c[k] for c in cs.values() if k in c]
            tr = [r for r in rows if tried(r)]
            nt = [r for r in rows if not tried(r)]
            self.assertEqual(e["tried_a_tool"]["asks"], len(tr))
            self.assertEqual(e["did_not"]["asks"], len(nt))
            self.assertTrue(all(truth[(r["pass"], v, r["unit"])]["tried"] for r in tr))
            if v == "2.1.300":
                self.assertEqual(e["tried_a_tool"]["equal_to_last_message_only"], len(tr))
                self.assertEqual(e["did_not"]["equal"], len(nt))
            elif v == "2.1.301":
                self.assertEqual(e["tried_a_tool"]["other"], len(tr))
                self.assertEqual(e["did_not"]["other"], len(nt))
            else:
                self.assertTrue(e["tried_a_tool"]["all_equal"] or not tr)
                self.assertTrue(e["did_not"]["all_equal"])
            self.assertEqual(e["tried_a_tool"]["lines_of_one_message_differ"], len(tr))
        self.assertEqual(it["scored_asks_without_a_raw_record"], 0)
        th = it["api_against_author_on_2_1_322"]["thinking"]
        self.assertEqual(th, s["final"]["small_groups"]["api"]["against_author_same_version"]["thinking"])

    def test_message_counting_and_resends(self):
        ev = [{"type": "assistant", "parent_tool_use_id": None, "message": {"id": "a", "usage": {"output_tokens": 5}}},
              {"type": "assistant", "parent_tool_use_id": None, "message": {"id": "a", "usage": {"output_tokens": 40}}},
              {"type": "assistant", "parent_tool_use_id": "t", "message": {"id": "s", "usage": {"output_tokens": 999}}},
              {"type": "assistant", "parent_tool_use_id": None, "message": {"id": "b", "usage": {"output_tokens": 60}}}]
        m = xn.message_output_tokens(ev)
        self.assertEqual((m["messages"], m["sum"], m["last"], m["lines_of_one_message_differ"]), (2, 100, 60, True))
        rows, _ = fd.make_rows(seed=40, passes=1, with_small=False)
        r0 = next(r for r in rows if r["group"] == "main" and r["outcome"] == "scored")
        resent = dict(r0, plan="F1r", ask_id="r1b000o00001", output_tokens=r0["output_tokens"] + 11,
                      resend_of={"plan": "F1", "ask_id": r0["ask_id"]})
        raw = fd.make_raw([r0, resent])
        with tempfile.TemporaryDirectory() as tmp:
            got = xn.read_raw(fd.write_raw(raw, Path(tmp)))
        self.assertEqual(len(got), 1)
        self.assertEqual(got[(1, r0["version"], r0["unit"])]["sum"], r0["output_tokens"] + 11)


# ------------------------------------------------------------------------------ the program as a whole

class Program(Base):
    def setUp(self):
        self.s = scenario("accuracy_drop")
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.graded = t / "graded.jsonl"
        self.graded.write_text("".join(json.dumps(r) + "\n" for r in self.s["rows"]))
        self.final = t / "final.json"
        self.final.write_text(json.dumps(self.s["final"]))
        self.interim = t / "interim.json"
        self.interim.write_text(json.dumps(self.s["interim"]))
        self.items = t / "items.json"
        self.items.write_text(json.dumps(fd.panel()))
        self.raw = fd.write_raw(fd.make_raw(self.s["rows"]), t / "raw")
        self.out = t / "out"

    def tearDown(self):
        self.tmp.cleanup()

    def args(self, final=None):
        a = ["--graded", str(self.graded), "--final-report", str(final or self.final), "--interim-report",
             str(self.interim), "--items", str(self.items), "--author-repo", AUTHOR_REPO, "--out", str(self.out),
             "--draws", "300", "--placement-draws", "50", "--scan-shuffles", "100"]
        for d in self.raw:
            a += ["--raw-dir", str(d)]
        return a

    def test_one_command_writes_both_files(self):
        self.assertEqual(xn.main(self.args()), 0)
        rep = json.loads((self.out / "extra_numbers.json").read_text())
        self.assertEqual(sorted(rep["items"], key=int), [str(i) for i in xn.ITEMS_HERE])
        for i in xn.ITEMS_HERE:
            self.assertEqual(rep["items"][str(i)]["item"], i)
        self.assertTrue(rep["checks_against_the_registered_reports"]["ok"])
        md = (self.out / "extra_numbers.md").read_text()
        for i in xn.ITEMS_HERE:
            self.assertIn(f"## Item {i}.", md)
        self.assertNotRegex(md + json.dumps(rep), r"/Users/|/private/|/var/folders/")
        answers = {r["answer"] for r in self.s["rows"] if r.get("answer") and len(r["answer"]) > 3}
        text = md + json.dumps(rep)
        self.assertFalse([a for a in answers if a in text])

    def test_stops_on_other_data(self):
        bad = json.loads(json.dumps(self.s["final"]))
        bad["thinking"]["diff"] += 0.01
        path = Path(self.tmp.name) / "bad.json"
        path.write_text(json.dumps(bad))
        self.assertEqual(xn.main(self.args(final=path)), 2)
        self.assertFalse((self.out / "extra_numbers.json").exists())

    def test_no_final_report_no_run(self):
        self.assertEqual(xn.main(self.args(final=Path(self.tmp.name) / "missing.json")), 2)

    def test_a_path_in_the_outputs_stops_the_writing(self):
        rep = {"items": {}, "x": "/Users/someone/file"}
        with self.assertRaises(RuntimeError):
            xn.write_outputs({**self.s["rep"], "leak": rep}, self.out)
        self.assertFalse((self.out / "extra_numbers.json").exists())


if __name__ == "__main__":
    unittest.main()
