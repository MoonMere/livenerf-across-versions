"""Tests of analysis.py on made-up rows. No data of the run is read.

    python -B -m unittest test_analysis
"""

import math
import random
import unittest

import analysis as an


def make_rows(group: str, think_by_version: dict, acc_by_version: dict, passes=(1, 2, 3), units: int = 6,
              seed: int = 0, spread: float = 0.0) -> list[dict]:
    """One scored ask per version, pass and question. Thinking tokens are think_by_version[v] (times a
    random factor when spread > 0); the ask is right with probability acc_by_version[v] (exactly, by
    rounding, when the probability is 0 or 1)."""
    rng = random.Random(seed)
    out = []
    for v in think_by_version:
        for p in passes:
            for u in range(units):
                t = think_by_version[v] * (math.exp(rng.gauss(0, spread)) if spread else 1.0)
                out.append({"group": group, "version": v, "pass": p, "unit": f"item:q{u}", "outcome": "scored",
                            "thinking_tokens": int(round(t)), "score": float(rng.random() < acc_by_version[v]),
                            "tool_calls": 0})
    return out


FLAT = {v: 1000 for v in an.TEN + (an.ELEVENTH,)}
HALF = {v: 0.5 for v in an.TEN + (an.ELEVENTH,)}


class SplitTest(unittest.TestCase):
    def test_complete_separation_gives_the_smallest_p(self):
        values = {v: 1.0 for v in an.EARLIER} | {v: 0.0 for v in an.LATER}
        r = an.split_test(values)
        self.assertAlmostEqual(r["T"], -1.0)
        self.assertAlmostEqual(r["p"], 2 / 252)
        self.assertTrue(r["declared"])

    def test_no_difference_gives_p_one(self):
        r = an.split_test({v: 3.0 for v in an.TEN})
        self.assertEqual(r["p"], 1.0)
        self.assertFalse(r["declared"])

    def test_p_counts_both_directions_and_the_true_split(self):
        # values 1..10 in version order: the later five are the five largest; only the mirror split is as far
        values = {v: float(i) for i, v in enumerate(an.TEN, 1)}
        r = an.split_test(values)
        self.assertAlmostEqual(r["T"], 5.0)
        self.assertEqual(r["splits_at_least_as_far"], 2)

    def test_one_overlap_is_not_the_smallest_p(self):
        values = {v: float(i) for i, v in enumerate(an.TEN, 1)}
        values["2.1.316"], values["2.1.317"] = values["2.1.317"], values["2.1.316"]  # swap 5 and 6
        r = an.split_test(values)
        self.assertAlmostEqual(r["T"], 4.6)
        self.assertEqual(r["splits_at_least_as_far"], 4)

    def test_p_against_a_direct_count(self):
        rng = random.Random(3)
        from itertools import combinations
        for _ in range(20):
            x = [rng.gauss(0, 1) for _ in range(10)]
            t = sum(x[5:]) / 5 - sum(x[:5]) / 5
            n = 0
            for c in combinations(range(10), 5):
                a = sum(x[i] for i in c) / 5
                b = sum(x[i] for i in range(10) if i not in c) / 5
                n += abs(a - b) >= abs(t) - 1e-12
            self.assertEqual(an.split_test(dict(zip(an.TEN, x)))["splits_at_least_as_far"], n)


class CountedTest(unittest.TestCase):
    def test_unscored_asks_do_not_count_and_are_listed(self):
        rows = make_rows("g", FLAT, HALF)
        rows[0]["outcome"] = "void"
        asks, info = an.counted(rows, "g")
        self.assertEqual(len(asks), len(rows) - 1)
        self.assertEqual(info["records_by_version_and_outcome"][rows[0]["version"]]["void"], 1)

    def test_a_cell_one_of_the_ten_has_no_record_of_is_left_out_for_all(self):
        rows = make_rows("g", FLAT, HALF)
        gone = [r for r in rows if not (r["version"] == "2.1.318" and r["pass"] == 3 and r["unit"] == "item:q0")]
        asks, info = an.counted(gone, "g")
        self.assertFalse([r for r in asks if r["pass"] == 3 and r["unit"] == "item:q0"])
        self.assertEqual(info["cells_with_all_ten_versions"], info["cells"] - 1)
        # the eleventh version missing a record does not remove the cell
        gone = [r for r in rows if not (r["version"] == an.ELEVENTH and r["pass"] == 3 and r["unit"] == "item:q0")]
        self.assertEqual(an.counted(gone, "g")[1]["cells_with_all_ten_versions"], 18)

    def test_other_groups_and_passes_are_left_out(self):
        rows = make_rows("g", FLAT, HALF) + make_rows("other", FLAT, HALF)
        self.assertEqual(len(an.counted(rows, "g", passes={1})[0]), 11 * 6)


class ComparisonTest(unittest.TestCase):
    def test_half_the_thinking_is_minus_fifty_per_cent(self):
        think = {v: 1000 for v in an.EARLIER} | {v: 500 for v in an.LATER} | {an.ELEVENTH: 500}
        asks, _ = an.counted(make_rows("g", think, HALF), "g")
        c = an.one_comparison(asks, an.lthink, "thinking", is_test=True)
        self.assertAlmostEqual(c["change_in_geometric_mean_per_cent"], (501 / 1001 - 1) * 100, places=6)
        self.assertAlmostEqual(c["p"], 2 / 252)
        self.assertTrue(c["declared"])
        self.assertEqual(c["direction"], "later five lower")
        self.assertLess(c["ask_shuffle_for_comparison_only"]["p"], 0.01)

    def test_a_comparison_that_is_no_test_declares_nothing(self):
        think = {v: 1000 for v in an.EARLIER} | {v: 500 for v in an.LATER}
        asks, _ = an.counted(make_rows("g", think, HALF), "g")
        self.assertIsNone(an.one_comparison(asks, an.lthink, "thinking")["declared"])

    def test_accuracy_in_points(self):
        acc = {v: 1.0 for v in an.EARLIER} | {v: 0.0 for v in an.LATER}
        asks, _ = an.counted(make_rows("g", {v: 100 for v in an.TEN}, acc), "g")
        c = an.one_comparison(asks, an.correct, "accuracy", is_test=True)
        self.assertAlmostEqual(c["difference_points"], -100.0)
        self.assertEqual(c["range_points"], [-100.0, -100.0])

    def test_questions_weigh_the_same_when_a_version_lost_asks(self):
        rows = make_rows("g", FLAT, {v: 1.0 for v in FLAT}, units=2)
        for r in rows:  # version 2.1.317 is wrong on question 1 only
            if r["version"] == "2.1.317" and r["unit"] == "item:q1":
                r["score"] = 0.0
        # and loses two of its three asks on question 0 (voided)
        k = 0
        for r in rows:
            if r["version"] == "2.1.317" and r["unit"] == "item:q0" and k < 2:
                r["outcome"], k = "void", k + 1
        asks, _ = an.counted(rows, "g")
        c = an.one_comparison(asks, an.correct, "accuracy")
        self.assertAlmostEqual(c["version_values"]["2.1.317"], 0.5)  # (1.0 + 0.0) / 2, not 1 right out of 4 asks

    def test_a_question_one_version_has_no_scored_ask_for_is_left_out_for_all(self):
        rows = make_rows("g", FLAT, HALF)
        for r in rows:
            if r["version"] == "2.1.311" and r["unit"] == "item:q5":
                r["outcome"] = "error"
        asks, _ = an.counted(rows, "g")
        c = an.one_comparison(asks, an.lthink, "thinking")
        self.assertEqual(c["questions"], 5)
        self.assertEqual(c["questions_left_out"], ["item:q5"])

    def test_no_true_difference_is_rarely_declared(self):
        hits = 0
        for seed in range(60):
            asks, _ = an.counted(make_rows("g", FLAT, HALF, seed=seed, spread=0.7, units=8), "g")
            means = an.cell_means(asks, an.lthink)
            units, _ = an.common_units(means)
            values = {v: sum(means[v][u] for u in units) / len(units) for v in an.TEN}
            hits += an.split_test(values)["declared"]
        self.assertLessEqual(hits, 8)  # 5% of 60 is 3; 8 leaves room for luck

    def test_range_is_reproducible(self):
        asks, _ = an.counted(make_rows("g", FLAT, HALF, seed=5, spread=0.5), "g")
        a = an.one_comparison(asks, an.lthink, "thinking")
        b = an.one_comparison(asks, an.lthink, "thinking")
        self.assertEqual(a["range_per_cent"], b["range_per_cent"])
        self.assertEqual(a["ask_shuffle_for_comparison_only"], b["ask_shuffle_for_comparison_only"])


class ReportTest(unittest.TestCase):
    def test_xhigh_report_runs_and_marks_what_is_complete(self):
        think = {v: 2000 for v in an.EARLIER} | {v: 1500 for v in an.LATER} | {an.ELEVENTH: 1500}
        rows = make_rows("xhigh_recheck", think, HALF, passes=(1, 2, 3, 4, 5), units=6, seed=1, spread=0.3)
        kinds = {"a": {"item:q0", "item:q1"}, "b": {"item:q2"}}
        kinds["rest"] = {f"item:q{i}" for i in range(6)} - kinds["a"] - kinds["b"]
        rep = an.xhigh_report(rows, kinds, expected_units=6)
        self.assertTrue(rep["complete"])
        self.assertTrue(rep["test_1_thinking_at_xhigh"]["declared"])
        self.assertIsNone(rep["accuracy_all_questions_no_declaration"]["declared"])
        self.assertEqual(rep["version_2_1_323"]["mean_ln_thinking"]["nearer_to"], "later five")
        self.assertEqual(rep["versions"]["2.1.311"]["scored_asks"], 30)
        self.assertIn("TEST 1", an.text_report({"xhigh_recheck": rep}))
        cut = [r for r in rows if not (r["pass"] == 5 and r["unit"] in ("item:q4", "item:q5") and r["version"] > "2.1.316")]
        self.assertFalse(an.xhigh_report(cut, kinds, expected_units=6)["complete"])

    def test_high_report_uses_stage_1_for_test_2_and_both_stages_for_test_3(self):
        think = {v: 1000 for v in an.EARLIER} | {v: 800 for v in an.LATER} | {an.ELEVENTH: 800}
        acc = {v: 0.6 for v in an.EARLIER} | {v: 0.2 for v in an.LATER} | {an.ELEVENTH: 0.2}
        s1 = make_rows("high_recheck", think, acc, passes=tuple(range(1, 13)), units=4, seed=2)
        rep = an.high_report(s1, expected_units=4)
        self.assertFalse(rep["stage_2_sent"])
        self.assertNotIn("both_stages", rep)
        self.assertTrue(rep["stage_1"]["complete"])
        self.assertIsNone(rep["stage_1"]["D1_accuracy_stage_1"]["declared"])
        self.assertIn("stage 2 was not sent", an.text_report({"high_recheck": rep}))
        # stage 2 with the thinking difference turned around: test 2 must not move
        think2 = {v: 800 for v in an.EARLIER} | {v: 1000 for v in an.LATER} | {an.ELEVENTH: 1000}
        s2 = make_rows("high_recheck", think2, acc, passes=tuple(range(13, 25)), units=4, seed=3)
        rep2 = an.high_report(s1 + s2, expected_units=4)
        self.assertTrue(rep2["stage_2_sent"])
        self.assertEqual(rep2["stage_1"]["test_2_thinking_at_high_stage_1"]["T"], rep["stage_1"]["test_2_thinking_at_high_stage_1"]["T"])
        self.assertTrue(rep2["both_stages"]["test_3_accuracy_at_high_both_stages"]["declared"])
        self.assertEqual(rep2["both_stages"]["versions"]["2.1.311"]["scored_asks"], 24 * 4)
        self.assertIn("TEST 3", an.text_report({"high_recheck": rep2}))

    def test_version_rows(self):
        think = {v: 0 for v in an.TEN} | {an.ELEVENTH: 99}
        rows = make_rows("g", think, {v: 1.0 for v in think}, units=3)
        for r in rows:
            if r["version"] == "2.1.311" and r["unit"] == "item:q0":
                r["thinking_tokens"], r["tool_calls"] = 99, 2
        asks, info = an.counted(rows, "g")
        v = an.version_rows(asks, info)
        self.assertAlmostEqual(v["2.1.312"]["share_zero_thinking_per_cent"], 100.0)
        self.assertIsNone(v["2.1.312"]["thinking_geometric_mean_over_asks_above_zero"])
        self.assertAlmostEqual(v["2.1.311"]["share_zero_thinking_per_cent"], 200 / 3)
        self.assertAlmostEqual(v["2.1.311"]["thinking_geometric_mean_over_asks_above_zero"], 99.0)
        self.assertAlmostEqual(v["2.1.311"]["share_that_tried_a_tool_per_cent"], 100 / 3)
        self.assertAlmostEqual(v["2.1.311"]["thinking_geometric_mean_tokens"], math.exp(math.log(100) / 3) - 1)
        self.assertAlmostEqual(v[an.ELEVENTH]["accuracy_per_cent"], 100.0)


if __name__ == "__main__":
    unittest.main()
