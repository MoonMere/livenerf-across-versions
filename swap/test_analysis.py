"""Tests of analysis.py on made-up rows. No record of any run is read. What a test writes goes into a
temporary folder of its own, removed at the end.

    python -B -m unittest test_analysis
"""

import contextlib
import io
import json
import math
import random
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import analysis as an

OLD, NEW = an.OLD, an.NEW
LN10 = math.log(10)
NO_KEYS = {"sound": [], "also_accepted": {}, "replaced": {}, "left_out": []}


def row(version, way, unit, pass_, tokens=None, score=1.0, outcome="scored", set_="w1", **more):
    """One graded row. Its folder is the folder of its set and version."""
    scored = outcome == "scored"
    unit = unit if unit.startswith("item:") else "item:" + unit
    return {"ask_id": f"p{pass_}-{unit}-{version}-{way}", "group": way, "version": version, "unit": unit,
            "pass": pass_, "outcome": outcome, "thinking_tokens": tokens if scored else None,
            "score": score if scored else None, "tool_calls": 0, "answer": None,
            "config_dir": f"/cfg/root/{version}/{set_}", "swap": {"set": set_}, "options": {"config_set": set_},
            "first_request_input_tokens": 5000, **more}


def make_rows(factor=None, passes=(1, 2, 3, 4), units=8, seed=0, spread=0.5, acc=None, sets=3,
              folder_factor=None, qfactor=None, ways=an.DEFAULT_WAYS) -> list[dict]:
    """One scored ask per pass, question and cell. All asks of a question in a pass use set w<k>, with k
    turning with the pass and the question. Thinking tokens: 200 times (question number + 1), times
    factor[cell], times qfactor[(version, way, question number)], times folder_factor[folder] (each 1
    when not given), times exp(a normal draw with sd `spread`). The ask is right with chance acc[cell]
    (0.5 when not given)."""
    rng = random.Random(seed)
    out = []
    for p in passes:
        for u in range(units):
            s = f"w{(p + u) % sets + 1}"
            for v, w in an.cells_of(ways):
                t = 200 * (u + 1) * (factor or {}).get((v, w), 1.0) * (qfactor or {}).get((v, w, u), 1.0)
                t *= (folder_factor or {}).get(f"/cfg/root/{v}/{s}", 1.0)
                t *= math.exp(rng.gauss(0, spread)) if spread else 1.0
                out.append(row(v, w, f"q{u}", p, int(round(t)), float(rng.random() < (acc or {}).get((v, w), 0.5)),
                               set_=s, first_request_input_tokens=4000 + u))
    return out


def tests_of(rows, line=None, ways=an.DEFAULT_WAYS):
    slots, cells, have, _ = an.counted(rows, ways)
    universe = sorted({u for _, u in have})
    return (an.comparison(slots, cells, an.TEST_1, an.lthink, "thinking", universe, line=line),
            an.comparison(slots, cells, an.TEST_2, an.lthink, "thinking", universe, line=line))


def pairs_of(rows, layers, ways=an.DEFAULT_WAYS):
    slots, cells, _, _ = an.counted(rows, ways)
    return len(an.make_pairs(an.slot_values(slots, an.lthink), cells, layers))


def tok(k: int) -> int:
    """10**k - 1 tokens: the value ln(tokens + 1) is k ln 10."""
    return 10 ** k - 1


# The hand-worked example. Values in units of ln 10 by (question, pass), cells in the order of
# an.FOUR (2.1.316 sw_o, 2.1.316 sw_w, 2.1.317 sw_o, 2.1.317 sw_w). None is an ask that was voided.
# Pass 1 uses set w1, pass 2 set w2.
HAND = {("q0", 1): (2, 1, 3, 1), ("q0", 2): (3, 2, 3, 3),
        ("q1", 1): (2, 2, 4, 3), ("q1", 2): (2, 1, 2, None)}


def hand_rows() -> list[dict]:
    out = []
    for (u, p), ks in HAND.items():
        for (v, w), k in zip(an.FOUR, ks):
            wrong = (u, p, v, w) == ("q0", 1, NEW, "sw_w")  # the one wrong answer
            s = f"w{p}"
            out.append(row(v, w, u, p, outcome="void", set_=s) if k is None else
                       row(v, w, u, p, tok(k), 0.0 if wrong else 1.0, set_=s))
    return out


class HandWorkedTest(unittest.TestCase):
    """Worked by hand from the table HAND.

    Test 1 (sw_w minus sw_o, a layer per program):
      q0  2.1.316: 1-2 = -1, 2-3 = -1, mean -1.   2.1.317: 1-3 = -2, 3-3 = 0, mean -1.   figure -1
      q1  2.1.316: 2-2 = 0, 1-2 = -1, mean -0.5.  2.1.317: 3-4 = -1 (pass 2 voided), mean -1.  figure -0.75
      T = -0.875 (pooling the 7 pairs instead would give -6/7)
    Test 2 (2.1.317 minus 2.1.316, a layer per way):
      q0  sw_o: 3-2 = 1, 3-3 = 0, mean 0.5.  sw_w: 1-1 = 0, 3-2 = 1, mean 0.5.  figure 0.5
      q1  sw_o: 4-2 = 2, 2-2 = 0, mean 1.    sw_w: 3-2 = 1 (pass 2 voided), mean 1.  figure 1
      T = 0.75
    The two cells with their own sentences (2.1.317 sw_w minus 2.1.316 sw_o): q0 1-2 = -1 and 3-3 = 0,
      figure -0.5. q1 3-2 = 1 (pass 2 voided), figure 1. T = 0.25
    Split, on the question and pass cells with all four values (all but q1 in pass 2):
      q0  two cells -0.5 = test 1 -1 + test 2 0.5
      q1  two cells 1 = test 1 (0 + -1) / 2 = -0.5 + test 2 (2 + 1) / 2 = 1.5
      T: 0.25 = -0.75 + 1.0. Shares -3 and 4
    Accuracy of test 1: only 2.1.317 sw_w on q0 in pass 1 is wrong: q0 (0 + (-1 + 0) / 2) / 2 = -0.25, q1 0,
      T = -0.125, -12.5 points
    The cell 2.1.316 sw_o: q0 (2 + 3) / 2 = 2.5, q1 (2 + 2) / 2 = 2, mean 2.25: geometric mean 10**2.25 - 1
    The cell 2.1.317 sw_w: q0 (1 + 3) / 2 = 2, q1 3 (one scored ask), mean 2.5: geometric mean 10**2.5 - 1
    Set w1 (pass 1): test 1 q0 (-1 + -2) / 2 = -1.5, q1 (0 + -1) / 2 = -0.5, T -1. Test 2 q0 (1 + 0) / 2,
      q1 (2 + 1) / 2, T 1. 8 scored asks.
    Set w2 (pass 2): test 1 q0 (-1 + 0) / 2 = -0.5, q1 has no pair on 2.1.317 and is left out, T -0.5.
      Test 2 q0 (0 + 1) / 2 = 0.5, q1 left out, T 0.5. 7 scored asks.
    """

    @classmethod
    def setUpClass(cls):
        cls.rep = an.report(hand_rows(), keys=NO_KEYS)

    def test_test_1(self):
        t1 = self.rep["test_1_sentences_thinking"]
        self.assertAlmostEqual(t1["T"], -0.875 * LN10)
        self.assertAlmostEqual(t1["question_figures"]["item:q0"], -1 * LN10)
        self.assertAlmostEqual(t1["question_figures"]["item:q1"], -0.75 * LN10)
        self.assertAlmostEqual(t1["exp_T_minus_1"], 10 ** -0.875 - 1)
        self.assertEqual((t1["questions"], t1["pairs"], t1["pairs_by_layer"]), (2, 7, {OLD: 4, NEW: 3}))
        self.assertEqual(t1["line"], an.LINE_CONTINUE)

    def test_test_2(self):
        t2 = self.rep["test_2_program_thinking"]
        self.assertAlmostEqual(t2["T"], 0.75 * LN10)
        self.assertAlmostEqual(t2["question_figures"]["item:q0"], 0.5 * LN10)
        self.assertAlmostEqual(t2["question_figures"]["item:q1"], 1 * LN10)
        self.assertAlmostEqual(t2["exp_T_minus_1"], 10 ** 0.75 - 1)
        self.assertEqual(t2["pairs_by_layer"], {"sw_o": 4, "sw_w": 3})

    def test_own_sentences_two_cells(self):
        own = self.rep["reported_no_declaration"]["own_sentences_two_cells"]["thinking"]
        self.assertAlmostEqual(own["T"], 0.25 * LN10)
        self.assertEqual((own["pairs"], own["declared"]), (3, None))
        self.assertAlmostEqual(self.rep["reported_no_declaration"]["test_1_on_2.1.317_alone"]["thinking"]["T"], -1.0 * LN10)

    def test_split(self):
        d = self.rep["decomposition"]["thinking"]
        self.assertEqual((d["questions"], d["question_passes"]), (2, 3))
        self.assertAlmostEqual(d["T"]["own"], 0.25 * LN10)
        self.assertAlmostEqual(d["T"]["test_1"], -0.75 * LN10)
        self.assertAlmostEqual(d["T"]["test_2"], 1.0 * LN10)
        self.assertAlmostEqual(d["share_of_test_1"], -3.0)
        self.assertAlmostEqual(d["share_of_test_2"], 4.0)

    def test_accuracy(self):
        a = self.rep["test_1_sentences_accuracy_no_declaration"]
        self.assertAlmostEqual(a["points"], -12.5)
        self.assertIsNone(a["declared"])

    def test_cells(self):
        c = self.rep["cell_rows"]
        self.assertEqual(self.rep["cells"], [f"{OLD} sw_o", f"{OLD} sw_w", f"{NEW} sw_o", f"{NEW} sw_w"])
        self.assertAlmostEqual(c[f"{OLD} sw_o"]["thinking_geometric_mean_tokens"], 10 ** 2.25 - 1, places=6)
        self.assertAlmostEqual(c[f"{NEW} sw_w"]["thinking_geometric_mean_tokens"], 10 ** 2.5 - 1, places=6)
        self.assertEqual(c[f"{NEW} sw_w"]["records_by_outcome"], {"scored": 3, "void": 1})
        self.assertEqual(c[f"{NEW} sw_w"]["first_request_input_tokens"], {"5000": 3})
        self.assertAlmostEqual(c[f"{NEW} sw_w"]["accuracy_per_cent"], 75.0)  # q0 (0 + 1) / 2, q1 1

    def test_sets(self):
        s = self.rep["sets"]
        self.assertEqual(sorted(s), ["w1", "w2"])
        self.assertEqual((s["w1"]["asks"], s["w2"]["asks"]), (8, 7))
        self.assertAlmostEqual(s["w1"]["test_1_thinking"]["T"], -1.0 * LN10)
        self.assertAlmostEqual(s["w1"]["test_2_thinking"]["T"], 1.0 * LN10)
        self.assertAlmostEqual(s["w2"]["test_1_thinking"]["T"], -0.5 * LN10)
        self.assertAlmostEqual(s["w2"]["test_2_thinking"]["T"], 0.5 * LN10)
        self.assertIn("item:q1", s["w2"]["test_1_thinking"]["questions_left_out"])
        self.assertIsNone(s["w1"]["test_1_thinking"]["declared"])

    def test_question_rows(self):
        q = self.rep["questions"]["item:q1"]
        self.assertAlmostEqual(q["test_1_thinking"], -0.75 * LN10)
        self.assertAlmostEqual(q["test_2_thinking"], 1 * LN10)
        self.assertAlmostEqual(q["own_sentences_two_cells_thinking"], 1 * LN10)
        self.assertEqual(q["cells"][f"{NEW} sw_w"], {"zero_thinking_asks": 0, "scored_asks": 1})


class ZeroThinkingTest(unittest.TestCase):
    def test_zero_thinking_asks_by_question_and_cell_counted_by_hand(self):
        # q0: 2.1.316 sw_o 0 and 0, sw_w 0 and 5, 2.1.317 sw_o 5 and 5, sw_w 0 and a void
        # q1: every ask 7, no zero
        tokens = {(OLD, "sw_o"): (0, 0), (OLD, "sw_w"): (0, 5), (NEW, "sw_o"): (5, 5), (NEW, "sw_w"): (0, None)}
        rows = []
        for (v, w), ks in tokens.items():
            for p, k in zip((1, 2), ks):
                rows.append(row(v, w, "q0", p, outcome="void") if k is None else row(v, w, "q0", p, k))
                rows.append(row(v, w, "q1", p, 7))
        q = an.report(rows, keys=NO_KEYS)["questions"]
        self.assertEqual({c: (x["zero_thinking_asks"], x["scored_asks"]) for c, x in q["item:q0"]["cells"].items()},
                         {f"{OLD} sw_o": (2, 2), f"{OLD} sw_w": (1, 2), f"{NEW} sw_o": (0, 2), f"{NEW} sw_w": (1, 1)})
        self.assertEqual({x["zero_thinking_asks"] for x in q["item:q1"]["cells"].values()}, {0})


class SignFlipTest(unittest.TestCase):
    def test_three_equal_pairs(self):
        # all three D equal: a draw is as far from zero only when all signs agree, chance 2 / 8
        c = an.compare([("item:a", "x", 1.0)] * 3, ["x"], "thinking")
        self.assertAlmostEqual(c["p_by_pairs"], 0.25, delta=0.02)
        self.assertEqual(c["p_by_pairs"], (c["draws_at_least_as_far_by_pairs"] + 1) / 10_001)

    def test_four_equal_questions(self):
        c = an.compare([(f"item:{u}", "x", 2.0) for u in "abcd"], ["x"], "thinking")
        self.assertAlmostEqual(c["p_by_questions"], 0.125, delta=0.015)
        self.assertEqual(c["range"], [2.0, 2.0])
        self.assertFalse(c["range_crosses_zero"])

    def test_zero_gives_one(self):
        c = an.compare([("item:a", "x", 1.0), ("item:a", "x", -1.0)], ["x"], "accuracy")
        self.assertEqual((c["T"], c["p_by_pairs"], c["p_by_questions"]), (0.0, 1.0, 1.0))
        self.assertTrue(c["range_crosses_zero"])

    def test_the_line(self):
        c = an.compare([(f"item:{u}", "x", 1.0) for u in "abcdefghi"], ["x"], "thinking", line=0.01)
        self.assertTrue(c["declared"])  # p by pairs is about 2 / 512
        c = an.compare([(f"item:{u}", "x", 1.0) for u in "abcdef"], ["x"], "thinking", line=0.01)
        self.assertFalse(c["declared"])  # about 2 / 64


class StageRuleTest(unittest.TestCase):
    def test_the_four_cases(self):
        self.assertEqual(an.stage1_decision(0.004, 0.009), "stop")      # both at most 0.01
        self.assertEqual(an.stage1_decision(0.004, 0.30), "stop")       # one at most 0.01, the other above 0.10
        self.assertEqual(an.stage1_decision(0.30, 0.004), "stop")
        self.assertEqual(an.stage1_decision(0.004, 0.05), "continue")   # one at most 0.01, the other between
        self.assertEqual(an.stage1_decision(0.05, 0.004), "continue")
        self.assertEqual(an.stage1_decision(0.02, 0.50), "continue")    # both above 0.01
        self.assertEqual(an.stage1_decision(0.20, 0.50), "continue")

    def test_the_edges(self):
        self.assertEqual(an.stage1_decision(0.01, 0.01), "stop")
        self.assertEqual(an.stage1_decision(0.01, 0.10), "continue")  # 0.10 is not above 0.10
        self.assertEqual(an.stage1_decision(0.0101, 0.5), "continue")


class DeclaredTest(unittest.TestCase):
    def test_the_sentences_and_not_the_program(self):
        f = {(OLD, "sw_w"): 0.6, (NEW, "sw_w"): 0.6}
        rep = an.report(make_rows(f, seed=1), keys=NO_KEYS)
        t1, t2 = rep["test_1_sentences_thinking"], rep["test_2_program_thinking"]
        self.assertTrue(t1["declared"])
        self.assertEqual(t1["direction"], "T below zero")
        self.assertLess(t1["p_by_questions"], 0.05)
        self.assertFalse(t2["declared"])
        self.assertEqual(rep["outcome_of_the_tests"], {"test_1": "declared, T below zero",
                                                       "test_2": "not declared, " + t2["direction"]})
        text = an.text_report(rep)
        self.assertIn("Outcome: test 1 declared, T below zero | test 2 not declared", text)
        self.assertIn("DECLARED at 0.04", text)

    def test_the_program_and_not_the_sentences(self):
        f = {(NEW, w): 0.6 for w in an.ALL_WAYS}
        t1, t2 = tests_of(make_rows(f, seed=2), line=an.LINE_CONTINUE)
        self.assertTrue(t2["declared"])
        self.assertEqual(t2["direction"], "T below zero")
        self.assertFalse(t1["declared"])

    def test_no_difference_is_declared_about_one_time_in_twenty(self):
        # with no decision file the line is 0.04: about 16 of 400
        hits = [0, 0]
        for seed in range(400):
            for i, t in enumerate(tests_of(make_rows(seed=1000 + seed, units=6, passes=(1, 2, 3)), line=0.04)):
                hits[i] += t["declared"]
        # a binomial count (400 draws, chance 0.04) falls from 5 to 30 with chance above 0.998
        for h in hits:
            self.assertGreaterEqual(h, 5)
            self.assertLessEqual(h, 30)

    def test_no_difference_through_the_two_stages(self):
        # stage 1 is passes 1 to 3, the whole group passes 1 to 6
        reps, hits = 500, [0, 0]
        for seed in range(reps):
            first = make_rows(seed=5000 + seed, units=6, passes=(1, 2, 3))
            s1 = tests_of(first)
            if an.stage1_decision(s1[0]["p_by_pairs"], s1[1]["p_by_pairs"]) == "stop":
                done = tests_of(first, line=an.LINE_STOP)
            else:
                done = tests_of(first + make_rows(seed=9000 + seed, units=6, passes=(4, 5, 6)), line=an.LINE_CONTINUE)
            for i, t in enumerate(done):
                hits[i] += t["declared"]
        # about 4.6% is expected (0.01 x 0.91 when stage 1 stops, up to 0.04 when it goes on)
        for h in hits:
            self.assertLessEqual(h, 40)  # 8% of 500
            self.assertGreaterEqual(h, 8)


class WhichAsksCountTest(unittest.TestCase):
    def setUp(self):
        self.rows = make_rows(seed=5)
        self.full_1, self.full_2 = pairs_of(self.rows, an.TEST_1), pairs_of(self.rows, an.TEST_2)
        self.full_own = pairs_of(self.rows, an.OWN)

    def test_a_question_one_cell_has_no_record_of_is_left_out_of_every_cell(self):
        gone = [r for r in self.rows if not (r["version"] == NEW and r["group"] == "sw_o"
                                             and r["unit"] == "item:q2" and r["pass"] == 3)]
        slots, cells, _, info = an.counted(gone)
        self.assertEqual(info["cells_with_every_cell"], info["cells"] - 1)
        self.assertNotIn((3, "item:q2"), cells)
        self.assertFalse([k for k in slots if k[:2] == ("item:q2", 3)])
        self.assertEqual(pairs_of(gone, an.TEST_1), self.full_1 - 2)  # both programs lose the pair
        self.assertEqual(pairs_of(gone, an.TEST_2), self.full_2 - 2)  # both ways lose the pair
        self.assertEqual(pairs_of(gone, an.OWN), self.full_own - 1)  # its 2.1.316 sw_o ask counts no more
        rep = an.report(gone, numbers=range(1, 5), keys=NO_KEYS)
        self.assertFalse(rep["completeness"]["passes"]["3"]["complete"])
        self.assertEqual(rep["completeness"]["passes"]["3"]["questions_not_complete"], ["item:q2"])
        self.assertTrue(rep["completeness"]["passes"]["2"]["complete"])
        self.assertIn("pass 3: NOT complete", an.text_report(rep))

    def test_an_ask_that_is_not_scored_takes_out_its_own_pairs_only(self):
        for r in self.rows:
            if (r["version"], r["group"], r["unit"], r["pass"]) == (NEW, "sw_w", "item:q1", 2):
                r.update(outcome="void", thinking_tokens=None, score=None)
        self.assertEqual(pairs_of(self.rows, an.TEST_1), self.full_1 - 1)
        self.assertEqual(pairs_of(self.rows, an.TEST_2), self.full_2 - 1)
        self.assertEqual(pairs_of(self.rows, an.OWN), self.full_own - 1)
        self.assertEqual(pairs_of(self.rows, an.REPORTED["test_2_on_sw_o_alone"]), self.full_own)

    def test_a_question_with_a_layer_without_pairs_is_left_out_and_named(self):
        for r in self.rows:
            if (r["version"], r["group"], r["unit"]) == (NEW, "sw_o", "item:q3"):
                r.update(outcome="error", thinking_tokens=None, score=None)
            if r["unit"] == "item:q4" and r["group"] == "sw_w":
                r.update(outcome="void", thinking_tokens=None, score=None)
        rep = an.report(self.rows, keys=NO_KEYS)
        t1 = rep["test_1_sentences_thinking"]
        self.assertEqual(t1["questions"], 6)
        self.assertEqual(t1["questions_left_out"], {"item:q3": {OLD: 4, NEW: 0}, "item:q4": {OLD: 0, NEW: 0}})
        self.assertNotIn("item:q3", t1["question_figures"])
        self.assertEqual(rep["test_2_program_thinking"]["questions_left_out"]["item:q3"], {"sw_o": 0, "sw_w": 4})
        self.assertIn("item:q3", rep["reported_no_declaration"]["own_sentences_two_cells"]["thinking"]["question_figures"])
        self.assertIsNone(rep["questions"]["item:q3"]["test_1_thinking"])
        self.assertIn("left out (pairs by layer): item:q3 2.1.316 4, 2.1.317 0 | item:q4", an.text_report(rep))


class SwNTest(unittest.TestCase):
    def test_four_cells_and_no_sw_n(self):
        rep = an.report(make_rows(seed=17), keys=NO_KEYS)
        self.assertEqual(len(rep["cells"]), 4)
        self.assertEqual(set(rep["reported_no_declaration"]), set(an.REPORTED))
        self.assertIn("sw_n was not sent in the passes", an.text_report(rep))

    def test_with_sw_n_the_three_more_are_reported(self):
        rows = make_rows(seed=18, ways=an.ALL_WAYS, factor={(NEW, "sw_n"): 0.5})
        rep = an.report(rows, ways=an.ALL_WAYS, keys=NO_KEYS)
        self.assertEqual(len(rep["cells"]), 6)
        self.assertEqual(set(rep["reported_no_declaration"]), set(an.REPORTED) | set(an.REPORTED_WITH_SW_N))
        self.assertLess(rep["reported_no_declaration"]["original_two_cells"]["thinking"]["exp_T_minus_1"], -0.3)
        # a question whose sw_n record is missing in one pass is left out of all six cells there
        gone = [r for r in rows if not (r["group"] == "sw_n" and r["version"] == OLD and r["unit"] == "item:q0" and r["pass"] == 1)]
        self.assertEqual(pairs_of(gone, an.TEST_1, an.ALL_WAYS), pairs_of(rows, an.TEST_1, an.ALL_WAYS) - 2)

    def test_where_the_ways_come_from(self):
        tmp = Path(tempfile.mkdtemp(prefix="swap_analysis_test_"))
        try:
            rows = make_rows(seed=19, passes=(1,), ways=an.ALL_WAYS)
            self.assertEqual(an.ways_in_use(tmp, [1], rows), (an.ALL_WAYS, "the records (no plan file found)"))
            self.assertEqual(an.ways_in_use(tmp, [1], [], ["sw_w", "sw_o"], "[group] scored_groups"),
                             (an.DEFAULT_WAYS, "[group] scored_groups"))
            with self.assertRaisesRegex(an.AnalysisError, "sw_o and sw_w must both be sent"):
                an.ways_in_use(tmp, [1], rows, ["sw_n", "sw_o"])
            with self.assertRaisesRegex(an.AnalysisError, "does not know"):
                an.ways_in_use(tmp, [1], rows, ["sw_o", "sw_w", "sw_x"])
            (tmp / "SW1.json").write_text(json.dumps({"asks": [{"ask_id": "a", "group": "sw_o"}, {"ask_id": "b", "group": "sw_w"}]}))
            self.assertEqual(an.ways_in_use(tmp, [1], rows), (an.DEFAULT_WAYS, "the pass plans"))
            with self.assertRaisesRegex(an.AnalysisError, "the pass plans send"):
                an.ways_in_use(tmp, [1], rows, ["sw_n", "sw_o", "sw_w"], "[group] scored_groups")
        finally:
            shutil.rmtree(tmp)


class SplitTest(unittest.TestCase):
    def test_the_three_numbers_agree(self):
        rows = make_rows({(OLD, "sw_w"): 0.7, (NEW, "sw_o"): 0.8, (NEW, "sw_w"): 0.5}, seed=20, spread=0.6)
        for r in rows[::17]:
            r.update(outcome="void", thinking_tokens=None, score=None)
        rep = an.report(rows, keys=NO_KEYS)
        for kind in ("thinking", "accuracy"):
            d = rep["decomposition"][kind]
            self.assertAlmostEqual(d["T"]["own"], d["T"]["test_1"] + d["T"]["test_2"], places=12)
        d = rep["decomposition"]["thinking"]
        self.assertAlmostEqual(d["share_of_test_1"] + d["share_of_test_2"], 1.0, places=9)
        self.assertLess(d["range"]["own"][1], 0)
        self.assertFalse(d["denominator_range_crosses_zero"])
        self.assertNotIn("the range of the denominator crosses 0", " ".join(an._fmt_split(d)))

    def test_a_split_that_does_not_add_up_stops(self):
        slots, full, _, _ = an.counted(make_rows(seed=21))
        wrong = (("x", (NEW, "sw_o"), (OLD, "sw_w")),)
        with mock.patch.object(an, "OWN", wrong), self.assertRaises(an.AnalysisError):
            an.decomposition(slots, full, an.lthink, "thinking")

    def test_a_denominator_whose_range_crosses_zero_is_marked(self):
        f = {(OLD, "sw_w"): 0.6, (NEW, "sw_o"): 1 / 0.6, (NEW, "sw_w"): 1.0}  # test 1 and test 2 cancel out
        rep = an.report(make_rows(f, seed=22), keys=NO_KEYS)
        d = rep["decomposition"]["thinking"]
        self.assertTrue(d["denominator_range_crosses_zero"])
        self.assertIn("(the range of the denominator crosses 0)", an.text_report(rep))


class LeaveOneOutTest(unittest.TestCase):
    def test_a_difference_on_one_question_names_it(self):
        q = {(v, "sw_w", 3): 0.2 for v in an.PROGRAMS}  # only q3: sw_w thinks a fifth of sw_o
        rep = an.report(make_rows(qfactor=q, seed=23, spread=0.2), keys=NO_KEYS)
        loo = rep["test_1_sentences_thinking"]["leave_one_out"]
        self.assertEqual(loo["questions_without_which_T_is_below_half"], ["item:q3"])
        self.assertEqual(loo["highest"]["without"], "item:q3")
        f = rep["test_1_sentences_thinking"]["question_figures"]
        self.assertAlmostEqual(loo["T_without_each"]["item:q3"], (sum(f.values()) - f["item:q3"]) / 7)
        self.assertIn("less than half as far from zero without: item:q3", an.text_report(rep))
        for c in (rep["test_2_program_accuracy_no_declaration"],
                  rep["reported_no_declaration"]["own_sentences_two_cells"]["thinking"]):
            self.assertIn("lowest", c["leave_one_out"])


class ReadingTest(unittest.TestCase):
    """Plan folders, plan files and a settings file in a temporary folder. The stand-in for the grader
    reads rows.jsonl in a plan folder."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="swap_analysis_test_"))
        self.raw = self.tmp / "raw"
        self.raw.mkdir()
        self.plans = self.tmp / "plans"
        self.out = self.tmp / "out"
        self.called = []

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def put(self, name: str, rows: list[dict], plan: list[dict] | None = None):
        """The records of a plan, and its plan file with the asks of `plan` (the rows when not given)."""
        (self.raw / name).mkdir(exist_ok=True)
        (self.raw / name / "rows.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        self.plans.mkdir(exist_ok=True)
        asks = [{k: r[k] for k in ("ask_id", "pass", "version", "unit", "group")} for r in (rows if plan is None else plan)]
        (self.plans / f"{name}.json").write_text(json.dumps({"name": name, "asks": asks}))

    def put_passes(self, rows: list[dict]):
        for n in sorted({r["pass"] for r in rows}):
            self.put(f"SW{n}", [r for r in rows if r["pass"] == n])

    def grade_plan(self, name: str):
        self.called.append(name)
        f = self.raw / name / "rows.jsonl"
        return an.load_jsonl(f) if f.exists() else None

    def settings(self, stage1_passes=2, passes=4, units=8, scored_groups=None) -> Path:
        (self.tmp / "items.json").write_text(json.dumps({"items": [f"q{u}" for u in range(units)]}))
        f = self.tmp / "settings.toml"
        f.write_text("\n".join(
            ["[paths]"] + [f'{k} = "{self.tmp / k}"' for k in (
                "author_repo", "livenerf_cache", "item_file", "probe_file", "versions_file", "experiment_root",
                "config_root", "home_dir", "workdir", "tmpdir", "config_dirs_file")]
            + [f'raw_dir = "{self.raw}"', "[env]"] + [f'{k} = "x"' for k in ("PATH", "SHELL", "USER", "LANG", "TZ")]
            + ["[login]", 'method = "keychain"', f'securestorage_config_dir = "{self.tmp}"',
               "[group]", 'item_list = "items.json"', f"passes = {passes}", f"stage1_passes = {stage1_passes}"]
            + ([f"scored_groups = {json.dumps(scored_groups)}"] if scored_groups else [])) + "\n")
        return f

    def run_main(self, *more, scored_groups=None) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = an.main(["--settings", str(self.settings(scored_groups=scored_groups)), "--out", str(self.out), *more],
                           grade_plan=self.grade_plan)
        return code, out.getvalue(), err.getvalue()

    def test_scored_groups_with_sw_n_gives_six_cells(self):
        self.put_passes(make_rows(seed=36, passes=(1, 2, 3, 4), ways=an.ALL_WAYS))
        code, _, _ = self.run_main(scored_groups=["sw_n", "sw_o", "sw_w"])
        self.assertEqual(code, 0)
        rep = json.loads((self.out / "report.json").read_text())
        self.assertEqual((len(rep["cells"]), rep["ways_from"]), (6, "[group] scored_groups"))
        self.assertIn("original_two_cells", rep["reported_no_declaration"])
        # the settings say four cells, the plans six: stop and say so
        code, _, err = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("the default of swap.py (no scored_groups) says the passes send ['sw_o', 'sw_w'], "
                      "the pass plans send ['sw_n', 'sw_o', 'sw_w']", err)

    def test_only_sw_n_and_sw_n_r_are_read(self):
        rows = make_rows(seed=6, passes=(1, 2))
        self.put_passes(rows)
        self.put("SW1r", [])
        self.put("SW10", [])
        trial = [dict(r, thinking_tokens=1) for r in make_rows(seed=7, passes=(1,))]
        for name in ("SWS", "SW", "SW0", "SWx1", "SW1rr", "sw7", "X1", "RP1", "SW2probe", "SW1 r", "SWH_001", "SWP1_1"):
            self.put(name, trial)
        (self.raw / "SW3").write_text("a file, not a plan folder")
        self.assertEqual(an.plan_names(self.raw), ["SW1", "SW1r", "SW2", "SW10"])
        got, plans, beyond, _ = an.load_rows(self.raw, self.grade_plan)
        self.assertEqual(self.called, ["SW1", "SW1r", "SW2", "SW10"])
        self.assertEqual(list(plans), ["SW1", "SW1r", "SW2", "SW10"])
        self.assertEqual(json.dumps(got), json.dumps(rows))
        self.called.clear()
        _, plans, beyond, _ = an.load_rows(self.raw, self.grade_plan, last=2)
        self.assertEqual((self.called, beyond), (["SW1", "SW1r", "SW2"], ["SW10"]))

    def test_an_ask_asked_once_more_goes_into_the_pass_it_replaces(self):
        rows = make_rows(seed=8, passes=(1, 2))
        key = (OLD, "sw_w", "item:q1", 2)
        original = next(r for r in rows if (r["version"], r["group"], r["unit"], r["pass"]) == key)
        failed = dict(original, outcome="error", thinking_tokens=None, score=None, never_reached_model=True)
        again = dict(original, ask_id="r2-again", thinking_tokens=tok(4), resend_of={"plan": "SW2", "ask_id": original["ask_id"]})
        self.put("SW1", [r for r in rows if r["pass"] == 1])
        self.put("SW2", [failed if r is original else r for r in rows if r["pass"] == 2])
        self.put("SW2r", [again])
        got, plans, _, detail = an.load_rows(self.raw, self.grade_plan)
        self.assertEqual(plans["SW2r"], {"rows": 1, "rows_whose_pass_is_not_the_plans": 0})
        self.assertEqual(an.pass_gaps(self.plans, [1, 2], detail), {"1": [], "2": []})
        slots, cells, _, info = an.counted(got)
        self.assertEqual(info["cells_with_every_cell"], info["cells"])
        self.assertAlmostEqual(an.slot_values(slots, an.lthink)[("item:q1", 2, OLD, "sw_w")], 4 * LN10)
        self.assertEqual(pairs_of(got, an.TEST_1), pairs_of(rows, an.TEST_1))
        without = [r for r in got if r["ask_id"] != "r2-again"]
        self.assertEqual(pairs_of(without, an.TEST_1), pairs_of(rows, an.TEST_1) - 1)

    def test_rows_of_another_pass_in_a_plan_are_counted(self):
        self.put("SW1", [row(OLD, "sw_o", "q0", 2, 10)])
        _, plans, _, _ = an.load_rows(self.raw, self.grade_plan)
        self.assertEqual(plans["SW1"]["rows_whose_pass_is_not_the_plans"], 1)

    # -- the two stages through main()

    def test_stage_1_refuses_when_a_pass_is_not_complete(self):
        rows = make_rows({(OLD, "sw_w"): 0.5, (NEW, "sw_w"): 0.5}, seed=24, passes=(1, 2))
        self.put("SW1", [r for r in rows if r["pass"] == 1])
        two = [r for r in rows if r["pass"] == 2]
        self.put("SW2", two[:-3], plan=two)  # three asks of the plan have no record yet
        code, out, err = self.run_main("--stage1")
        self.assertEqual(code, 2)
        self.assertIn("pass 2: 3 of the 32 asks of SW2 have no record", err)
        self.assertFalse((self.out / "stage1_decision.json").exists())
        self.assertNotIn("STAGE1", out)

    def test_stage_1_refuses_when_an_ask_that_never_reached_the_model_was_not_asked_again(self):
        rows = make_rows(seed=25, passes=(1, 2))
        rows[3].update(outcome="error", thinking_tokens=None, score=None, never_reached_model=True)
        self.put_passes(rows)
        code, _, err = self.run_main("--stage1")
        self.assertEqual(code, 2)
        self.assertIn("pass 1: 1 asks of SW1 never reached the model and were not asked once more", err)

    def test_stage_1_refuses_without_the_plan_of_a_pass(self):
        self.put("SW1", make_rows(seed=26, passes=(1,)))
        code, _, err = self.run_main("--stage1")
        self.assertEqual(code, 2)
        self.assertIn("pass 2: no plan file SW2.json", err)

    def test_stop_after_stage_1_then_the_end_reads_stage_1_at_0_01(self):
        f = {(OLD, "sw_w"): 0.4, (NEW, "sw_w"): 0.4, (NEW, "sw_o"): 0.4}
        self.put_passes(make_rows(f, seed=27, passes=(1, 2), spread=0.3))
        code, out, _ = self.run_main("--stage1")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[-1], "STAGE1 stop")
        d = json.loads((self.out / "stage1_decision.json").read_text())
        self.assertEqual(d["decision"], "stop")
        self.assertEqual(set(d), {"decision", "p_by_pairs", "T", "stage1_passes", "passes", "rule", "plans_read", "computed_at"})
        self.assertEqual(d["plans_read"], {"SW1": 32, "SW2": 32})
        self.assertLessEqual(max(d["p_by_pairs"].values()), 0.01)
        self.assertEqual(out[:-len("STAGE1 stop\n")], (self.out / "stage1_report.txt").read_text())
        s1 = json.loads((self.out / "stage1_report.json").read_text())
        self.assertIsNone(s1["test_1_sentences_thinking"]["declared"])
        self.assertEqual(s1["stage1_decision"]["decision"], "stop")
        self.assertFalse((self.out / "report.json").exists())
        # the end: passes 1 and 2 only, line 0.01
        self.called.clear()
        code, out, _ = self.run_main()
        self.assertEqual(code, 0)
        rep = json.loads((self.out / "report.json").read_text())
        self.assertEqual((rep["stage"]["decision"], rep["stage"]["line"]), ("stop", 0.01))
        self.assertTrue(rep["stage"]["decision_p_agree_with_now"])
        self.assertEqual(rep["test_1_sentences_thinking"]["line"], 0.01)
        self.assertTrue(rep["test_1_sentences_thinking"]["declared"])
        self.assertEqual(list(rep["completeness"]["passes"]), ["1", "2"])
        self.assertTrue(rep["completeness"]["all_complete"])
        self.assertIn("Stopped after stage 1: passes 1 to 2, line 0.01.", out)
        self.assertEqual(out, (self.out / "report.txt").read_text())
        # a plan of a later pass in the records: stop and say so
        self.put("SW3", make_rows(seed=28, passes=(3,)))
        code, _, err = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("stage 1 said stop, but the records hold plans after pass 2: SW3", err)

    def test_continue_after_stage_1_then_the_end_reads_every_pass_at_0_04(self):
        self.put_passes(make_rows(seed=29, passes=(1, 2)))
        code, out, _ = self.run_main("--stage1")
        self.assertEqual(out.splitlines()[-1], "STAGE1 continue")
        self.put_passes(make_rows(seed=30, passes=(3, 4)))
        self.put("SW7", make_rows(seed=31, passes=(7,)))
        self.called.clear()
        code, out, _ = self.run_main()
        self.assertEqual(code, 0)
        self.assertEqual(self.called, ["SW1", "SW2", "SW3", "SW4"])
        rep = json.loads((self.out / "report.json").read_text())
        self.assertEqual((rep["stage"]["decision"], rep["stage"]["line"]), ("continue", 0.04))
        self.assertEqual(rep["test_2_program_thinking"]["line"], 0.04)
        self.assertEqual(list(rep["completeness"]["passes"]), ["1", "2", "3", "4"])
        self.assertEqual(rep["stage"]["plans_not_read"], ["SW7"])
        self.assertIn("Both stages sent: passes 1 to 4, line 0.04.", out)
        # --stage1 again on the same records keeps the file it wrote, and a file with another decision is refused
        before = (self.out / "stage1_decision.json").read_text()
        self.assertEqual(self.run_main("--stage1")[0], 0)
        self.assertEqual((self.out / "stage1_decision.json").read_text(), before)
        (self.out / "stage1_decision.json").write_text(json.dumps(dict(json.loads(before), decision="stop")))
        code, _, err = self.run_main("--stage1")
        self.assertEqual(code, 2)
        self.assertIn("already holds decision stop", err)

    def test_no_decision_file_reads_every_pass_and_says_so(self):
        rows = make_rows(seed=32, passes=(1, 2, 3))
        self.put_passes(rows)
        main_file = self.tmp / "main_graded.jsonl"
        main_file.write_text("".join(json.dumps(dict(r, group="main")) + "\n"
                                     for r in make_rows(seed=33, passes=(1, 2, 3)) if r["group"] == "sw_o"))
        code, out, _ = self.run_main("--main-graded", str(main_file))
        self.assertEqual(code, 0)
        rep = json.loads((self.out / "report.json").read_text())
        self.assertEqual(rep["raw_dir"], str(self.raw))
        self.assertIsNone(rep["stage"]["decision_file"])
        self.assertEqual(rep["stage"]["line"], 0.04)
        self.assertTrue(out.splitlines()[2].startswith("No stage1_decision.json"))
        self.assertFalse(rep["completeness"]["all_complete"])  # pass 4 was not sent
        self.assertEqual(rep["completeness"]["passes"]["4"]["plan_problems"], ["no plan file SW4.json"])
        self.assertEqual(rep["ways_from"], "the default of swap.py (no scored_groups)")
        self.assertEqual(rep["beside_own_sentences_two_cells"]["main"]["thinking"]["questions"], 8)
        self.assertIn("pass 4: NOT complete", out)


class FolderTest(unittest.TestCase):
    def test_a_folder_that_thinks_more_gives_a_small_p(self):
        rows = make_rows(passes=tuple(range(1, 10)), seed=11, spread=0.4, folder_factor={f"/cfg/root/{OLD}/w1": 1.8})
        slots, _, _, _ = an.counted(rows)
        f = an.folder_rows(slots)
        self.assertLess(f["programs"][OLD]["p"], 0.01)
        self.assertGreater(f["programs"][NEW]["p"], 0.05)
        top = max((r for r in f["folders"].values() if r["program"] == OLD), key=lambda r: r["mean_ln_difference"])
        self.assertEqual((top["label"], top["sets"]), (f"{OLD}/w1", ["w1"]))
        self.assertEqual(sum(r["asks"] for r in f["folders"].values()), len(rows))
        self.assertEqual(f["folders_used_by_both_programs"], [])

    def test_no_folder_apart_gives_a_p_that_is_not_small(self):
        slots, _, _, _ = an.counted(make_rows(passes=tuple(range(1, 10)), seed=12, spread=0.4))
        f = an.folder_rows(slots)
        for v in an.PROGRAMS:
            self.assertGreater(f["programs"][v]["p"], 0.05)

    def test_the_figure_of_a_folder(self):
        # one question, one way: folder w1 has 3 and 1, folder w2 has 2 (in ln 10). Mean 2.
        rows = [row(OLD, "sw_o", "q0", p, tok(k), set_=s) for p, k, s in ((1, 3, "w1"), (2, 1, "w1"), (3, 2, "w2"))]
        slots = {("item:q0", r["pass"], OLD, "sw_o"): [r] for r in rows}
        f = an.folder_rows(slots)
        self.assertAlmostEqual(f["folders"][f"{OLD} /cfg/root/{OLD}/w1"]["mean_ln_difference"], 0.0)
        rows[1]["thinking_tokens"] = tok(4)  # now w1 has 3 and 4, w2 has 2: mean 3, w1 +0.5, w2 -1
        f = an.folder_rows(slots)
        self.assertAlmostEqual(f["folders"][f"{OLD} /cfg/root/{OLD}/w1"]["mean_ln_difference"], 0.5 * LN10)
        self.assertAlmostEqual(f["folders"][f"{OLD} /cfg/root/{OLD}/w2"]["mean_ln_difference"], -1.0 * LN10)
        self.assertAlmostEqual(f["programs"][OLD]["statistic"], (2 * 0.25 + 1) * LN10 ** 2)


class SetTest(unittest.TestCase):
    def test_the_set_comes_from_the_swap_field_then_the_options(self):
        self.assertEqual(an.ask_set({"swap": {"set": "w2"}, "options": {"config_set": "w3"}}), "w2")
        self.assertEqual(an.ask_set({"swap": {"set": an.NO_SET}, "options": {"config_set": "w3"}}), "w3")
        self.assertEqual(an.ask_set({"options": {"config_set": "w3"}}), "w3")
        self.assertIsNone(an.ask_set({}))

    def test_a_question_and_pass_in_two_sets_is_named(self):
        rows = make_rows(seed=34, passes=(1,))
        rows[0]["swap"] = {"set": "w9"}
        _, _, _, info = an.counted(rows)
        self.assertEqual(info["question_passes_in_more_than_one_set"], [f"pass 1 {rows[0]['unit']}"])


class SameTwiceTest(unittest.TestCase):
    def test_the_same_rows_give_the_same_report(self):
        rows = make_rows(seed=13, spread=0.6)
        keys = {"sound": ["q0", "q1"], "also_accepted": {}, "replaced": {}, "left_out": ["q2"]}
        main = [dict(r, group="main") for r in rows if r["group"] == "sw_o"]
        a = an.report(rows, keys=keys, main_rows=main)
        b = an.report([dict(r) for r in rows], keys=keys, main_rows=[dict(r) for r in main])
        self.assertEqual(json.dumps(a), json.dumps(b))
        tmp = Path(tempfile.mkdtemp(prefix="swap_analysis_test_"))
        try:
            an.write_report(a, tmp / "1")
            an.write_report(b, tmp / "2")
            for name in ("report.json", "report.txt"):
                self.assertEqual((tmp / "1" / name).read_bytes(), (tmp / "2" / name).read_bytes())
        finally:
            shutil.rmtree(tmp)


class TwoMoreWaysTest(unittest.TestCase):
    KEYS = {"sound": ["q0", "q1"], "also_accepted": {"q2": "B"}, "replaced": {"q3": "7"}, "left_out": ["q4"]}

    def test_rescore_is_loaded_without_taking_the_name_of_this_file(self):
        rs = an.rescore_module()
        self.assertIs(sys.modules["analysis"], an)
        self.assertEqual(rs.A.__name__, "recheck_analysis")
        self.assertTrue(hasattr(rs.A, "TEN"))
        self.assertEqual(rs.KEYS_FILE.name, "rescore_keys_20261113.json")

    def test_sound_and_corrected(self):
        rows = []
        for p in (1, 2):
            for u in range(5):
                for v, w in an.FOUR:
                    # sw_w gives answer B on q2 (wrong by the key, right as well by the list), A elsewhere
                    ans = "B" if (w == "sw_w" and u == 2) else "A"
                    rows.append(row(v, w, f"q{u}", p, 100, 0.0 if ans == "B" else 1.0, answer=ans))
        rep = an.report(rows, keys=self.KEYS)
        m = rep["accuracy_two_more_ways_no_declaration"]
        self.assertEqual(set(m["sound"]), {"test_1", "test_2", "own_sentences_two_cells"})
        self.assertEqual(m["sound"]["test_1"]["questions"], 2)
        self.assertAlmostEqual(m["sound"]["test_1"]["points"], 0.0)
        c = m["corrected"]["test_1"]
        self.assertEqual(c["questions"], 4)
        self.assertNotIn("item:q4", c["questions_left_out"])
        self.assertNotIn("item:q4", c["question_figures"])
        self.assertAlmostEqual(c["question_figures"]["item:q2"], 0.0)  # right as well by the list
        self.assertAlmostEqual(c["question_figures"]["item:q3"], 0.0)  # A is not the replaced value 7: all wrong
        self.assertAlmostEqual(rep["test_1_sentences_accuracy_no_declaration"]["points"], -100 / 5)
        self.assertAlmostEqual(m["corrected"]["own_sentences_two_cells"]["points"], 0.0)
        for way in ("sound", "corrected"):
            for c in m[way].values():
                self.assertIsNone(c["declared"])

    def test_the_real_lists_are_read_when_none_are_given(self):
        m = an.report(make_rows(seed=14))["accuracy_two_more_ways_no_declaration"]
        self.assertTrue(m["sound"]["test_1"]["no_data"])  # made-up questions are on none of the lists


class BesideTest(unittest.TestCase):
    def test_main_and_high_recheck_on_the_same_questions(self):
        rows = [r for r in make_rows(seed=15) if r["unit"] != "item:q7"]
        main = []
        for p in (1, 2, 3):
            for u in range(8):
                for v, t in ((OLD, 1000), (NEW, 500), ("2.1.318", 50)):
                    main.append(row(v, "main", f"q{u}", p, t))
                main.append(row(OLD, "flags_on", f"q{u}", p, 5))
        high = [dict(r, group="high_recheck") for r in main if r["group"] == "main"]
        rep = an.report(rows, main_rows=main, high_rows=high, keys=NO_KEYS)
        for name in ("main", "high_recheck"):
            b = rep["beside_own_sentences_two_cells"][name]
            self.assertEqual(b["thinking"]["questions"], 7)  # q7 is not in the swap group
            self.assertEqual(b["thinking"]["pairs"], 21)
            self.assertAlmostEqual(b["thinking"]["exp_T_minus_1"], 501 / 1001 - 1)
            self.assertIsNone(b["thinking"]["declared"])
        self.assertIn("== Beside the two cells with their own sentences", an.text_report(rep))
        self.assertNotIn("beside_own_sentences_two_cells", an.report(rows, keys=NO_KEYS))


class TextTest(unittest.TestCase):
    def test_the_text_has_every_part(self):
        rep = an.report(make_rows(seed=16), keys=TwoMoreWaysTest.KEYS)
        text = an.text_report(rep)
        for part in ("TEST 1, the sentences", "TEST 2, the program", "Outcome:", "no declaration",
                     "own_sentences_two_cells", "test_2_on_sw_w_alone", "as test 1 plus test 2",
                     "one question left out", "== Each cell", "== Each question", "asks with zero thinking",
                     "== Each set of worker folders", "== Each config folder", "Accuracy scored two more ways",
                     "Decided after the registered results were seen."):
            self.assertIn(part, text)
        # the fixed line beside each test
        beside = [line for line in text.splitlines() if line.startswith("    p by pairs")]
        self.assertEqual(len(beside), 2)
        self.assertTrue(all("| p by questions" in b and "| range crosses 0: " in b for b in beside))

    def test_the_stage_1_report(self):
        rep = an.report(make_rows(seed=35), stage1=True, keys=NO_KEYS)
        self.assertIsNone(rep["test_1_sentences_thinking"]["declared"])
        self.assertIn(rep["stage1_decision"]["decision"], ("stop", "continue"))
        self.assertNotIn("outcome_of_the_tests", rep)
        self.assertIn("STAGE 1 DECISION:", an.text_report(rep))

    def test_no_rows_at_all(self):
        rep = an.report([], keys=TwoMoreWaysTest.KEYS)
        self.assertTrue(rep["test_1_sentences_thinking"]["no_data"])
        self.assertEqual(rep["outcome_of_the_tests"], {"test_1": "no data", "test_2": "no data"})
        self.assertTrue(rep["decomposition"]["thinking"]["no_data"])
        self.assertIn("no pass is read", an.text_report(rep))
        with self.assertRaises(an.AnalysisError):
            an.report([], stage1=True, keys=NO_KEYS)


if __name__ == "__main__":
    unittest.main()
