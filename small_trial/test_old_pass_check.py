"""Tests of old_pass_check.py on made-up rows and a made-up mid November table. No data of the trial is read.

    python -B -m unittest test_old_pass_check        (from this folder)
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import old_pass_check as opc  # noqa: E402

FIVE = opc.FIVE
OFTEN = ("mmlupro-574", "mmlupro-594", "gpqa-a", "gpqa-b", "gpqa-c", "gpqa-d", "gpqa-e", "gpqa-f",
         "mmlupro-1", "mmlupro-2")  # 10 items that sometimes think in mid November
ALWAYS = tuple(f"item{n:02d}" for n in range(63))


def table() -> dict:
    """78 items: the five, 10 sometimes, 63 always. Medians: 0 for the five, 100 for the rest, 0 for 574."""
    mid = {i: {"share_without": 0.95, "median": 0.0} for i in FIVE}
    mid |= {i: {"share_without": 0.3, "median": 100.0} for i in OFTEN}
    mid["mmlupro-574"] = {"share_without": 0.86, "median": 0.0}
    mid |= {i: {"share_without": 0.0, "median": 200.0} for i in ALWAYS}
    return mid


def rows(mid, tokens=None, outcome=None, group="small_trial_old") -> list[dict]:
    """One scored ask per item. Default tokens: 0 for the five, 1.0 x the median for the rest."""
    tokens = tokens or {}
    out = []
    for n, i in enumerate(sorted(mid)):
        t = tokens.get(i, 0 if i in FIVE else (mid[i]["median"] or 50.0))
        out.append({"plan": "SO1", "ask_id": f"a{n:03d}", "group": group, "unit": f"item:{i}",
                    "outcome": (outcome or {}).get(i, "scored"), "thinking_tokens": t, "score": 1.0})
    return out


class OldPassCheck(unittest.TestCase):
    def setUp(self):
        self.mid = table()
        self.assertEqual(len(self.mid), 78)

    def test_everything_as_in_mid_november_matches(self):
        rep = opc.check(rows(self.mid), self.mid)
        self.assertTrue(rep["matches"], rep)
        self.assertAlmostEqual(rep["condition_4_thinking_ratio"]["geometric_mean"], 1.0)
        # 574 thought but has a median of 0: left out of condition 4, named
        self.assertEqual([x["item"] for x in rep["condition_4_thinking_ratio"]["left_out_median_zero"]], ["mmlupro-574"])
        self.assertEqual(rep["condition_3_always_thinking"]["items_always_thinking_in_mid_november"], 63)

    def test_one_item_without_a_scored_ask_is_allowed_two_are_not(self):
        one = opc.check(rows(self.mid, outcome={"item05": "void"}), self.mid)
        self.assertTrue(one["condition_1_scored_with_tokens"]["holds"])
        self.assertEqual(one["condition_1_scored_with_tokens"]["items_with_a_scored_ask"], 77)
        self.assertEqual(one["condition_1_scored_with_tokens"]["items_without_a_scored_ask"], ["item05"])
        self.assertTrue(one["matches"], one)
        two = opc.check(rows(self.mid, outcome={"item05": "void", "item06": "error"}), self.mid)
        self.assertFalse(two["condition_1_scored_with_tokens"]["holds"])
        self.assertEqual(two["condition_1_scored_with_tokens"]["items_without_a_scored_ask"], ["item05", "item06"])
        self.assertFalse(two["matches"])

    def test_a_missing_token_count_breaks_condition_1(self):
        r = rows(self.mid)
        r[10]["thinking_tokens"] = None
        rep = opc.check(r, self.mid)
        self.assertFalse(rep["condition_1_scored_with_tokens"]["holds"])
        self.assertFalse(rep["matches"])

    def test_a_missing_item_counts_like_an_ask_that_is_not_scored(self):
        one = opc.check([x for x in rows(self.mid) if x["unit"] != "item:item07"], self.mid)
        self.assertEqual(one["condition_1_scored_with_tokens"]["items_without_a_scored_ask"], ["item07"])
        self.assertTrue(one["matches"])
        two = opc.check([x for x in rows(self.mid) if x["unit"] not in ("item:item07", "item:item08")], self.mid)
        self.assertFalse(two["matches"])

    def test_an_item_of_the_five_without_a_scored_ask_cannot_count_in_condition_2(self):
        # one of the five not scored (allowed by condition 1) and one more of the five thinking: 3 of 5
        rep = opc.check(rows(self.mid, tokens={FIVE[1]: 300}, outcome={FIVE[0]: "void"}), self.mid)
        self.assertTrue(rep["condition_1_scored_with_tokens"]["holds"])
        self.assertEqual(rep["condition_2_five_rarely_thinking"]["without_thinking_now"], 3)
        self.assertFalse(rep["matches"])

    def test_rows_that_are_not_one_pass_of_the_78_do_not_match(self):
        r = rows(self.mid)
        twice = opc.check(r + [dict(r[3], ask_id="extra")], self.mid)
        self.assertEqual(twice["rows_are_one_pass_of_the_78"]["items_with_more_than_one_ask"], [opc.item_of(r[3])])
        self.assertFalse(twice["matches"])
        stranger = opc.check(r + [dict(r[3], unit="item:not-in-the-table", ask_id="x")], self.mid)
        self.assertEqual(stranger["rows_are_one_pass_of_the_78"]["items_not_in_the_table"], ["not-in-the-table"])
        self.assertFalse(stranger["matches"])
        small = {i: v for n, (i, v) in enumerate(self.mid.items()) if n}  # a table of 77 items
        self.assertFalse(opc.check(rows(small), small)["rows_are_one_pass_of_the_78"]["holds"])

    def test_a_resend_takes_the_place_of_the_failed_ask(self):
        r = rows(self.mid, outcome={"item05": "error", "item06": "error"})
        self.assertFalse(opc.check(opc.apply_resends(r), self.mid)["matches"])
        for i in ("item05", "item06"):
            failed = next(x for x in r if x["unit"] == f"item:{i}")
            r.append({**failed, "plan": "SO1r", "ask_id": f"r-{i}", "outcome": "scored", "thinking_tokens": 200.0,
                      "resend_of": {"plan": "SO1", "ask_id": failed["ask_id"]}})
        rep = opc.check(opc.apply_resends(r), self.mid)
        self.assertTrue(rep["matches"], rep)
        self.assertEqual(rep["resent_asks"], 2)
        self.assertEqual(rep["condition_1_scored_with_tokens"]["items_with_a_scored_ask"], 78)

    def test_four_of_the_five_is_enough_three_is_not(self):
        four = opc.check(rows(self.mid, tokens={FIVE[0]: 300}), self.mid)
        self.assertTrue(four["condition_2_five_rarely_thinking"]["holds"])
        self.assertEqual(four["condition_2_five_rarely_thinking"]["without_thinking_now"], 4)
        three = opc.check(rows(self.mid, tokens={FIVE[0]: 300, FIVE[1]: 300}), self.mid)
        self.assertFalse(three["condition_2_five_rarely_thinking"]["holds"])
        self.assertFalse(three["matches"])

    def test_two_always_thinking_items_without_thinking_is_allowed_three_is_not(self):
        two = opc.check(rows(self.mid, tokens={"item01": 0, "item02": 0}), self.mid)
        self.assertTrue(two["condition_3_always_thinking"]["holds"])
        three = opc.check(rows(self.mid, tokens={"item01": 0, "item02": 0, "item03": 0}), self.mid)
        self.assertFalse(three["condition_3_always_thinking"]["holds"])
        self.assertEqual(three["condition_3_always_thinking"]["of_those_without_thinking_now"], ["item01", "item02", "item03"])

    def test_the_ratio_band_and_its_edges(self):
        def at(factor):
            t = {i: self.mid[i]["median"] * factor for i in ALWAYS + OFTEN if self.mid[i]["median"] > 0}
            return opc.check(rows(self.mid, tokens=t), self.mid)["condition_4_thinking_ratio"]
        self.assertTrue(at(0.75)["holds"])
        self.assertTrue(at(1.33)["holds"])
        self.assertFalse(at(0.74)["holds"])
        self.assertFalse(at(1.34)["holds"])
        self.assertAlmostEqual(at(1.2)["geometric_mean"], 1.2)

    def test_the_mean_is_geometric(self):
        # half the items at 2x, half at 0.5x: geometric mean 1, arithmetic mean 1.25
        used = [i for i in ALWAYS + OFTEN if self.mid[i]["median"] > 0]
        t = {i: self.mid[i]["median"] * (2.0 if n % 2 else 0.5) for n, i in enumerate(used)}
        c4 = opc.check(rows(self.mid, tokens=t), self.mid)["condition_4_thinking_ratio"]
        self.assertEqual(len(used) % 2, 0)
        self.assertAlmostEqual(c4["geometric_mean"], 1.0)
        self.assertTrue(c4["holds"])

    def test_rows_of_another_group_are_not_read(self):
        r = rows(self.mid) + [{**x, "group": "other", "thinking_tokens": 0} for x in rows(self.mid)]
        self.assertTrue(opc.check(r, self.mid)["matches"])

    def test_command_line_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            (t / "graded.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows(self.mid)))
            lines = ["item\t" + opc.SHARE_COL + "\t" + opc.MEDIAN_COL]
            lines += [f"{i}\t{v['share_without']}\t{v['median']}" for i, v in self.mid.items()]
            (t / "mid.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
            out = subprocess.run([sys.executable, "-B", str(HERE / "old_pass_check.py"), "--graded", str(t / "graded.jsonl"),
                                  "--mid-november", str(t / "mid.tsv"), "--out", str(t / "out")],
                                 capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertIn("MATCHES MID NOVEMBER: yes", out.stdout)
            self.assertTrue(json.loads((t / "out" / "report.json").read_text())["matches"])


if __name__ == "__main__":
    unittest.main()
