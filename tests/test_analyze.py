"""analyze.py and judge.py on made-up rows: a hidden drop is found, a flat run is not, a resent ask
replaces the first one, and a pass that stopped early still counts cell by cell.

    python -B -m unittest discover -s tests          (from the program folder)
"""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import fake_rows  # noqa: E402
from ccversions import analyze, judge  # noqa: E402

FAST = 400  # shuffles; enough for these tests


class JudgeTests(unittest.TestCase):
    def test_segments_and_drop_direction(self):
        starts, ends = judge.segments(39)
        self.assertEqual(len(starts), 779)
        self.assertTrue(judge.has_drop(20, 38, -0.05, 39))    # low from version 21 to the end
        self.assertTrue(judge.has_drop(0, 19, 0.05, 39))      # the same split seen from the other side
        self.assertFalse(judge.has_drop(20, 38, 0.05, 39))    # high at the end: a rise only
        self.assertFalse(judge.has_drop(0, 19, -0.05, 39))
        self.assertTrue(judge.has_drop(10, 12, -0.1, 39) and judge.has_drop(10, 12, 0.1, 39))

    def test_a_rise_with_two_lucky_first_versions_is_not_called_a_drop(self):
        # versions 0 and 1 a little high by chance, 2 to 20 at the base, 21 to 38 six points higher:
        # the most marked segment is "2 to 20 low", whose place alone would read as a drop
        base = np.full((78, 3, 39), 0.60)
        base[:, :, 21:] = 0.66
        base[:, :, :2] = 0.615
        rng = np.random.default_rng(8)
        u = rng.random((400, 78, 3, 39))
        opened, named, shaped = 0, 0, 0
        for k in range(40):
            val = (u[k] < base).astype(float)
            res = judge.judge(val, min_effect=0.03, shuffles=60)
            shaped += res["drop_shape"]
            opened += res["has_drop"]
            named += res["drop_named"]
        self.assertLess(opened, shaped)          # the support check takes some of them away
        self.assertLessEqual(named, opened)
        self.assertLessEqual(named, 4)           # named a drop in a small share of the 40
        # a real step down from version 21 on keeps its name
        down = np.full((78, 3, 39), 0.64)
        down[:, :, 21:] = 0.56
        res = judge.judge((u[0] < down).astype(float), min_effect=0.03, shuffles=200)
        self.assertTrue(res["has_drop"] and res["drop_named"])

    def test_scan_equals_plain_accuracy_difference_on_full_data(self):
        rng = np.random.default_rng(3)
        val = (rng.random((78, 2, 39)) < 0.6).astype(float)
        res = judge.judge(val, min_effect=0.03, shuffles=200)
        a, b = res["best_start"], res["best_end"]
        inside = val[:, :, a:b + 1].mean()
        outside = np.delete(val, np.s_[a:b + 1], axis=2).mean()
        self.assertAlmostEqual(res["diff"], inside - outside, places=12)

    def test_missing_values_do_not_tilt_a_version(self):
        rng = np.random.default_rng(4)
        easy = np.repeat(np.linspace(0.05, 0.95, 78)[:, None, None], 2, axis=1)
        val = (rng.random((78, 2, 39)) < easy).astype(float)
        val[60:, :, 5] = np.nan  # version 5 lost its easiest items
        resid, mask = judge.residuals(val)
        score5 = resid[:, :, 5].sum() / mask[:, :, 5].sum()
        self.assertLess(abs(score5), 0.06)  # the plain accuracy would be about 15 points lower


class AnalyzeTests(unittest.TestCase):
    def test_hidden_drop_is_found_and_opens_the_third_pass(self):
        rows = fake_rows.make_rows(11, drop_from="2.1.303", drop_points=9, think_drop=0.25)
        rep, _ = analyze.analyze(rows, versions=fake_rows.VERSIONS, shuffles=FAST, interim=True)
        self.assertTrue(rep["accuracy"]["declared"], rep["accuracy"]["p"])
        self.assertTrue(rep["accuracy_difference_declared"])
        self.assertTrue(rep["accuracy"]["has_drop"])
        self.assertLessEqual(abs(fake_rows.VERSIONS.index(rep["accuracy"]["first_version"])
                                 - fake_rows.VERSIONS.index("2.1.303")), 3)
        self.assertTrue(rep["thinking_difference_declared"])
        self.assertLess(rep["thinking"]["effect_shown"], -0.1)
        self.assertTrue(rep["third_pass"]["open_third_pass"])
        self.assertEqual(rep["cells_that_count"], {"1": 78, "2": 78})
        low = rep["small_groups"]["effort_low"]["against_main_same_versions"]
        self.assertLess(low["thinking"]["ratio"], 0.6)
        self.assertEqual(len(rep["small_groups"]), 9)

    def test_a_version_the_server_refuses_is_left_out_and_does_not_block_the_third_pass(self):
        rows = fake_rows.make_rows(11, drop_from="2.1.303", drop_points=9, think_drop=0.25)
        for r in rows:
            if r["group"] == "main" and r["version"] == "2.1.281":
                r.update(outcome="error", reason="min_version", score=None, thinking_tokens=None)
        rep, out_rows = analyze.analyze(rows, versions=fake_rows.VERSIONS, shuffles=FAST, interim=True)
        self.assertEqual(rep["versions_refused_by_the_server"], ["2.1.281"])
        self.assertNotIn("2.1.281", rep["versions"])
        self.assertEqual(len(rep["versions"]), len(fake_rows.VERSIONS) - 1)
        self.assertEqual(rep["cells_that_count"], {"1": 78, "2": 78})
        self.assertTrue(rep["third_pass"]["quality_ok"])
        self.assertTrue(rep["third_pass"]["open_third_pass"])
        self.assertTrue(rep["accuracy_difference_declared"])      # the two ways of counting still agree
        self.assertEqual(len(out_rows), len(rows))                # its rows stay in the public table
        self.assertIn({"version": "2.1.281", "pass": 1, "outcome": "error",
                       "reason": "min_version (out of the comparison)", "asks": 78}, rep["errors_and_voids"])
        first = rep["per_version"][0]
        self.assertGreater(first["thinking_tokens_geometric_mean"], 0)
        self.assertGreaterEqual(first["thinking_tokens_median"], 0)
        self.assertIsNotNone(first["asks_with_no_thinking"])
        self.assertGreaterEqual(first["asks_that_tried_tools"], 0)
        self.assertIn("2.1.281", analyze.report_text(rep))

    def test_flat_run_declares_nothing(self):
        rows = fake_rows.make_rows(5)
        rep, _ = analyze.analyze(rows, versions=fake_rows.VERSIONS, shuffles=FAST, interim=True)
        self.assertFalse(rep["accuracy_difference_declared"])
        self.assertFalse(rep["thinking_difference_declared"])
        self.assertGreater(rep["accuracy"]["p"], 0.05)
        f = rep["figure"]["accuracy"]
        self.assertTrue(f["band_bottom"] < min(f["mean"]) + 0.03 and f["band_top"] > max(f["mean"]) - 0.03)

    def test_resent_ask_replaces_the_first_one(self):
        rows = fake_rows.make_rows(5)
        first = next(r for r in rows if r["group"] == "main" and r["outcome"] == "scored")
        first.update(outcome="error", reason="failed", score=None, thinking_tokens=None)
        again = {**first, "plan": "F1r", "ask_id": "r1b000o00001", "outcome": "scored", "reason": None,
                 "score": 1.0, "thinking_tokens": 300, "output_tokens": 500,
                 "resend_of": {"plan": first["plan"], "ask_id": first["ask_id"]}}
        merged = analyze.apply_resends(rows + [again])
        self.assertEqual(len(merged), len(rows))
        hit = next(r for r in merged if r["version"] == first["version"] and r["unit"] == first["unit"]
                   and r["pass"] == first["pass"] and r["group"] == "main")
        self.assertTrue(hit["resent"] and hit["score"] == 1.0 and hit["plan"] == first["plan"])

    def test_pass_that_stopped_early_counts_cell_by_cell(self):
        rows = fake_rows.make_rows(7, passes=3, skip_last_blocks=20)  # the third pass has 6 of 26 blocks
        rows = [r for r in rows if not (r["pass"] == 3 and r["block"] == 5 and r["version"] == "2.1.322")]
        rep, _ = analyze.analyze(rows, versions=fake_rows.VERSIONS, shuffles=FAST)
        self.assertEqual(rep["cells_that_count"], {"1": 78, "2": 78, "3": 15})  # block 5 is not complete
        third = next(p for p in rep["accuracy"]["per_pass"] if p["pass"] == 3)
        self.assertFalse(third["counts_for_sign"])


if __name__ == "__main__":
    unittest.main()
