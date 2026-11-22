"""Tests of new_passes_numbers.py on made-up rows, made-up readers' tables and a made-up code table. No data of
the trial is read.

    python -B -m unittest test_new_passes_numbers        (from this folder)
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import new_passes_numbers as npn  # noqa: E402

HOLDS = npn.HOLDS
MORE = npn.VERDICTS[1]
MISSING = npn.VERDICTS[3]


def key_table(n=10):
    return [{"code": f"T{i + 1:03d}", "batch": "AB"[i % 2], "question_id": 1000 + i, "key": "A"} for i in range(n)]


def item(i):
    return f"mmlupro-{1000 + i}"


def asks(spec: dict, group=npn.GROUP) -> list[dict]:
    """spec: {item index: [(thinking tokens, score), ...]}; one ask per pass, passes 1..len."""
    out, n = [], 0
    for i, lst in spec.items():
        for p, (t, s) in enumerate(lst, 1):
            n += 1
            out.append({"plan": f"SN{p}", "ask_id": f"a{n:04d}", "pass": p, "group": group, "unit": f"item:{item(i)}",
                        "outcome": "scored", "thinking_tokens": t, "score": s, "elapsed_seconds": 10.0,
                        "started_at": f"2026-11-23T00:{n // 60:02d}:{n % 60:02d}+00:00", "weekly_utilization": 0.2 + n / 1000})
    return out


def judged(verdicts: dict, answers: dict | None = None) -> dict:
    kt = {k["question_id"]: k for k in key_table()}
    return {item(i): {"code": kt[1000 + i]["code"], "batch": "A", "key": "A", "verdict": v,
                      "my_answer": (answers or {}).get(i, "A"), "confidence": "高", "recognized": "否"}
            for i, v in verdicts.items()}


NO_PROBLEMS = {"unknown_codes": [], "repeated_codes": [], "bad_verdicts": [], "missing_columns": {}}


def always(t=500, s=1.0):
    return [(t, s)] * 5


class Numbers(unittest.TestCase):
    def test_m_is_k_times_n_minus_k_over_n_times_n_minus_1(self):
        # k = 0, 1, 2, 3, 4, 5 and four more with k = 0: pq = 0, .2, .3, .3, .2, 0, 0, 0, 0, 0 -> mean 0.1
        spec = {i: [(0, 1.0)] * k + [(400, 1.0)] * (5 - k) for i, k in enumerate([0, 1, 2, 3, 4, 5])}
        spec |= {i: always() for i in range(6, 10)}
        n = npn.numbers(asks(spec), [item(i) for i in range(10)], set())
        self.assertAlmostEqual(n["M"]["M"], 0.1)
        self.assertEqual(n["k_items_with_five_scored_asks"], {"0": 5, "1": 1, "2": 1, "3": 1, "4": 1, "5": 1})
        self.assertAlmostEqual(n["share_without_thinking"], 15 / 50)
        lo, hi = n["M"]["range_90"]
        self.assertLessEqual(lo, 0.1)
        self.assertGreaterEqual(hi, 0.1)

    def test_m_is_unbiased_over_many_draws(self):
        import numpy as np
        rng = np.random.default_rng(1)
        p = np.array([0.0] * 150 + [0.1] * 25 + [0.5] * 25)
        truth = float(np.mean(p * (1 - p)))
        ests = []
        for _ in range(400):
            k = rng.binomial(5, p)
            spec = {i: [(0, 1.0)] * int(k[i]) + [(300, 1.0)] * (5 - int(k[i])) for i in range(200)}
            ests.append(npn.numbers(asks(spec), [item(i) for i in range(200)], set())["M"]["M"])
        self.assertAlmostEqual(float(np.mean(ests)), truth, delta=0.0015)

    def test_an_item_with_fewer_asks_uses_its_own_n_and_one_ask_is_left_out(self):
        spec = {0: [(0, 1.0), (300, 1.0), (300, 1.0)], 1: [(0, 1.0)], 2: always()}
        n = npn.numbers(asks(spec), [item(i) for i in range(3)], set())
        self.assertAlmostEqual(n["M"]["M"], (1 * 2 / 6 + 0) / 2)
        self.assertEqual(n["M"]["items"], 2)
        self.assertEqual(n["items_by_scored_asks"], {"1": 1, "3": 1, "5": 1})
        self.assertEqual(sum(n["k_items_with_five_scored_asks"].values()), 1)

    def test_thinking_medians_spread_and_long_items(self):
        spec = {0: [(100, 1.0), (200, 1.0), (300, 1.0), (0, 1.0), (0, 1.0)],   # median of thinking asks 200
                1: [(2000, 1.0)] * 5,                                            # 2000: above 1,000
                2: [(0, 1.0)] * 5}                                               # never thought: no median
        n = npn.numbers(asks(spec), [item(i) for i in range(3)], set())
        self.assertEqual(n["median_thinking_per_item"]["n"], 2)
        self.assertEqual(n["median_thinking_per_item"]["min"], 200)
        self.assertEqual(n["items_median_thinking_above_1000"], 1)
        self.assertEqual(n["items_that_thought"], 2)
        import math
        import statistics
        self.assertAlmostEqual(n["sd_ln_thinking_per_item"]["min"], 0.0)  # item 1: five equal values
        self.assertAlmostEqual(n["sd_ln_thinking_per_item"]["max"], statistics.stdev([math.log(x) for x in (100, 200, 300)]))

    def test_right_and_wrong_split_by_thinking(self):
        spec = {0: [(300, 1.0), (300, 0.0), (300, 1.0), (0, 1.0), (0, 1.0)],   # a thought ask wrong
                1: [(0, 0.0), (300, 1.0), (300, 1.0), (300, 1.0), (300, 1.0)],   # an ask without thinking wrong
                2: [(300, 0.0)] * 5,                                             # never right
                3: always()}
        n = npn.numbers(asks(spec), [item(i) for i in range(4)], {item(2)})
        self.assertEqual(n["items_thought_not_all_correct"], [item(0), item(2)])
        self.assertEqual(n["items_without_thinking_with_a_wrong_ask"], [item(1)])
        self.assertEqual(n["items_never_right"], [item(2)])
        self.assertAlmostEqual(n["share_correct_thought"], 11 / 17)  # 3 + 4 + 5 + 5 asks thought, 2 + 4 + 0 + 5 right
        self.assertAlmostEqual(n["share_correct_without_thinking"], 2 / 3)
        self.assertEqual(n["thinking_flagged_vs_rest"]["direction"], "equal")

    def test_higher_or_lower(self):
        spec = {0: always(900), 1: always(100), 2: always(100), 3: always(120)}
        n = npn.numbers(asks(spec), [item(i) for i in range(4)], {item(0)})
        self.assertEqual(n["thinking_flagged_vs_rest"]["direction"], "higher")
        self.assertEqual(n["thinking_flagged_vs_rest"]["median"], 900)
        self.assertEqual(n["thinking_flagged_vs_rest"]["other_median"], 100)

    def test_asks_that_are_not_scored_do_not_count(self):
        rows = asks({0: always(), 1: always()})
        rows[0]["outcome"] = "error"
        rows[1]["outcome"] = "void"
        n = npn.numbers(rows, [item(0), item(1)], set())
        self.assertEqual(n["scored_asks"], 8)
        self.assertEqual(n["items_by_scored_asks"], {"3": 1, "5": 1})

    def test_a_resend_takes_the_place_of_its_ask(self):
        rows = asks({0: always(), 1: always()})
        rows[0]["outcome"] = "error"
        rows.append({**rows[0], "plan": "SN1r", "ask_id": "r1", "outcome": "scored", "thinking_tokens": 0,
                     "resend_of": {"plan": rows[0]["plan"], "ask_id": rows[0]["ask_id"]}})
        n = npn.numbers(npn.apply_resends(rows), [item(0), item(1)], set())
        self.assertEqual(n["scored_asks"], 10)
        self.assertEqual(n["asks_without_thinking"], 1)


class Section7(unittest.TestCase):
    def band(self, m, lo, hi):
        return npn.section_7({"M": m, "range_90": [lo, hi]}, 0.2, True)["point_1_usable"]

    def test_bands_and_lines(self):
        self.assertEqual(self.band(0.006, 0.0055, 0.007)["band_that_counts"], "usable")
        self.assertEqual(self.band(0.005, 0.005, 0.006)["band_that_counts"], "usable")
        self.assertEqual(self.band(0.003, 0.0025, 0.0035)["band_that_counts"], "marginal")
        self.assertEqual(self.band(0.002, 0.002, 0.0021)["band_that_counts"], "marginal")
        self.assertEqual(self.band(0.0015, 0.001, 0.0019)["band_that_counts"], "not usable as it is")

    def test_the_band_of_M_counts_and_a_range_across_a_line_is_reported(self):
        b = self.band(0.006, 0.004, 0.008)
        self.assertTrue(b["range_crosses_a_line"])
        self.assertEqual(b["band_of_M"], "usable")
        self.assertEqual(b["band_that_counts"], "usable")
        self.assertEqual((b["band_of_range_low"], b["band_of_range_high"]), ("marginal", "usable"))
        wide = self.band(0.006, 0.0015, 0.009)
        self.assertEqual(wide["band_that_counts"], "usable")
        self.assertEqual(wide["band_of_range_low"], "not usable as it is")
        low = self.band(0.0015, 0.0, 0.004)
        self.assertEqual(low["band_that_counts"], "not usable as it is")
        self.assertTrue(low["range_crosses_a_line"])
        self.assertFalse(self.band(0.006, 0.0055, 0.007)["range_crosses_a_line"])

    def test_point_2(self):
        over = npn.section_7({"M": 0.006, "range_90": [0.006, 0.006]}, 0.55, True)["point_2_reading"]
        self.assertTrue(over["more_than_half"])
        self.assertIsNone(over["pool_left_at_this_share"])
        half = npn.section_7({"M": 0.006, "range_90": [0.006, 0.006]}, 0.5, True)["point_2_reading"]
        self.assertFalse(half["more_than_half"])
        self.assertAlmostEqual(half["pool_left_at_this_share"], npn.POOL * 0.5)
        self.assertAlmostEqual(half["pool_without_the_trial_items_left_at_this_share"], (npn.POOL - 200) * 0.5)


class Readers(unittest.TestCase):
    def write(self, tmp: Path, name: str, rows: list[list[str]]) -> Path:
        p = tmp / name
        p.write_text("\t".join(npn.JUDGMENT_COLUMNS) + "\n" + "".join("\t".join(r) + "\n" for r in rows), encoding="utf-8")
        return p

    def test_tables_codes_and_problems(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            a = self.write(t, "A.tsv", [["T001", "A", "高", HOLDS, "", "否"], ["T003", "B", "中", MORE, "B and C", "否"],
                                        ["T999", "A", "高", HOLDS, "", "否"]])
            b = self.write(t, "B.tsv", [["T002", "A", "高", "站不住", "", "否"], ["T001", "A", "高", HOLDS, "", "否"]])
            j, problems = npn.readers([a, b], key_table())
        self.assertEqual(set(j), {item(0), item(1), item(2)})
        self.assertEqual(problems["unknown_codes"], ["T999"])
        self.assertEqual(problems["repeated_codes"], ["T001"])
        self.assertEqual(problems["bad_verdicts"], [{"code": "T002", "verdict": "站不住"}])

    def test_report_splits_flagged_and_marks_incomplete_reading(self):
        spec = {i: always() for i in range(10)}
        spec[0] = [(0, 1.0)] * 2 + [(300, 1.0)] * 3
        j = judged({i: HOLDS for i in range(8)} | {8: MORE}, answers={1: "B"})  # item 9 not read
        rep = npn.report(asks(spec), key_table(), j, NO_PROBLEMS, None)
        self.assertEqual(rep["reading"]["flagged"], 1)
        self.assertEqual(rep["reading"]["items_not_read"], [item(9)])
        self.assertFalse(rep["reading"]["complete"])
        self.assertEqual(rep["not_flagged"]["items"], 8)
        self.assertEqual(rep["all_200"]["items"], 10)
        self.assertAlmostEqual(rep["not_flagged"]["M"]["M"], 0.3 / 8)
        self.assertTrue(rep["section_7"]["point_1_usable"]["provisional_readers_not_complete"])
        self.assertEqual(rep["reading"]["holds_but_reader_answer_differs_from_key"], [item(1)])
        self.assertEqual(rep["section_8_lists"]["to_check"], [item(1)])
        self.assertFalse(rep["reading"]["main_conversation_reads"]["given"])

    def test_main_conversation_reads(self):
        j = judged({i: (HOLDS if i < 6 else MISSING) for i in range(10)})
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "reads.tsv"
            p.write_text("code\tclear_flaw\nT007\tyes\nT008\t否\nT009\t是\nT010\tno\nT001\t\n", encoding="utf-8")
            reads = npn.main_reads(p, key_table())
        rep = npn.report(asks({i: always() for i in range(10)}), key_table(), j, NO_PROBLEMS, reads)
        mr = rep["reading"]["main_conversation_reads"]
        self.assertEqual((mr["flagged_items"], mr["flagged_items_read"], mr["clear_flaw"]), (4, 4, 2))
        self.assertAlmostEqual(mr["share_with_a_clear_flaw"], 0.5)
        self.assertTrue(mr["read_enough"])
        self.assertAlmostEqual(rep["reading"]["share_flagged"], 0.4)
        self.assertAlmostEqual(rep["section_7"]["point_2_reading"]["pool_left_at_this_share"], npn.POOL * 0.6)
        self.assertEqual(mr["read_but_not_flagged"], [])  # T001 has no label: not read

    def test_main_conversation_reads_with_its_own_column_and_labels(self):
        j = judged({i: (HOLDS if i < 5 else MORE) for i in range(10)})
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "reads.tsv"
            p.write_text("code\tquestion_id\tverdict\t判断\nT006\t1005\tx\t真毛病\nT007\t1006\tx\t说不准\n"
                         "T008\t1007\tx\t真毛病\n", encoding="utf-8")
            reads = npn.main_reads(p, key_table(), column="判断", yes=("真毛病",))
            with self.assertRaises(SystemExit):
                npn.main_reads(p, key_table())  # no column clear_flaw
        mr = npn.report(asks({i: always() for i in range(10)}), key_table(), j, NO_PROBLEMS, reads,
                        yes=("真毛病",))["reading"]["main_conversation_reads"]
        self.assertEqual((mr["flagged_items"], mr["flagged_items_read"], mr["clear_flaw"]), (5, 3, 2))
        self.assertEqual(mr["labels"], {"真毛病": 2, "说不准": 1})
        self.assertFalse(mr["read_enough"])  # fewer than 30 flagged: all 5 had to be read

    def test_command_line_end_to_end(self):
        spec = {i: always(1500 if i == 3 else 400) for i in range(10)}
        spec[2] = [(0, 1.0)] + [(300, 1.0)] * 4
        rows = asks(spec)
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            (t / "g1.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows if r["pass"] <= 2))
            (t / "g2.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows if r["pass"] > 2))
            (t / "keys.json").write_text(json.dumps(key_table()))
            a = self.write(t, "A.tsv", [[f"T{i:03d}", "A", "高", HOLDS, "", "否"] for i in (1, 3, 5, 7, 9)])
            b = self.write(t, "B.tsv", [[f"T{i:03d}", "A", "高", HOLDS if i != 10 else MORE, "", "否"] for i in (2, 4, 6, 8, 10)])
            out = subprocess.run([sys.executable, "-B", str(HERE / "new_passes_numbers.py"), "--graded", str(t / "g1.jsonl"),
                                  "--graded", str(t / "g2.jsonl"), "--judgments", str(a), "--judgments", str(b),
                                  "--key-table", str(t / "keys.json"), "--out", str(t / "out")], capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            rep = json.loads((t / "out" / "report.json").read_text())
            self.assertTrue(rep["reading"]["complete"])
            self.assertEqual(rep["all_200"]["scored_asks"], 50)
            self.assertEqual(rep["all_200"]["items_median_thinking_above_1000"], 1)
            self.assertAlmostEqual(rep["all_200"]["M"]["M"], 0.2 / 10)
            self.assertAlmostEqual(rep["not_flagged"]["M"]["M"], 0.2 / 9)
            self.assertEqual(rep["section_7"]["point_1_usable"]["band_of_M"], "usable")
            self.assertEqual(len((t / "out" / "per_item.tsv").read_text().splitlines()), 11)
            self.assertIn("BAND THAT COUNTS", out.stdout)
            self.assertEqual(rep["time_and_usage"]["asks"], 50)
            self.assertAlmostEqual(rep["time_and_usage"]["weekly_reading_moved"], 0.049)


if __name__ == "__main__":
    unittest.main()
