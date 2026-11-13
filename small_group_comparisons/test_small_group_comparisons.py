"""Self-tests of small_group_comparisons.py on made-up data (fake_data.py). Nothing here reads a record of the
experiment, and no model is asked.

    python -B test_small_group_comparisons.py

Every number the program writes is worked out here a second way: from fake_data's list of made-up asks, with
plain Python loops, without grade.py, analyze.py or the program. Ranges are checked against a closed form where
the made-up data give one (every item differs by the same amount, so the range is that amount) and otherwise
against a second computation of the redraws (the same random draws, means and percentiles computed in plain
Python). Some numbers are also checked against analyze.small_groups, the registered function.

LiveNerf's graders are stood in for by fake_data's copies of their rules. If the environment variable
LIVENERF_REPO names a copy of LiveNerf's repository, one test checks that the stand-ins agree with the real
graders on every made-up answer.
"""

import copy
import json
import math
import os
import shutil
import statistics
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

import small_group_comparisons as m
import fake_data as fd
from ccversions import analyze, grade

DRAWS = 2000
SEED = 20261111


# ------------------------------------------------------------------ the second way

def value_fns():
    """Each measure as a function of one made-up ask: a number, or None when the ask does not count."""
    def acc(a):
        return None if a["kind"] == "void" else float(a["kind"] == "right")

    def acc_bad(a):
        return 0.0 if a["kind"] == "void" else float(a["kind"] == "right")

    def think(a):
        return None if a["kind"] == "void" else math.log(a["thinking"] + 1)

    def out(a):
        return None if a["kind"] == "void" else math.log(a["output"] + 1)

    return {"accuracy": acc, "accuracy_bad_as_wrong": acc_bad, "thinking": think, "output": out}


def unread(a):
    return None if a["kind"] == "void" else (0.0 if fd.is_read(a) else 1.0)


def acc_read(a):
    return float(a["kind"] == "right") if a["kind"] != "void" and fd.is_read(a) else None


def means(asks, fn):
    acc = {}
    for a in asks:
        v = fn(a)
        if v is not None:
            acc.setdefault(a["unit"], []).append(v)
    return {u: sum(v) / len(v) for u, v in acc.items()}


def by_hand(a_asks, b_asks, fn):
    """Item by item: (mean difference, the differences in item order)."""
    A, B = means(a_asks, fn), means(b_asks, fn)
    units = sorted(set(A) & set(B))
    d = [A[u] - B[u] for u in units]
    return sum(d) / len(d), d


def py_quantile(xs, q):
    """numpy's default (linear) percentile, in plain Python."""
    xs = sorted(xs)
    pos = q * (len(xs) - 1)
    lo = math.floor(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def py_range(d, draws=DRAWS):
    """The redraws of analyze.paired (the same random items), the means and percentiles in plain Python."""
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(d), size=(draws, len(d))).tolist()
    boot = [sum(d[j] for j in row) / len(d) for row in idx]
    return [py_quantile(boot, 0.025), py_quantile(boot, 0.975)]


def run(root, *extra, grader=None):
    return m.main(fd.argv(root, "--draws", str(DRAWS), *extra), grader=grader or fd.fake_grader(m))


def output(root):
    return json.loads((Path(root) / "out" / "small_group_comparisons.json").read_text())


class Base(unittest.TestCase):
    world_args = {}

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.world = fd.World(**cls.world_args)
        cls.parts = fd.write_world(cls.world, cls.tmp / "w")
        cls.code = run(cls.tmp / "w")
        cls.rep = output(cls.tmp / "w") if cls.code == 0 else None

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def copy_world(self, name):
        dest = self.tmp / name
        shutil.copytree(self.tmp / "w", dest)
        shutil.rmtree(dest / "out", ignore_errors=True)
        return dest

    def close(self, got, want, places=12, msg=None):
        self.assertIsNotNone(got, msg)
        self.assertAlmostEqual(got, want, places=places, msg=msg)

    def check_paired(self, r, a_asks, b_asks, name, *, with_range=True):
        """One measure of the program's output against the second way."""
        fn = value_fns()[name]
        diff, d = by_hand(a_asks, b_asks, fn)
        self.assertEqual(r["items"], len(d))
        self.close(r["diff"], diff, msg=name)
        A, B = means(a_asks, fn), means(b_asks, fn)
        units = sorted(set(A) & set(B))
        self.close(r["a"], sum(A[u] for u in units) / len(units), msg=name)
        self.close(r["b"], sum(B[u] for u in units) / len(units), msg=name)
        if with_range:
            lo, hi = py_range(d)
            self.close(r["range_95"][0], lo, places=10, msg=name)
            self.close(r["range_95"][1], hi, places=10, msg=name)
        if name in ("thinking", "output"):
            self.close(r["ratio"], math.exp(diff), msg=name)


# ------------------------------------------------------------------ a world with a planted difference

class PlantedWorld(Base):
    world_args = {"nosent": "planted", "flags": "planted_322"}

    def setUp(self):
        self.assertEqual(self.code, 0)
        self.n = self.rep["numbers"]
        self.w = self.world

    def test_check_against_the_final_report(self):
        c = self.rep["check_against_the_final_report"]
        self.assertTrue(c["ok"], c["problems"])
        self.assertEqual(c["compared"], ["small_groups.flags_on", "small_groups.author"])
        self.assertEqual(self.rep["sources"]["registered_run"]["resent"], 1)

    def test_planted_difference_has_its_known_size(self):
        r = self.n["nosent_against_main"]["2.1.280"]["measures"]
        self.assertEqual(len(self.w.P), 12)
        self.close(r["accuracy"]["diff"], -12 / 78)          # twelve items right in every pass, now wrong
        self.close(r["thinking"]["ratio"], 2.0, places=9)     # every ask thinks twice as much (tokens + 1)
        self.close(r["thinking"]["ratio_range_95"][0], 2.0, places=9)
        self.close(r["thinking"]["ratio_range_95"][1], 2.0, places=9)
        self.close(r["output"]["ratio"], 1.0, places=12)

    def test_nosent_against_main_every_number(self):
        for label, versions in (("2.1.280", ("2.1.280",)), ("2.1.322", ("2.1.322",)),
                                ("both_versions", ("2.1.280", "2.1.322"))):
            a = self.w.side("nosent", versions, (1, 2, 3))
            b = self.w.side("main", versions, (1, 2, 3))
            e = self.n["nosent_against_main"][label]
            self.assertEqual(e["passes"], {"a": [1, 2, 3], "b": [1, 2, 3]})
            for name in ("accuracy", "accuracy_bad_as_wrong", "thinking", "output"):
                self.check_paired(e["measures"][name], a, b, name)
                self.assertEqual(e["measures"][name]["asks_a"], len(a))
                self.assertEqual(e["measures"][name]["asks_b"], len(b))

    def test_both_versions_is_what_small_groups_gives(self):
        """The registered function on the same rows: nosent pooled over its two versions against main on them."""
        rows = [r for rs in self.parts["graded"].values() for r in rs]
        grader = fd.fake_grader(m)
        for plan in ("NS1", "NS2", "NS3"):
            rows += grader.grade(self.parts["raw"][plan] + self.parts["raw"].get(f"{plan}r", []))
        want = analyze.small_groups(analyze.apply_resends(rows))["nosent"]["against_main_same_versions"]
        got = self.n["nosent_against_main"]["both_versions"]["measures"]
        for name in want:
            self.close(got[name]["diff"], want[name]["diff"], msg=name)
            self.assertEqual(got[name]["items"], want[name]["items"])
            self.assertEqual((got[name]["asks_a"], got[name]["asks_b"]), (want[name]["asks_a"], want[name]["asks_b"]))

    def test_gap_between_the_versions(self):
        fns = value_fns()
        g = self.n["nosent_gap"]["measures"]
        for name, fn in fns.items():
            sides = {k: means(self.w.side(grp, (v,), (1, 2, 3)), fn)
                     for k, grp, v in (("n280", "nosent", "2.1.280"), ("n322", "nosent", "2.1.322"),
                                       ("m280", "main", "2.1.280"), ("m322", "main", "2.1.322"))}
            units = sorted(set.intersection(*(set(s) for s in sides.values())))
            gn = [sides["n322"][u] - sides["n280"][u] for u in units]
            gm = [sides["m322"][u] - sides["m280"][u] for u in units]
            both = [x - y for x, y in zip(gn, gm)]
            self.assertEqual(g[name]["items"], len(units))
            for key, d in (("nosent_322_minus_280", gn), ("main_322_minus_280", gm), ("nosent_gap_minus_main_gap", both)):
                self.close(g[name][key]["diff"], sum(d) / len(d), msg=f"{name} {key}")
                lo, hi = py_range(d)
                self.close(g[name][key]["range_95"][0], lo, places=10)
                self.close(g[name][key]["range_95"][1], hi, places=10)
        # the third is the first minus the second
        a = g["accuracy"]
        self.close(a["nosent_gap_minus_main_gap"]["diff"], a["nosent_322_minus_280"]["diff"] - a["main_322_minus_280"]["diff"])

    def test_unread_answers(self):
        u = self.n["nosent_unread"]
        self.assertNotIn("not_computable", u)
        for label, versions in (("2.1.280", ("2.1.280",)), ("2.1.322", ("2.1.322",)),
                                ("both_versions", ("2.1.280", "2.1.322"))):
            for side in ("nosent", "main"):
                asks = self.w.side(side, versions, (1, 2, 3))
                scored = [a for a in asks if a["kind"] != "void"]
                read = [a for a in scored if fd.is_read(a)]
                c = u[label][side]
                self.assertEqual((c["asks"], c["scored"], c["not_read"], c["read"]),
                                 (len(asks), len(scored), len(scored) - len(read), len(read)))
                self.close(c["share_not_read"], (len(scored) - len(read)) / len(scored))
                self.close(c["accuracy_all_scored"], sum(a["kind"] == "right" for a in scored) / len(scored))
                self.close(c["accuracy_over_read"], sum(a["kind"] == "right" for a in read) / len(read))
                self.assertEqual(c["errors_and_voids"], len(asks) - len(scored))
                self.close(c["accuracy_bad_as_wrong"], sum(a["kind"] == "right" for a in asks) / len(asks))
            a, b = self.w.side("nosent", versions, (1, 2, 3)), self.w.side("main", versions, (1, 2, 3))
            for key, fn in (("share_not_read", unread), ("accuracy_over_read", acc_read)):
                diff, d = by_hand(a, b, fn)
                r = u[label]["nosent_minus_main_item_by_item"][key]
                self.close(r["diff"], diff)
                lo, hi = py_range(d)
                self.close(r["range_95"][0], lo, places=10)
                self.close(r["range_95"][1], hi, places=10)
        self.assertEqual(u["2.1.322"]["nosent"]["not_read"], 6)   # three with no block, three in a wrong form
        self.assertEqual(u["2.1.322"]["nosent"]["scored"], 233)   # one void

    def test_resends_take_the_place_of_their_ask(self):
        f = self.rep["resend_fields"]["NS1"]
        self.assertEqual((f["resends"], f["resends_with_their_ask"], f["never_reached_the_model"],
                          f["never_reached_and_not_resent"]), (2, 2, 2, 0))
        self.assertEqual(f["records_lacking_a_field"], {})
        # the two resent asks count with the resend's answer: no error is left in nosent's rows
        e = self.n["nosent_against_main"]["both_versions"]["measures"]
        self.assertEqual(e["accuracy"]["asks_a"], 468)
        self.close(e["accuracy_bad_as_wrong"]["a"],
                   statistics.mean(means(self.w.side("nosent", ("2.1.280", "2.1.322"), (1, 2, 3)),
                                         value_fns()["accuracy_bad_as_wrong"]).values()))

    def test_flags_on_two_and_three_passes(self):
        fo = self.n["flags_on_against_main"]
        main = self.w.side("main", fd.FLAGS_VERSIONS, (1, 2, 3))
        for key, passes in (("two_passes", (1, 2)), ("three_passes", (1, 2, 3))):
            a = self.w.side("flags_on", fd.FLAGS_VERSIONS, passes)
            for name in ("accuracy", "accuracy_bad_as_wrong", "thinking", "output"):
                self.check_paired(fo[key]["measures"][name], a, main, name)
        # two passes is the registered report's own figure (its range has 10,000 draws, these tests fewer)
        want = self.parts["final"]["small_groups"]["flags_on"]["against_main_same_versions"]
        for name in want:
            self.close(fo["two_passes"]["measures"][name]["diff"], want[name]["diff"])
            self.assertEqual(fo["two_passes"]["measures"][name]["items"], want[name]["items"])

    def test_flags_on_three_passes_is_what_small_groups_gives(self):
        rows = [r for rs in self.parts["graded"].values() for r in rs]
        rows += fd.fake_grader(m).grade(self.parts["raw"]["S3"])
        want = analyze.small_groups(analyze.apply_resends(rows))["flags_on"]["against_main_same_versions"]
        got = self.n["flags_on_against_main"]["three_passes"]["measures"]
        for name in want:
            self.close(got[name]["diff"], want[name]["diff"], msg=name)
            self.assertEqual(got[name]["asks_a"], 936)

    def test_author_against_main(self):
        am = self.n["author_against_main"]
        main = self.w.side("main", ("2.1.280",), (1, 2, 3))
        for key, passes in (("two_passes", (1, 2)), ("three_passes", (1, 2, 3))):
            a = self.w.side("author", ("2.1.280",), passes)
            for name in ("accuracy", "accuracy_bad_as_wrong", "thinking", "output"):
                self.check_paired(am[key]["measures"][name], a, main, name)

    def test_author_against_livenerf_range(self):
        lr = self.n["author_against_livenerf_range"]
        days = fd.daily_values()
        for name, test in (("before_3_november", lambda d: d < "2026-11-03"), ("from_3_november_on", lambda d: d >= "2026-11-03")):
            vals = [v for d, v in days.items() if test(d)]
            per = lr["livenerf_periods"][name]
            self.assertEqual(per["days"], len(vals))
            self.assertEqual((per["first_day"], per["last_day"]), (min(d for d in days if test(d)), max(d for d in days if test(d))))
            self.close(per["accuracy_lowest"], min(v[0] for v in vals))
            self.close(per["accuracy_highest"], max(v[0] for v in vals))
            self.close(per["output_tokens_median_lowest"], min(v[1] for v in vals))
            self.close(per["output_tokens_median_highest"], max(v[1] for v in vals))
        for key, passes in (("pass_1", (1,)), ("pass_2", (2,)), ("pass_3", (3,)), ("passes_1_and_2_pooled", (1, 2)),
                            ("all_passes_pooled", (1, 2, 3))):
            asks = self.w.side("author", ("2.1.280",), passes)
            acc = sum(a["kind"] == "right" for a in asks) / len(asks)
            med = statistics.median(a["output"] for a in asks)
            f = lr["this_group"][key]
            self.close(f["accuracy"], acc)
            self.close(f["accuracy_bad_as_wrong"], acc)       # no error or void among author's made-up asks
            self.close(f["output_tokens_median"], med)
            self.assertEqual((f["scored"], f["errors_and_voids"], f["passes"]), (len(asks), 0, list(passes)))
            for name in ("before_3_november", "from_3_november_on"):
                per = lr["livenerf_periods"][name]
                self.assertEqual(f["inside"][name]["accuracy"], per["accuracy_lowest"] <= acc <= per["accuracy_highest"])
                self.assertEqual(f["inside"][name]["accuracy_bad_as_wrong"],
                                 per["accuracy_lowest"] <= acc <= per["accuracy_highest"])   # author has no error here
                self.assertEqual(f["inside"][name]["output_tokens_median"],
                                 per["output_tokens_median_lowest"] <= med <= per["output_tokens_median_highest"])

    def test_livenerf_rows_are_its_measured_model_over_all_items(self):
        self.assertEqual(self.rep["sources"]["livenerf_daily"]["rows"], len(fd.daily_values()))

    def test_item_9_same_day(self):
        i9 = self.n["item_9"]["passes"]
        days = fd.daily_values()
        for p in (1, 2, 3):
            asks = self.w.side("author", ("2.1.280",), (p,))
            per_day = {}
            for a in asks:
                per_day.setdefault(a["started"].date().isoformat(), []).append(a)
            ref = sum(days[d][0] * len(v) for d, v in per_day.items()) / len(asks)
            acc = sum(a["kind"] == "right" for a in asks) / len(asks)
            e = i9[str(p)]
            self.assertEqual(e["scored_asks_by_utc_day"], {d: len(v) for d, v in sorted(per_day.items())})
            self.close(e["accuracy"], acc)
            self.close(e["livenerf"], ref)
            self.close(e["difference"], acc - ref)
            self.close(e["difference_bad_as_wrong"], sum(a["kind"] == "right" for a in asks) / len(asks) - ref)
            # one answer per item: the range of the pass's accuracy is the range of the mean of item scores
            scores = [float(a["kind"] == "right") for a in sorted(asks, key=lambda a: a["unit"])]
            lo, hi = py_range(scores)
            self.close(e["range_95"][0], lo, places=10)
            self.close(e["range_95"][1], hi, places=10)
            self.close(e["difference_range_95"][0], lo - ref, places=10)
            self.assertEqual(e["differ"], not (lo <= ref <= hi))
            self.assertEqual(e["sentence"] is not None, e["differ"])
            self.assertEqual(e["added"], p == 3)
        self.assertEqual(set(i9["2"]["each_day"]), {"2026-11-11", "2026-11-12"})
        for day, piece in i9["2"]["each_day"].items():
            asks = [a for a in self.w.side("author", ("2.1.280",), (2,)) if a["started"].date().isoformat() == day]
            acc = sum(a["kind"] == "right" for a in asks) / len(asks)
            self.close(piece["accuracy"], acc)
            self.close(piece["livenerf"], days[day][0])
            self.close(piece["difference"], acc - days[day][0])
            lo, hi = py_range([float(a["kind"] == "right") for a in sorted(asks, key=lambda a: a["unit"])])
            self.close(piece["range_95"][0], lo, places=10)
            self.close(piece["range_95"][1], hi, places=10)
        self.assertEqual(i9["2"]["scored_asks_by_utc_day"], {"2026-11-11": 50, "2026-11-12": 28})
        self.assertTrue(i9["3"]["differ"])           # LiveNerf's 13 November is set far below
        self.assertIn("do not depend on it", i9["3"]["sentence"])

    def test_item_9_range_is_what_paired_gives_against_zero(self):
        """A third way for one range: analyze.paired of the pass against a side that is wrong on every item."""
        rows = [r for r in self.parts["graded"]["F1"] if r["group"] == "author" and r["version"] == "2.1.280"]
        zero = [dict(r, score=0.0) for r in rows]
        want = analyze.paired(rows, zero, "accuracy", draws=DRAWS)["range_95"]
        got = self.n["item_9"]["passes"]["1"]["range_95"]
        self.close(got[0], want[0])
        self.close(got[1], want[1])

    def test_a_day_apart(self):
        da = self.n["a_day_apart"]
        x = da["author_2_1_322_pass_3_against_passes_1_and_2"]
        a, b = self.w.side("author", ("2.1.322",), (3,)), self.w.side("author", ("2.1.322",), (1, 2))
        for name in ("accuracy", "accuracy_bad_as_wrong", "thinking", "output"):
            self.check_paired(x["measures"][name], a, b, name)
        y = da["desktop_prompt_e_against_main_on_2_1_321"]
        want = fd.desktop_prompt_report()["comparisons"][1]["metrics"]
        self.assertEqual(y["metrics"]["accuracy"]["diff"], want["accuracy"]["diff"])
        self.assertEqual(y["metrics"]["log_thinking"]["range_95_shown"], want["log_thinking"]["range_95_shown"])
        self.assertNotIn("p", y["metrics"]["accuracy"])     # only the size is copied

    def test_send_times(self):
        st = {s["plan"]: s for s in self.rep["sources"]["nosent"]}
        t = st["NS2"]["send_times"]
        self.close(t["longest_gap_hours"], 6 + 20 / 3600, places=9)   # NS2's second half starts 6 hours later
        times = sorted(a["started"] for a in self.w.asks if a["source"] == "NS2")
        self.assertEqual((t["first"], t["last"]), (fd.iso(times[0]), fd.iso(times[-1])))
        self.assertLess(st["NS1"]["send_times"]["longest_gap_hours"], 0.1)

    def test_every_block_says_where_it_is_registered(self):
        for key, block in self.n.items():
            entry, part = block["registered_in"]
            self.assertIn(entry, (m.ENTRY_NOSENT, m.ENTRY_EXTRA), key)
            self.assertTrue(part)
        text = (self.tmp / "w" / "out" / "small_group_comparisons.md").read_text()
        self.assertEqual(text.count("Asked for by the change log entry"), len(self.n))

    def test_outputs_hold_no_answer_and_no_path(self):
        for name in ("small_group_comparisons.json", "small_group_comparisons.md"):
            text = (self.tmp / "w" / "out" / name).read_text()
            self.assertNotIn(fd.MARK, text)
            self.assertNotIn("made-up question", text)
            self.assertNotIn('"answer"', text)
            self.assertNotIn("fake-0", text)                  # no item name
            self.assertEqual(grade.PUBLIC_BAD.findall(text), [])
            self.assertNotIn(str(self.tmp), text)

    def test_item_16_cannot_speak_when_nothing_is_declared(self):
        i16 = self.n["item_16"]
        self.assertTrue(i16["nothing_declared"])
        self.assertEqual(i16["summary_sentence"], m.SENTENCES["item_16_cannot"])


def declared(final: dict, *, acc_seg=None, acc_diff=-0.1, think_seg=None, think_diff=-0.5, two_segments=False) -> dict:
    """A copy of the final report with declared differences written in (item 16 reads only these fields)."""
    f = copy.deepcopy(final)
    f["accuracy_difference_declared"] = acc_seg is not None
    f["thinking_difference_declared"] = think_seg is not None
    if acc_seg is not None:
        for key in ("accuracy", "accuracy_errors_and_voids_as_wrong"):
            seg = acc_seg if not (two_segments and key != "accuracy") else (acc_seg[0], acc_seg[1] - 1)
            f[key].update(best_start=seg[0], best_end=seg[1], diff=acc_diff, drop_named=acc_diff < 0)
    if think_seg is not None:
        f["thinking"].update(best_start=think_seg[0], best_end=think_seg[1], diff=think_diff, drop_named=True)
    return f


class Item16(unittest.TestCase):
    """The three wordings of item 16, on report files with declared differences written in."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.worlds = {}
        for flags in ("planted_322", "flat"):
            w = fd.World(nosent="same", flags=flags)
            parts = fd.write_world(w, cls.tmp / flags)
            cls.worlds[flags] = (w, parts)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_with(self, flags, final, name):
        w, parts = self.worlds[flags]
        root = self.tmp / name
        shutil.copytree(self.tmp / flags, root)
        (root / "final" / "report.json").write_text(json.dumps(final))
        self.assertEqual(run(root), 0)
        return w, output(root)["numbers"]["item_16"]

    def test_flags_on_shows_it_too(self):
        w, parts = self.worlds["planted_322"]
        final = declared(parts["final"], acc_seg=(38, 38), acc_diff=-0.08, think_seg=(38, 38), think_diff=-0.3)
        w, i16 = self.run_with("planted_322", final, "shown")
        acc, think = i16["declared_differences"]
        self.assertEqual((acc["test"], think["test"]), ("accuracy", "thinking"))
        for e in (acc, think):
            self.assertTrue(e["covered"])
            self.assertEqual(e["flags_on_versions_inside"], ["2.1.322"])
            self.assertEqual(e["flags_on_versions_outside"], ["2.1.280", "2.1.299", "2.1.308"])
            self.assertEqual(e["case"], "flags_on shows it too")
            self.assertTrue(e["sentence"].startswith("Group main shows a declared"))
        inside = w.side("flags_on", ("2.1.322",), (1, 2, 3))
        outside = w.side("flags_on", ("2.1.280", "2.1.299", "2.1.308"), (1, 2, 3))
        r = acc["flags_on_three_passes"]["accuracy"]
        self.assertAlmostEqual(r["diff"], -15 / 78, places=12)        # fifteen items wrong only on 2.1.322
        diff, d = by_hand(inside, outside, value_fns()["accuracy"])
        lo, hi = py_range(d)
        self.assertAlmostEqual(r["range_95"][0], lo, places=10)
        self.assertAlmostEqual(r["range_95"][1], hi, places=10)
        t = think["flags_on_three_passes"]["thinking"]
        self.assertAlmostEqual(t["ratio"], 0.5, places=9)              # half the tokens + 1 on every item
        self.assertAlmostEqual(t["ratio_range_95"][0], 0.5, places=9)
        # beside it: two passes, and main on the same split
        r2 = acc["flags_on_passes_1_and_2"]["accuracy"]
        self.assertAlmostEqual(r2["diff"], by_hand(w.side("flags_on", ("2.1.322",), (1, 2)),
                                                   w.side("flags_on", ("2.1.280", "2.1.299", "2.1.308"), (1, 2)),
                                                   value_fns()["accuracy"])[0], places=12)
        rm = acc["main_same_four_versions"]["accuracy"]
        self.assertAlmostEqual(rm["diff"], by_hand(w.side("main", ("2.1.322",), (1, 2, 3)),
                                                   w.side("main", ("2.1.280", "2.1.299", "2.1.308"), (1, 2, 3)),
                                                   value_fns()["accuracy"])[0], places=12)
        self.assertIsNone(i16["summary_sentence"])

    def test_flags_on_does_not_show_it(self):
        w, parts = self.worlds["flat"]
        final = declared(parts["final"], acc_seg=(38, 38), acc_diff=-0.08)
        w, i16 = self.run_with("flat", final, "not_shown")
        (e,) = i16["declared_differences"]
        self.assertTrue(e["covered"])
        self.assertAlmostEqual(e["flags_on_three_passes"]["accuracy"]["diff"], 0.0, places=14)  # the four answer alike
        self.assertEqual(e["case"], "flags_on does not show it")
        self.assertIn("about 7 points", e["sentence"])
        self.assertIn("not seen with them fetched", e["sentence"])

    def test_sign_against_the_declared_one_is_not_showing_it(self):
        w, parts = self.worlds["planted_322"]
        final = declared(parts["final"], acc_seg=(38, 38), acc_diff=+0.08)     # main higher there, flags_on lower
        w, i16 = self.run_with("planted_322", final, "other_sign")
        self.assertEqual(i16["declared_differences"][0]["case"], "flags_on does not show it")

    def test_no_declared_difference_between_versions_flags_on_covers(self):
        w, parts = self.worlds["planted_322"]
        final = declared(parts["final"], acc_seg=(5, 10))     # 2.1.285 to 2.1.290: no flags_on version inside
        w, i16 = self.run_with("planted_322", final, "cannot")
        (e,) = i16["declared_differences"]
        self.assertFalse(e["covered"])
        self.assertEqual(e["flags_on_versions_inside"], [])
        self.assertEqual(e["case"], "cannot speak to it")
        self.assertEqual(i16["summary_sentence"], m.SENTENCES["item_16_cannot"])

    def test_two_segments_of_one_accuracy_difference_are_both_listed(self):
        w, parts = self.worlds["planted_322"]
        final = declared(parts["final"], acc_seg=(26, 38), two_segments=True)
        w, i16 = self.run_with("planted_322", final, "two_segments")
        segs = [(e["segment"], e["named_by"]) for e in i16["declared_differences"]]
        self.assertEqual(segs, [("2.1.308 to 2.1.322", ["accuracy"]),
                                ("2.1.308 to 2.1.321", ["accuracy_errors_and_voids_as_wrong"])])
        self.assertEqual(i16["declared_differences"][1]["flags_on_versions_inside"], ["2.1.308"])


# ------------------------------------------------------------------ a world with no difference

class SameWorld(Base):
    world_args = {"nosent": "same", "flags": "flat"}

    def test_no_difference_gives_zero_and_a_range_of_zero(self):
        self.assertEqual(self.code, 0)
        n = self.rep["numbers"]
        for label in ("2.1.280", "2.1.322", "both_versions"):
            for name in ("accuracy", "accuracy_bad_as_wrong", "thinking", "output"):
                r = n["nosent_against_main"][label]["measures"][name]
                self.assertEqual(r["items"], 78)
                self.assertAlmostEqual(r["diff"], 0.0, places=14)
                self.assertAlmostEqual(r["range_95"][0], 0.0, places=14)
                self.assertAlmostEqual(r["range_95"][1], 0.0, places=14)
        for name in ("accuracy", "thinking"):
            self.assertAlmostEqual(n["nosent_gap"]["measures"][name]["nosent_gap_minus_main_gap"]["diff"], 0.0, places=14)
        u = n["nosent_unread"]["both_versions"]
        self.assertEqual(u["nosent"]["not_read"], 0)
        self.assertEqual(u["nosent"]["accuracy_over_read"], u["main"]["accuracy_over_read"])


# ------------------------------------------------------------------ what stops the program

class Stops(Base):
    world_args = {"nosent": "planted", "flags": "planted_322"}

    def stops(self, root, *extra, says=None):
        code = run(root, *extra)
        self.assertEqual(code, 2)
        self.assertFalse((Path(root) / "out" / "small_group_comparisons.json").exists())

    def test_a_plan_not_finished_stops_unless_allowed(self):
        root = self.copy_world("partial")
        asks = sorted((root / "nosentraw" / "NS3" / "asks").glob("*.json"))
        for p in asks[78:]:
            p.unlink()
        self.stops(root)
        self.assertEqual(run(root, "--allow-partial"), 0)
        rep = output(root)
        self.assertTrue(rep["warnings"] and "NS3 partly sent" in rep["warnings"][0])
        st = {s["plan"]: s for s in rep["sources"]["nosent"]}["NS3"]
        self.assertEqual((st["state"], st["asks_present"], st["asks_expected"]), ("partly sent", 78, 156))
        self.assertEqual(st["asks_missing_by_arm"], {"nosent 2.1.322": 78})
        r = rep["numbers"]["nosent_against_main"]["2.1.322"]
        self.assertEqual(r["passes"]["a"], [1, 2])
        self.assertEqual(r["measures"]["accuracy"]["asks_a"], 156)
        text = (root / "out" / "small_group_comparisons.md").read_text()
        self.assertIn("WARNING", text)

    def test_a_plan_not_sent_stops_unless_allowed(self):
        root = self.copy_world("not_sent")
        shutil.rmtree(root / "nosentraw" / "NS3")
        self.stops(root)
        self.assertEqual(run(root, "--allow-partial"), 0)
        rep = output(root)
        st = {s["plan"]: s for s in rep["sources"]["nosent"]}["NS3"]
        self.assertEqual(st["state"], "not sent")
        self.assertEqual(rep["numbers"]["nosent_against_main"]["2.1.280"]["passes"]["a"], [1, 2])

    def test_an_ask_that_never_reached_the_model_and_is_not_resent_yet(self):
        root = self.copy_world("pending")
        shutil.rmtree(root / "nosentraw" / "NS1r")
        self.stops(root)
        self.assertEqual(run(root, "--allow-partial"), 0)
        st = {s["plan"]: s for s in output(root)["sources"]["nosent"]}["NS1"]
        self.assertEqual((st["state"], st["never_reached_and_not_resent"]), ("partly sent", 2))

    def test_a_resend_that_points_to_no_ask_stops_always(self):
        root = self.copy_world("orphan")
        f = sorted((root / "nosentraw" / "NS1r" / "asks").glob("*.json"))[0]
        r = json.loads(f.read_text())
        r["resend_of"]["ask_id"] = "p1b999o99999"
        f.write_text(json.dumps(r))
        self.stops(root)
        self.stops(root, "--allow-partial")

    def test_a_record_without_a_field_resends_need_stops(self):
        root = self.copy_world("no_field")
        f = sorted((root / "s3raw" / "S3" / "asks").glob("*.json"))[0]
        r = json.loads(f.read_text())
        del r["resend_of"]
        f.write_text(json.dumps(r))
        self.stops(root, "--allow-partial")

    def test_a_row_of_another_pass_stops(self):
        root = self.copy_world("wrong_pass")
        f = sorted((root / "s3raw" / "S3" / "asks").glob("*.json"))[0]
        r = json.loads(f.read_text())
        r["pass"] = 2
        f.write_text(json.dumps(r))
        self.stops(root, "--allow-partial")

    def test_two_rows_for_one_ask_stop(self):
        root = self.copy_world("twice")
        d = root / "s3raw" / "S3" / "asks"
        f = sorted(d.glob("*.json"))[0]
        r = json.loads(f.read_text())
        r["ask_id"] = "p3b999o99999"
        (d / "p3b999o99999.json").write_text(json.dumps(r))
        self.stops(root, "--allow-partial")

    def test_numbers_that_differ_from_the_final_report_stop(self):
        root = self.copy_world("mismatch")
        final = json.loads((root / "final" / "report.json").read_text())
        final["small_groups"]["flags_on"]["against_main_same_versions"]["accuracy"]["diff"] += 0.01
        (root / "final" / "report.json").write_text(json.dumps(final))
        self.stops(root, "--allow-partial")
        # the message names the number that differs
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            run(root)
        self.assertIn("small_groups.flags_on.against_main_same_versions.accuracy.diff", buf.getvalue())

    def test_a_graded_row_missing_from_the_registered_run_stops(self):
        root = self.copy_world("row_missing")
        f = root / "graded" / "F2" / "graded.jsonl"
        lines = f.read_text().splitlines()
        keep = [ln for ln in lines if not (json.loads(ln)["group"] == "author" and json.loads(ln)["unit"] == fd.UNITS[5])]
        self.assertEqual(len(lines) - len(keep), 2)
        f.write_text("\n".join(keep) + "\n")
        self.stops(root, "--allow-partial")

    def test_no_daily_file_or_no_final_report_stops(self):
        root = self.copy_world("no_daily")
        (root / "daily.csv").unlink()
        self.stops(root)
        root = self.copy_world("no_final")
        (root / "final" / "report.json").unlink()
        self.stops(root)

    def test_without_the_desktop_prompt_report_and_plan_a3(self):
        root = self.copy_world("no_extras")
        (root / "dsp_report.json").unlink()
        shutil.rmtree(root / "a3raw")
        self.assertEqual(run(root), 0)
        da = output(root)["numbers"]["a_day_apart"]
        self.assertIn("not_computed", da["author_2_1_322_pass_3_against_passes_1_and_2"])
        self.assertIn("not_computed", da["desktop_prompt_e_against_main_on_2_1_321"])

    def test_a_daily_file_that_ends_too_early_is_a_warning(self):
        root = self.copy_world("old_daily")
        vals = {d: v for d, v in fd.daily_values().items() if d <= "2026-11-09"}
        fd.write_daily(root / "daily.csv", vals)
        self.assertEqual(run(root), 0)
        rep = output(root)
        self.assertTrue(any("download a newer copy" in w for w in rep["warnings"]))
        self.assertIsNone(rep["numbers"]["item_9"]["passes"]["1"]["difference"])
        self.assertIn("2026-11-11", rep["numbers"]["item_9"]["passes"]["1"]["why_not"])


# ------------------------------------------------------------------ constants against the project's own files

class Constants(unittest.TestCase):
    def test_against_the_files_that_sent_the_asks(self):
        arms = m.PROGRAM / "小组第三遍" / "arms.json"
        if not arms.is_file():
            self.skipTest("小组第三遍/arms.json is not here")
        groups = {g["group"]: g for g in json.loads(arms.read_text())["groups"]}
        self.assertEqual(tuple(groups["flags_on"]["versions"]), m.FLAGS_VERSIONS)
        self.assertEqual(groups["author"]["versions"], [m.AUTHOR_VERSION])
        nosent = m.PROGRAM / "去掉两句话组" / "nosent.py"
        if nosent.is_file():
            text = nosent.read_text()
            self.assertIn(f'VERSIONS = {m.NOSENT_VERSIONS!r}'.replace("'", '"'), text)
            self.assertIn(f'GROUP = "{m.NOSENT}"', text)
            self.assertIn('name = f"NS{number}"', text)
            self.assertIn('name = f"NS{number}r"', text)
        a3 = m.PROGRAM / "API第三遍" / "arms.json"
        if a3.is_file():
            g = {x["group"]: x for x in json.loads(a3.read_text())["groups"]}
            self.assertEqual(g["author"]["versions"], [m.A3_VERSION])
        self.assertEqual(m.SEED, 20261111)
        self.assertEqual(m.DRAWS, 10_000)
        self.assertEqual(fd.VERSIONS.index("2.1.299"), 17)
        self.assertEqual(fd.VERSIONS.index("2.1.308"), 26)
        self.assertEqual(len(fd.VERSIONS), 39)


class StandIns(unittest.TestCase):
    def test_stand_ins_agree_with_livenerf(self):
        repo = os.environ.get("LIVENERF_REPO")
        if not repo:
            self.skipTest("LIVENERF_REPO is not set")
        checks, claudecode = grade.import_author_graders(Path(repo))
        rational = m.xn.author_parsers(Path(repo))
        for i in range(78):
            t = fd.target(i)
            for kind in ("right", "wrong", "bad_form", "none"):
                ans = fd.answer_for(i, kind)
                text = f"x\n<answer>{ans}</answer>" if ans is not None else "x"
                self.assertEqual(fd.AUTHOR_CHECKS.extract_answer(text), checks.extract_answer(text))
                a = checks.extract_answer(text)
                scorer = fd.FAMILIES[i][1]
                fn = {"choice": "choice_score", "integer": "integer_score", "rational": "rational_score"}[scorer]
                self.assertEqual(getattr(fd.AUTHOR_CHECKS, fn)(a, t), getattr(checks, fn)(a, t))
                if a is not None:
                    self.assertEqual(fd.rational(a), rational(a))
        self.assertEqual(fd.CLAUDECODE.context_limit("ab", "cde"), claudecode.context_limit("ab", "cde"))

    def test_grader_from_a_settings_file_grades_as_the_stand_ins(self):
        """Grader.from_settings, the way the real run builds its grader: a settings file, an item file with its
        sha256, LiveNerf's own graders and parser. The whole planted world is run through it."""
        repo = os.environ.get("LIVENERF_REPO")
        if not repo:
            self.skipTest("LIVENERF_REPO is not set")
        if getattr(fd.items_mod, "stand_in", False):
            self.skipTest("ccversions/items.py and settings.py are not here (the public repository does not hold them)")
        import hashlib
        tmp = Path(tempfile.mkdtemp())
        try:
            inputs = fd.fake_inputs()
            doc = {"format": "ccversions-items-v1", "system_prompt": inputs.system_prompt, "items": [
                {"id": u.id, "input": u.text, "input_sha256": hashlib.sha256(u.text.encode()).hexdigest(),
                 "scorer": u.scorer, "target": u.target, "family": u.family} for u in inputs.items.values()]}
            (tmp / "items.json").write_text(json.dumps(doc))
            (tmp / "probes.json").write_text(json.dumps({"format": "ccversions-probes-v1", "probes": []}))
            sha = hashlib.sha256((tmp / "items.json").read_bytes()).hexdigest()
            paths = {k: str(tmp / k) for k in ("livenerf_cache", "versions_file", "experiment_root", "config_root",
                                               "home_dir", "workdir", "tmpdir", "config_dirs_file", "raw_dir")}
            paths.update(author_repo=repo, item_file=str(tmp / "items.json"), item_file_sha256=sha,
                         probe_file=str(tmp / "probes.json"))
            toml = "[paths]\n" + "".join(f'{k} = {json.dumps(v)}\n' for k, v in paths.items())
            toml += '[env]\nPATH = "/usr/bin"\nSHELL = "/bin/zsh"\nUSER = "x"\nLANG = "en_US.UTF-8"\nTZ = "UTC"\n'
            toml += '[login]\nmethod = "token"\ntoken_file = "none"\n'
            (tmp / "settings.toml").write_text(toml)
            real = m.Grader.from_settings(tmp / "settings.toml")
            stand_in = fd.fake_grader(m)
            recs = [r for rs in fd.raw_plans(fd.World()).values() for r in rs]
            a, b = real.grade(recs), stand_in.grade(recs)
            self.assertEqual(len(a), len(recs))
            for x, y in zip(a, b):
                self.assertEqual((x["outcome"], x["score"], x["answer"]), (y["outcome"], y["score"], y["answer"]))
                if x["outcome"] == "scored":
                    self.assertEqual(real.read(x), stand_in.read(y))
            self.assertEqual(sum(real.read(x) for x in a if x["outcome"] == "scored"),
                             sum(1 for x in a if x["outcome"] == "scored") - 6)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
