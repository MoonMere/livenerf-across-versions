"""Self-tests of desktop_prompt.py, on made-up graded rows and made-up raw records only. Nothing here reads
本机数据 (the registered run, the Desktop group, this group's records or any settings file there), no record
is graded with the author's code, no model is asked, and every output goes to a temporary folder.

    python -B -m unittest test_desktop_prompt -v

(from this folder).
"""

import json
import math
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import common  # noqa: E402
import desktop_prompt as DP  # noqa: E402
import desktop_vs_cli as dvc  # noqa: E402
from common import analyze  # noqa: E402

UTC = timezone.utc
ND = DP.NOT_DELIVERABLE[0]
U77 = [f"item:fake-{i:02d}" for i in range(77)]
U78 = U77 + [ND]                      # the item the Desktop group cannot ask is the last one
V = ["2.1.319", DP.VERSION, "2.1.322"]
LN2 = math.log(2)
BEFORE = datetime(2026, 11, 12, 20, 0, tzinfo=UTC)   # before 00:10 UTC on 13 November
AFTER = datetime(2026, 11, 13, 0, 10, tzinfo=UTC)

# the made-up world where every side is different from every other, so a wrong pairing shows:
# thinking + 1 = m(i) * 2 ** C[side], and the side answers item i right when i < N[side]
C = {"A": 0, "B": 1, "C": 3, "D": 6, "E": 10, "main": 15, "desktop": 21}
N = {"A": 10, "B": 20, "C": 33, "D": 50, "E": 58, "main": 67, "desktop": 70}


def m(i):
    return 1 + i % 5


def standard(x):
    if x == "desktop":  # right on its first 70 items and on the item it cannot ask (which must be left out)
        return lambda p, i, u: (float(i < N[x] or u == ND), m(i) * 2 ** C[x])
    return lambda p, i, u: (float(i < N[x]), m(i) * 2 ** C[x])


def row(group, version, p, unit, value, *, plan=None, ask_id=None, resend_of=None):
    """One graded row with the fields the comparisons read. value: (score, thinking + 1) or "error"."""
    err = value == "error"
    return {"plan": plan or f"P{p}", "ask_id": ask_id or f"{group}|{version}|{p}|{unit}", "group": group, "pass": p,
            "block": 0, "order": 0, "version": version, "mode": "stock_blocked", "effort": "high", "unit": unit,
            "repeat": 1, "warmup": False, "scored": True, "resend_of": resend_of,
            "outcome": "error" if err else "scored", "reason": "failed" if err else None,
            "score": None if err else value[0], "thinking_tokens": None if err else int(value[1]) - 1,
            "output_tokens": None if err else int(value[1]) + 200, "tool_calls": 0, "tool_rounds": 0, "num_turns": 1,
            "elapsed_seconds": 10.0, "started_at": "2026-11-13T02:00:00+00:00"}


def side(group, version, passes, fn, units=U78, plan=None):
    out = []
    for p in passes:
        for i, u in enumerate(units):
            v = fn(p, i, u)
            if v is not None:
                out.append(row(group, version, p, u, v, plan=(plan or (lambda q: f"P{q}"))(p)))
    return out


def world(fns=None, dsp_passes=None, main_fn=None, desk_fn=None):
    """(dsp rows, main rows, Desktop rows). fns: {letter: fn} in place of the standard ones."""
    fns = fns or {}
    dsp = []
    for x in DP.LETTERS:
        dsp += side(DP.GROUP_OF[x], DP.VERSION, (dsp_passes or {}).get(x, (1, 2, 3)), fns.get(x, standard(x)),
                    plan=lambda q: f"DSP{q}")
    main = []
    for v in V:
        main += side("main", v, (1, 2, 3), (main_fn or standard("main")) if v == DP.VERSION
                     else (lambda p, i, u: (float(i % 2 == 0), 300)))
    desk = side("desktop", DP.VERSION, (1, 2, 3), desk_fn or standard("desktop"))
    return dsp, main, desk


def acc_expected(a, b, units):
    """The accuracy difference of the standard world, counted straight from N."""
    ra = sum(1 for u in units if (U78.index(u) < N[a]) or (a == "desktop" and u == ND))
    rb = sum(1 for u in units if (U78.index(u) < N[b]) or (b == "desktop" and u == ND))
    return (ra - rb) / len(units)


def comp(rep, i):
    return rep["comparisons"][i - 1]


def write_jsonl(path, rows):
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


class Guarded(unittest.TestCase):
    """Points every default path of the run, the Desktop group and this group at empty temporary folders for
    the length of each test, so that no test can read 本机数据 even if it calls the program without options."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self._saved = (common.FORMAL_FINAL_REPORT, common.FORMAL_GRADED, common.DESKTOP_ASKS, common.OUT_DEFAULT,
                       common.SETTINGS_FILE, DP.DSP_SETTINGS)
        common.FORMAL_FINAL_REPORT = tmp / "no_final" / "report.json"
        common.FORMAL_GRADED = tmp / "no_graded"
        common.DESKTOP_ASKS = tmp / "no_desktop"
        common.OUT_DEFAULT = tmp / "no_out"
        common.SETTINGS_FILE = tmp / "no_settings.toml"
        DP.DSP_SETTINGS = tmp / "no_dsp" / "设置.toml"
        self.tmp = tmp

    def tearDown(self):
        (common.FORMAL_FINAL_REPORT, common.FORMAL_GRADED, common.DESKTOP_ASKS, common.OUT_DEFAULT,
         common.SETTINGS_FILE, DP.DSP_SETTINGS) = self._saved
        self._tmp.cleanup()


# ------------------------------------------------------------------------------------ constants

class ConstantsTests(unittest.TestCase):
    def test_the_constants_agree_with_dsp_py_and_dq_py(self):
        sys.path.insert(0, str(common.PROGRAM / "桌面版说明组"))
        import dsp  # only its constants. Importing it reads and writes nothing
        self.assertEqual(DP.GROUPS, dsp.GROUPS)
        self.assertEqual(DP.VERSION, dsp.VERSION)
        self.assertEqual(dsp.PASSES, 3)
        self.assertEqual(DP.PLANS, ("DSP1", "DSP1r", "DSP2", "DSP2r", "DSP3", "DSP3r"))
        self.assertEqual(DP.DSP_SETTINGS, dsp.DEFAULT_SETTINGS)
        self.assertEqual(DP.NOT_DELIVERABLE, ("item:gpqa-recWxGU8Q4YReJ1tb",))
        self.assertEqual(DP.DESKTOP_ITEMS, 77)


# ------------------------------------------------------------------------------------ pairing

class PairingTests(Guarded):
    def test_the_six_comparisons_pair_the_right_sides(self):
        rep = DP.analyse(*world(), V, shuffles=500, draws=500)
        want = {1: ("B", "A", U78), 2: ("D", "E", U78), 3: ("C", "B", U78), 4: ("D", "C", U78),
                5: ("E", "main", U78), 6: ("desktop", "D", U77)}
        names = {1: "B minus A", 2: "D minus E", 3: "C minus B", 4: "D minus C", 5: "E minus main on 2.1.321",
                 6: "Desktop minus D"}
        for i, (a, b, units) in want.items():
            c = comp(rep, i)
            self.assertEqual(c["name"], names[i])
            for metric in ("accuracy", "accuracy_bad_as_wrong"):
                r = c["metrics"][metric]
                self.assertEqual(r["items"], len(units), (i, metric))
                self.assertAlmostEqual(r["diff"], acc_expected(a, b, units), places=12, msg=(i, metric))
            t = c["metrics"]["log_thinking"]
            self.assertAlmostEqual(t["diff"], (C[a] - C[b]) * LN2, places=9, msg=i)
            self.assertAlmostEqual(t["diff_shown"], 2.0 ** (C[a] - C[b]) - 1, places=6, msg=i)
            self.assertLessEqual(t["range_95"][0], t["diff"] + 1e-9)
            self.assertGreaterEqual(t["range_95"][1], t["diff"] - 1e-9)
        # the six differences really are all different, so a swap of sides would have shown
        self.assertEqual(len({comp(rep, i)["metrics"]["accuracy"]["diff"] for i in want}), 6)
        self.assertEqual(len({comp(rep, i)["metrics"]["log_thinking"]["diff"] for i in want}), 6)

    def test_only_the_first_two_carry_a_wording_and_a_p(self):
        rep = DP.analyse(*world(), V, shuffles=500, draws=500)
        for i in (1, 2):
            c = comp(rep, i)
            self.assertEqual(c["write"], "wordings")
            self.assertIn("accuracy_wording", c)
            for r in c["metrics"].values():
                self.assertIn("p", r)
                self.assertIn("wording", r)
        for i in (3, 4, 5, 6):
            c = comp(rep, i)
            self.assertEqual(c["write"], "size")
            self.assertNotIn("accuracy_wording", c)
            for r in c["metrics"].values():
                self.assertNotIn("p", r, i)
                self.assertNotIn("wording", r, i)
                self.assertIn("range_95", r)
        # comparison 5 keeps its check for the reminder apart from what it reports
        for r in comp(rep, 5)["metrics"].values():
            self.assertIn("p", r["check_for_the_reminder"])
        text = DP.report_text(rep)
        self.assertEqual(text.count("Difference and range only (section 16)."), 4)
        self.assertEqual(text.count("Written in section 15's three wordings."), 2)

    def test_the_sixth_uses_only_the_desktop_groups_77_items(self):
        dsp, main, desk = world()
        self.assertIn(ND, {r["unit"] for r in desk})          # the made-up Desktop rows even hold it
        rep = DP.analyse(dsp, main, desk, V, shuffles=200, draws=200)
        c = comp(rep, 6)
        for r in c["metrics"].values():
            self.assertEqual(r["items"], 77)
            self.assertNotIn(ND, r["per_item"])
        self.assertAlmostEqual(c["metrics"]["accuracy"]["diff"], (70 - 50) / 77, places=12)
        # with the item it would have been 21/78: the 77 really decide the number
        self.assertNotAlmostEqual((70 + 1 - 50) / 78, (70 - 50) / 77, places=4)
        self.assertEqual(rep["desktop"]["by_pass"]["1"]["items"], 77)
        # the other five keep all 78
        for i in (1, 2, 3, 4, 5):
            self.assertEqual(comp(rep, i)["metrics"]["accuracy"]["items"], 78)

    def test_main_side_is_2_1_321_in_the_cells_that_count(self):
        dsp, main, desk = world()
        gone = next(r for r in main if r["version"] == "2.1.322" and r["pass"] == 1 and r["unit"] == U78[0])
        main.remove(gone)                                      # cell (item 0, pass 1) no longer counts
        rep = DP.analyse(dsp, main, desk, V, shuffles=200, draws=200)
        self.assertEqual(rep["main"]["by_pass"]["1"]["asks"], 77)
        self.assertEqual(rep["main"]["by_pass"]["2"]["asks"], 78)
        self.assertEqual(comp(rep, 5)["metrics"]["accuracy"]["b_asks_with_a_value"], 3 * 78 - 1)

    def test_a_resent_ask_takes_the_place_of_the_first(self):
        dsp, main, desk = world()
        first = next(r for r in dsp if r["group"] == "dsp_a" and r["pass"] == 1 and r["unit"] == U78[0])
        first.update(outcome="error", reason="failed", score=None, thinking_tokens=None)
        new = row("dsp_a", DP.VERSION, 1, U78[0], standard("A")(1, 0, U78[0]), plan="DSP1r", ask_id="r1b000o00001",
                  resend_of={"plan": first["plan"], "ask_id": first["ask_id"]})
        rep = DP.analyse(dsp + [new], main, desk, V, shuffles=200, draws=200)
        a1 = rep["ways"]["A"]["by_pass"]["1"]
        self.assertEqual((a1["asks"], a1["scored"]), (78, 78))
        self.assertAlmostEqual(comp(rep, 1)["metrics"]["accuracy_bad_as_wrong"]["diff"], acc_expected("B", "A", U78),
                               places=12)

    def test_the_same_numbers_as_the_existing_code(self):
        dsp, main, desk = world(fns={"E": lambda p, i, u: (float((i * 7 + p) % 3 != 0), 100 + 13 * ((i * p) % 11))})
        rep_main, _ = common.main_group(main, V)
        cli = DP.main_rows_on(rep_main, DP.VERSION)
        e = [r for r in dsp if r["group"] == "dsp_e"]
        for metric, effect, _ in common.METRICS:
            mine = DP.compare(e, cli, metric, effect, parts="against_mean", with_p=True, shuffles=3000, draws=3000)
            theirs = dvc.compare(e, cli, metric, effect, shuffles=3000, draws=3000)
            ref = analyze.paired(e, cli, metric, draws=3000)
            for k in ("diff", "p"):
                self.assertAlmostEqual(mine[k], theirs[k], places=12, msg=(metric, k))
            self.assertAlmostEqual(mine["diff"], ref["diff"], places=12)
            for j in (0, 1):
                self.assertAlmostEqual(mine["range_95"][j], theirs["range_95"][j], places=12)
                self.assertAlmostEqual(mine["range_95"][j], ref["range_95"][j], places=12)
            for p, x in theirs["rounds"].items():
                self.assertAlmostEqual(mine["passes"][p]["diff"], x["diff"], places=12)
            self.assertEqual(mine["same_sign_every_pass"], theirs["same_sign_every_round"])


# ------------------------------------------------------------------------------------ the three wordings

def b_against_a(score_b, think_b, score_a=None, think_a=None):
    """A world where only B and A matter: A right on even items with 100 * m(i) thinking + 1, B as given."""
    fa = lambda p, i, u: (score_a(p, i) if score_a else float(i % 2 == 0), think_a(p, i) if think_a else 100 * m(i))  # noqa: E731
    fb = lambda p, i, u: (score_b(p, i), think_b(p, i))  # noqa: E731
    return world(fns={"A": fa, "B": fb})


class WordingTests(Guarded):
    def wording(self, dsp_main_desk, which=1):
        rep = DP.analyse(*dsp_main_desk, V)
        return rep, comp(rep, which)

    def test_clear(self):
        # B right on 10 odd items A gets wrong, in every pass. B thinks twice as much on every item
        ten = {1, 3, 5, 7, 9, 11, 13, 15, 17, 19}
        _, c = self.wording(b_against_a(lambda p, i: float(i % 2 == 0 or i in ten), lambda p, i: 200 * m(i)))
        a, t = c["metrics"]["accuracy"], c["metrics"]["log_thinking"]
        self.assertAlmostEqual(a["diff"], 10 / 78, places=12)
        self.assertLess(a["p"], 0.01)          # only the flips that give all 10 the same sign reach it: 2 in 1,024
        self.assertTrue(a["big_enough"] and a["same_sign_every_pass"])
        self.assertEqual(a["passes_in_the_sign_check"], 3)
        self.assertEqual(a["wording_name"], "clear")
        self.assertAlmostEqual(t["diff"], LN2, places=12)
        self.assertEqual(t["wording_name"], "clear")
        self.assertEqual(c["accuracy_wording"]["wording_name"], "clear")
        self.assertEqual(c["thinking_wording"]["wording_name"], "clear")

    def test_points_one_way_by_p(self):
        # 6 items: p near 2 in 64, between 1 and 5 per cent. Thinking 4 times as much on 6 items: 11 per cent
        six = {1, 3, 5, 7, 9, 11}
        _, c = self.wording(b_against_a(lambda p, i: float(i % 2 == 0 or i in six),
                                        lambda p, i: 100 * m(i) * (4 if i in six else 1)))
        for k in ("accuracy", "log_thinking"):
            r = c["metrics"][k]
            self.assertTrue(0.01 <= r["p"] < 0.05, (k, r["p"]))
            self.assertTrue(r["big_enough"] and r["same_sign_every_pass"], k)
            self.assertEqual(r["wording_name"], "points one way", k)
        self.assertAlmostEqual(c["metrics"]["log_thinking"]["diff_shown"], math.exp(6 * math.log(4) / 78) - 1, places=12)
        self.assertEqual(c["accuracy_wording"]["wording_name"], "points one way")
        self.assertIn("Points this way, short of the line we call clear.", DP.report_text(DP.analyse(
            *b_against_a(lambda p, i: float(i % 2 == 0 or i in six), lambda p, i: 100 * m(i)), V)))

    def test_one_pass_the_other_way_is_short_of_clear(self):
        # 30 odd items: B right in passes 1 and 2, wrong in pass 3. 5 even items: in pass 3 B wrong and A right
        s1 = set(range(1, 61, 2))
        s2 = {0, 2, 4, 6, 8}
        score_b = lambda p, i: float((i in s1 and p < 3) or (i % 2 == 0 and not (p == 3 and i in s2)))  # noqa: E731
        _, c = self.wording(b_against_a(score_b, lambda p, i: 100 * m(i)))
        a = c["metrics"]["accuracy"]
        self.assertAlmostEqual(a["diff"], (30 * 2 / 3 - 5 / 3) / 78, places=12)
        self.assertLess(a["p"], 0.01)
        self.assertTrue(a["big_enough"])
        self.assertAlmostEqual(a["passes"]["3"]["diff"], -5 / 78, places=12)
        self.assertTrue(a["passes"]["3"]["counts_for_sign"])
        self.assertFalse(a["same_sign_every_pass"])
        self.assertEqual(a["wording_name"], "points one way")

    def test_otherwise_when_the_same(self):
        rep, c = self.wording(b_against_a(lambda p, i: float(i % 2 == 0), lambda p, i: 100 * m(i)))
        for r in c["metrics"].values():
            self.assertAlmostEqual(r["diff"], 0.0, places=12)
            self.assertEqual(r["p"], 1.0)
            self.assertEqual(r["wording_name"], "otherwise")
            self.assertAlmostEqual(r["not_larger_than"], 0.0, places=12)
        self.assertIn("Accuracy: no difference larger than 0.0 points was seen.", DP.report_text(rep))

    def test_the_size_line_for_thinking(self):
        # the same 5 per cent more on every item: p as small as it gets, the size short of 10 per cent
        _, c = self.wording(b_against_a(lambda p, i: float(i % 2 == 0), lambda p, i: 105 * m(i)))
        t = c["metrics"]["log_thinking"]
        self.assertAlmostEqual(t["diff_shown"], 0.05, places=12)
        self.assertEqual(t["p"], 1 / (1 + common.SHUFFLES))
        self.assertFalse(t["big_enough"])
        self.assertEqual(t["wording_name"], "otherwise")
        # 12 per cent more is clear
        _, c = self.wording(b_against_a(lambda p, i: float(i % 2 == 0), lambda p, i: 112 * m(i)))
        self.assertEqual(c["metrics"]["log_thinking"]["wording_name"], "clear")

    def test_the_size_line_for_accuracy(self):
        # the made-up p of 2 items can never be under 5 per cent, so look at the line itself: 3 points
        self.assertTrue(common.big_enough(0.03, "diff"))
        self.assertFalse(common.big_enough(0.0299, "diff"))
        self.assertTrue(common.big_enough(math.log(1.1), "ratio"))
        self.assertFalse(common.big_enough(math.log(1.0999), "ratio"))

    def test_the_two_ways_of_counting_must_agree(self):
        # B right on 10 odd items A gets wrong, and B has errors on 10 even items A gets right:
        # errors left out it is clear, errors counted as wrong it is 0, so accuracy says otherwise
        ten, lost = set(range(1, 21, 2)), set(range(0, 20, 2))
        fb = lambda p, i, u: "error" if i in lost else (float(i % 2 == 0 or i in ten), 100 * m(i))  # noqa: E731
        rep = DP.analyse(*world(fns={"A": lambda p, i, u: (float(i % 2 == 0), 100 * m(i)), "B": fb}), V)
        c = comp(rep, 1)
        self.assertEqual(c["metrics"]["accuracy"]["wording_name"], "clear")
        self.assertAlmostEqual(c["metrics"]["accuracy_bad_as_wrong"]["diff"], 0.0, places=12)
        self.assertEqual(c["accuracy_wording"]["wording_name"], "otherwise")
        self.assertEqual(c["accuracy_wording"]["errors_and_voids_left_out"], "clear")

    def test_the_second_comparison_is_worded_too(self):
        rep = DP.analyse(*world(fns={"D": lambda p, i, u: (float(i < 58), 2 ** 11 * m(i))}), V)
        c = comp(rep, 2)                                       # D thinks twice as much as E, same answers
        self.assertAlmostEqual(c["metrics"]["log_thinking"]["diff"], LN2, places=9)
        self.assertEqual(c["thinking_wording"]["wording_name"], "clear")
        self.assertEqual(c["accuracy_wording"]["wording_name"], "otherwise")
        text = DP.report_text(rep)
        self.assertIn("Thinking: Clear by section 15's line", text)
        self.assertIn("D is the prompt the Desktop group's sessions saved", text)


# ------------------------------------------------------------------------------------ the reminder

class ReminderTests(Guarded):
    def test_no_reminder_when_e_matches_main(self):
        rep = DP.analyse(*world(main_fn=standard("E")), V, shuffles=2000, draws=500)
        self.assertFalse(rep["reminder"]["applies"])
        self.assertTrue(comp(rep, 5)["reminder_check"]["computable"])
        for c in rep["comparisons"]:
            self.assertNotIn("reminder", c)
        self.assertNotIn("Reminder (section 16)", DP.report_text(rep))

    def test_a_clear_thinking_difference_puts_it_on_five_and_six(self):
        # E thinks twice as much as main on every item, the answers are the same
        main_fn = lambda p, i, u: (float(i < N["E"]), m(i) * 2 ** (C["E"] - 1))  # noqa: E731
        rep = DP.analyse(*world(main_fn=main_fn), V)
        self.assertTrue(rep["reminder"]["applies"])
        self.assertEqual(rep["reminder"]["from"], ["thinking"])
        self.assertEqual(rep["reminder"]["on_comparisons"], [5, 6])
        for c in rep["comparisons"]:
            self.assertEqual("reminder" in c, c["id"] in (5, 6), c["id"])
        text = DP.report_text(rep)
        self.assertEqual(text.count("Reminder (section 16)"), 2)
        self.assertIn("(thinking)", text)
        # what comparison 5 reports stays the difference and the range
        self.assertNotIn("p", comp(rep, 5)["metrics"]["log_thinking"])

    def test_a_clear_accuracy_difference_both_ways(self):
        # main right on 12 more items than E, in every pass
        main_fn = lambda p, i, u: (float(i < N["E"] + 12), m(i) * 2 ** C["E"])  # noqa: E731
        rep = DP.analyse(*world(main_fn=main_fn), V)
        self.assertEqual(rep["reminder"]["from"], ["accuracy"])
        self.assertEqual(comp(rep, 5)["reminder_check"]["accuracy_both_ways"], "clear")

    def test_points_one_way_is_not_enough(self):
        main_fn = lambda p, i, u: (float(i < N["E"] + 6), m(i) * 2 ** C["E"])  # noqa: E731
        rep = DP.analyse(*world(main_fn=main_fn), V)
        chk = comp(rep, 5)["metrics"]["accuracy"]["check_for_the_reminder"]
        self.assertTrue(0.01 <= chk["p"] < 0.05)
        self.assertEqual(chk["wording_name"], "points one way")
        self.assertFalse(rep["reminder"]["applies"])

    def test_no_main_on_2_1_321(self):
        dsp, main, desk = world()
        main = [r for r in main if r["version"] != DP.VERSION]
        rep = DP.analyse(dsp, main, desk, ["2.1.319", "2.1.322"], shuffles=200, draws=200)
        self.assertIn("not among main's versions", rep["main"]["why_not_computable"])
        self.assertFalse(comp(rep, 5)["reminder_check"]["computable"])
        self.assertTrue(any("whether the reminder applies is not known" in w for w in rep["warnings"]))
        DP.report_text(rep)


# ------------------------------------------------------------------------------------ passes that are short

class PartialTests(Guarded):
    def test_a_way_with_one_pass_missing(self):
        # D has passes 1 and 2 only. E thinks more in pass 3 (exponent 13 there, 10 in passes 1 and 2)
        e = lambda p, i, u: (float(i < N["E"]), m(i) * 2 ** (13 if p == 3 else 10))  # noqa: E731
        rep = DP.analyse(*world(fns={"E": e}, dsp_passes={"D": (1, 2)}), V)
        d = rep["ways"]["D"]
        self.assertEqual((d["passes_with_asks"], d["complete_passes"]), (2, 2))
        self.assertEqual(sorted(d["by_pass"]), ["1", "2"])
        self.assertEqual(rep["ways"]["E"]["complete_passes"], 3)
        c = comp(rep, 2)
        t = c["metrics"]["log_thinking"]
        self.assertEqual((t["a_passes"], t["b_passes"]), ([1, 2], [1, 2, 3]))
        self.assertAlmostEqual(t["diff"], (6 - (10 + 10 + 13) / 3) * LN2, places=9)   # D's 2 passes, E's 3
        self.assertEqual(t["passes"]["3"]["items"], 0)
        self.assertFalse(t["passes"]["3"]["counts_for_sign"])
        self.assertEqual(t["passes_in_the_sign_check"], 2)
        text = DP.report_text(rep)
        self.assertIn("- D (dsp_d): 2 passes with asks, 2 of them with all 78 items. Asks by pass: 1: 78, 2: 78.", text)
        self.assertIn("- E (dsp_e): 3 passes with asks, 3 of them with all 78 items.", text)
        self.assertTrue(any("D has 2 complete" in w for w in rep["warnings"]))
        self.assertIn("WARNING: ways with fewer than three complete passes", text)
        # the comparisons that do not involve D keep three passes on both sides
        self.assertEqual(comp(rep, 1)["metrics"]["log_thinking"]["a_passes"], [1, 2, 3])

    def test_stopped_part_way_through_pass_three(self):
        # pass 3 stopped after 30 items for every way. B thinks 4 times as much in pass 3 as in passes 1 and 2
        sent3 = set(sorted(range(78), key=lambda i: (i * 37) % 78)[:30])   # 30 items spread over the list

        def cut(x, mult3=1):
            def fn(p, i, u):
                if p == 3 and i not in sent3:
                    return None
                return (float(i < N[x]), m(i) * 2 ** C[x] * (mult3 if p == 3 else 1))
            return fn
        fns = {x: cut(x) for x in DP.LETTERS}
        fns["B"] = cut("B", 4)
        rep = DP.analyse(*world(fns=fns), V)
        for x in DP.LETTERS:
            w = rep["ways"][x]
            self.assertEqual(w["by_pass"]["3"]["asks"], 30, x)
            self.assertEqual((w["passes_with_asks"], w["complete_passes"]), (3, 2), x)
        # expected B minus A, item by item: the 30 items of pass 3 have three passes on both sides
        want = sum(((C["B"] - C["A"]) * LN2 + (math.log(4) / 3 if i in sent3 else 0.0)) for i in range(78)) / 78
        t = comp(rep, 1)["metrics"]["log_thinking"]
        self.assertAlmostEqual(t["diff"], want, places=9)
        self.assertEqual(t["passes"]["3"]["items"], 30)
        self.assertFalse(t["passes"]["3"]["counts_for_sign"])       # 30 of 78 is under half
        self.assertIn("why_not_in_the_sign_check", t["passes"]["3"])
        self.assertTrue(t["passes"]["1"]["counts_for_sign"] and t["passes"]["2"]["counts_for_sign"])
        self.assertIn("2 of them with all 78 items. Asks by pass: 1: 78, 2: 78, 3: 30.", DP.report_text(rep))

    def test_nothing_sent_for_one_way(self):
        rep = DP.analyse(*world(dsp_passes={"C": ()}), V, shuffles=200, draws=200)
        self.assertEqual(rep["ways"]["C"]["passes_with_asks"], 0)
        for i in (3, 4):
            for r in comp(rep, i)["metrics"].values():
                self.assertFalse(r["computable"])
        self.assertIn("not computable: no item that both sides have", DP.report_text(rep))


# ------------------------------------------------------------------------------------ reading the records

class RecordsTests(Guarded):
    def raw(self, plan, n, group, unit, **kw):
        return {"ask_id": f"{plan}-{n}", "plan": plan, "pass": int(plan[3]) if plan[3].isdigit() else 1,
                "group": group, "unit": unit, "version": DP.VERSION, "scored": True, "warmup": False, **kw}

    def test_only_the_three_passes_and_their_resends_are_read(self):
        raw = self.tmp / "原始记录"
        recs = {"DSP1": [self.raw("DSP1", 1, "dsp_a", U78[0]), self.raw("DSP1", 2, "dsp_e", U78[1])],
                "DSP1r": [self.raw("DSP1r", 1, "dsp_a", U78[0], resend_of={"plan": "DSP1", "ask_id": "DSP1-1"})],
                "DSP3": [self.raw("DSP3", 1, "dsp_b", U78[2]),
                         self.raw("DSP3", 2, "dsp_b", "probe:author-ok", scored=False),
                         self.raw("DSP3", 3, None, U78[3]),
                         self.raw("DSP3", 4, "dsp_c", U78[4], version="2.1.322")],
                "DSPS": [self.raw("DSPS", 1, "dsp_a", U78[5])],
                "DSPT_1": [self.raw("DSPT_1", 1, "dsp_a", "probe:author-ok", scored=False)],
                "DSPW_1": [self.raw("DSPW_1", 1, "dsp_d", "probe:author-ok", warmup=True, scored=False)]}
        for plan, rs in recs.items():
            (raw / plan / "asks").mkdir(parents=True)
            for r in rs:
                (raw / plan / "asks" / f"{r['ask_id']}.json").write_text(json.dumps(r))
        records, found = DP.load_dsp_records(raw)
        self.assertEqual(found, {"DSP1": 2, "DSP1r": 1, "DSP2": None, "DSP2r": None, "DSP3": 4, "DSP3r": None})
        self.assertEqual({r["plan"] for r in records}, {"DSP1", "DSP1r", "DSP3"})
        kept, left = DP.pick_raw(records)
        self.assertEqual(sorted(r["ask_id"] for r in kept), ["DSP1-1", "DSP1-2", "DSP1r-1", "DSP3-1"])
        whys = sorted(x["why"].split(" ")[0] for x in left)
        self.assertEqual(whys, ["group", "unit", "version"])

    def test_the_log_of_dsp_py(self):
        f = self.tmp / "g" / "设置.toml"
        f.parent.mkdir()
        self.assertIsNone(DP.dsp_log_says_all_sent(f))
        (f.parent / "state.json").write_text(json.dumps({"log": [{"what": "plan_made"}, {"what": "stopped"}]}))
        self.assertFalse(DP.dsp_log_says_all_sent(f))
        (f.parent / "state.json").write_text(json.dumps({"log": [{"what": "plan_made"}, {"what": "all_passes_sent"}]}))
        self.assertTrue(DP.dsp_log_says_all_sent(f))

    def test_a_row_twice_is_flagged(self):
        dsp, main, desk = world()
        dsp.append(dict(next(r for r in dsp if r["group"] == "dsp_c"), ask_id="again"))
        rep = DP.analyse(dsp, main, desk, V, shuffles=200, draws=200)
        self.assertTrue(any("more than one row" in w for w in rep["warnings"]))


# ------------------------------------------------------------------------------------ the program itself

class ProgramTests(Guarded):
    def files(self, desk_rows=None):
        dsp, main, desk = world()
        paths = {}
        for name, rows in (("main", main), ("dsp", dsp), ("desk", desk if desk_rows is None else desk_rows)):
            paths[name] = self.tmp / f"{name}.jsonl"
            write_jsonl(paths[name], rows)
        paths["versions"] = self.tmp / "versions.json"
        paths["versions"].write_text(json.dumps({"versions": V}))
        return paths

    def args(self, p, out):
        return ["--graded", str(p["main"]), "--dsp-graded", str(p["dsp"]), "--desktop-graded", str(p["desk"]),
                "--versions-file", str(p["versions"]), "--out", str(out), "--shuffles", "300", "--draws", "200"]

    def test_it_writes_both_files(self):
        p = self.files()
        out = self.tmp / "out"
        self.assertEqual(DP.main(self.args(p, out), now=BEFORE), 0)   # Desktop round 3 is in: no need to wait
        for name in ("report.json", "report.md"):
            self.assertTrue((out / "desktop_prompt" / name).is_file(), name)
        self.assertFalse((out / "desktop_prompt" / "graded").exists())  # graded rows were given, nothing graded here
        rep = json.loads((out / "desktop_prompt" / "report.json").read_text())
        self.assertEqual([c["id"] for c in rep["comparisons"]], [1, 2, 3, 4, 5, 6])
        self.assertEqual(rep["ways"]["A"]["complete_passes"], 3)
        self.assertIn("## 6. Desktop minus D", (out / "desktop_prompt" / "report.md").read_text())

    def test_it_waits_for_the_desktop_round_three_or_the_time(self):
        dsp, main, desk = world()
        part = [r for r in desk if r["pass"] < 3 or U78.index(r["unit"]) < 10]
        p = self.files(desk_rows=part)
        out = self.tmp / "out"
        self.assertEqual(DP.main(self.args(p, out), now=BEFORE), 2)
        self.assertFalse((out / "desktop_prompt").exists())
        self.assertEqual(DP.main(self.args(p, out), now=AFTER - timedelta(seconds=1)), 2)
        self.assertEqual(DP.main(self.args(p, out), now=AFTER), 0)
        rep = json.loads((out / "desktop_prompt" / "report.json").read_text())
        self.assertEqual(rep["desktop"]["by_pass"]["3"]["asks"], 10)
        # Desktop with two rounds only and the time passed: it runs on two rounds
        p = self.files(desk_rows=[r for r in desk if r["pass"] < 3])
        self.assertEqual(DP.main(self.args(p, out), now=BEFORE), 2)
        self.assertEqual(DP.main(self.args(p, out), now=AFTER), 0)

    def test_it_waits_for_the_registered_run(self):
        p = self.files()
        args = self.args(p, self.tmp / "out")
        i = args.index("--graded")
        del args[i:i + 2]
        self.assertEqual(DP.main(args, now=AFTER), 2)          # no final report: the run's rows are not read

    def test_a_desktop_round_three_part_way_stops_it_before_any_grading(self):
        asks = self.tmp / "asks"
        asks.mkdir()
        n = 0
        for rnd, units in ((1, U77), (2, U77), (3, U77[:10])):
            for u in units:
                n += 1
                (asks / f"d{rnd}q{n:03d}.json").write_text(json.dumps(
                    {"ask_id": f"d{rnd}q{n:03d}", "order": n, "group": "desktop", "pass": rnd, "unit": u,
                     "version": DP.VERSION, "status": "done", "text_ok": True, "effort_ok": True}))
        p = self.files()
        args = self.args(p, self.tmp / "out")
        i = args.index("--desktop-graded")
        args[i:i + 2] = ["--desktop-asks", str(asks)]
        self.assertEqual(DP.main(args, now=AFTER), 2)                          # round 3 has 10 of 77
        self.assertEqual(DP.main(args + ["--allow-partial-round3"], now=BEFORE), 2)  # and the time has not come


if __name__ == "__main__":
    unittest.main()
