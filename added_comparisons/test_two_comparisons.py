"""Self-tests of time_of_day.py and desktop_vs_cli.py, on made-up data (fake_data.py) and on the rehearsal's
graded rows (本机数据/演练_20261111, which do not count in the experiment). Nothing here reads the registered
run, the Desktop group's records or their raw records, and every output goes to a temporary folder.

    python -B test_two_comparisons.py -v

(from this folder). It takes a minute or two.
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
import desktop_vs_cli as D  # noqa: E402
import fake_data  # noqa: E402
import time_of_day as T  # noqa: E402
from common import analyze  # noqa: E402

REHEARSAL = common.DATA / "演练_20261111" / "graded" / "R1" / "graded.jsonl"
V = fake_data.VERSIONS
UTC = timezone.utc


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


class Guarded(unittest.TestCase):
    """Points the default paths of the run at empty temporary folders for the length of each test, so that no
    test can read the registered run even if it calls a program without --graded."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self._saved = (common.FORMAL_FINAL_REPORT, common.FORMAL_GRADED, common.DESKTOP_ASKS, common.OUT_DEFAULT)
        common.FORMAL_FINAL_REPORT = tmp / "no_final" / "report.json"
        common.FORMAL_GRADED = tmp / "no_graded"
        common.DESKTOP_ASKS = tmp / "no_desktop"
        common.OUT_DEFAULT = tmp / "no_out"
        self.tmp = tmp

    def tearDown(self):
        common.FORMAL_FINAL_REPORT, common.FORMAL_GRADED, common.DESKTOP_ASKS, common.OUT_DEFAULT = self._saved
        self._tmp.cleanup()


# ------------------------------------------------------------------------------------ US working hours

class HoursTests(unittest.TestCase):
    def test_edges_of_us_working_hours(self):
        cases = {"2026-11-11T13:59:59.000+00:00": False,   # Wednesday, before 9 am US Eastern
                 "2026-11-11T14:00:00.000+00:00": True,
                 "2026-11-12T00:59:59Z": True,             # Thursday 00:59 UTC belongs to Wednesday
                 "2026-11-12T01:00:00Z": False,
                 "2026-11-14T00:30:00Z": True,             # Saturday 00:30 UTC is Friday 4:30 pm US Pacific
                 "2026-11-14T14:30:00Z": False,            # Saturday
                 "2026-11-16T00:30:00Z": False,            # Monday 00:30 UTC is still Sunday in the US
                 "2026-11-12T01:30:00+11:00": True}        # Melbourne time, 14:30 UTC on Wednesday
        for ts, want in cases.items():
            self.assertEqual(common.in_us_hours(ts), want, ts)


# ------------------------------------------------------------------------------------ the fit itself

class FitTests(unittest.TestCase):
    def _cells(self, d, d_by_pass=None):
        import random
        rng = random.Random(4)
        a = {f"item:x-{i:02d}": rng.gauss(0.6, 0.2) for i in range(30)}
        b = {1: 0.0, 2: -0.03, 3: 0.02}
        cl = []
        for u, au in a.items():
            for p, bp in b.items():
                s = rng.choice([0.0, 1.0, rng.random()]) if p < 3 else 0.0
                dd = (d_by_pass or {}).get(p, d)
                cl.append({"unit": u, "pass": p, "y": au + bp + dd * s, "share_inside": s, "asks": []})
        return cl

    def test_exact_cells_give_back_d_and_the_pass_gap(self):
        lay = T.Layout(self._cells(0.05))
        one = T.fit_one_d(lay)
        self.assertTrue(one["identifiable"])
        self.assertAlmostEqual(one["d"], 0.05, places=10)
        self.assertAlmostEqual(one["largest_gap_between_passes"], 0.05, places=10)  # 0.02 - (-0.03)
        parts = T.fit_parts(lay)
        self.assertEqual(parts["passes_without_own_d"], ["3"])                       # pass 3 is all outside
        for p in ("1", "2"):
            self.assertAlmostEqual(parts["d_by_pass"][p], 0.05, places=10)

    def test_one_d_per_pass(self):
        lay = T.Layout(self._cells(0.0, {1: 0.04, 2: -0.02}))
        parts = T.fit_parts(lay)
        self.assertAlmostEqual(parts["d_by_pass"]["1"], 0.04, places=10)
        self.assertAlmostEqual(parts["d_by_pass"]["2"], -0.02, places=10)


# ------------------------------------------------------------------------------------ time of day

class TimeOfDayTests(Guarded):
    def test_a_known_difference_is_found(self):
        units = fake_data.fake_units()
        rows = fake_data.make_main_rows(units, seed=11, inside_points=0.08, inside_think=-0.25)
        rep = T.analyse(rows, V, shuffles=2000, draws=1000)
        self.assertEqual(rep["cells_that_count"], {"1": 78, "2": 78, "3": 78})
        main = rep["share_inside_by_pass"]["main"]
        self.assertAlmostEqual(main["1"]["share_inside"], 0.63, delta=0.02)
        self.assertAlmostEqual(main["2"]["share_inside"], 0.49, delta=0.02)
        self.assertEqual(main["3"]["share_inside"], 0.0)
        a, t = rep["metrics"]["accuracy"], rep["metrics"]["log_thinking"]
        # the true accuracy difference is a little under 8 points, as answers cannot be right more than always.
        # Over 30 made-up runs the fit averaged 7.7 points (spread 1.1) and -0.293 in log thinking (spread 0.026)
        self.assertAlmostEqual(a["d"], 0.077, delta=0.035)
        self.assertAlmostEqual(t["d"], math.log(0.75), delta=0.1)
        self.assertLess(a["range_95"][0], a["d"])
        self.assertGreater(a["range_95"][1], a["d"])
        self.assertEqual(a["passes_without_own_d"], ["3"])
        self.assertEqual(sorted(a["parts"]), ["1", "2"])
        self.assertEqual(a["wording_name"], "clear")
        self.assertEqual(t["wording_name"], "clear")
        self.assertEqual(rep["accuracy_wording"]["wording_name"], "clear")
        self.assertLess(t["d_shown"], -0.1)
        # every ask inside US working hours is on Wednesday 11 November, as the two limit sentences say
        self.assertEqual(list(rep["us_days_of_inside_asks"]), ["2026-11-11"])
        self.assertNotIn("warning", rep)

    def test_exact_cells_from_rows(self):
        units = fake_data.fake_units()
        rep = T.analyse(fake_data.make_exact_rows(units, d_count=3), V, shuffles=1000, draws=200)
        a = rep["metrics"]["accuracy"]
        self.assertAlmostEqual(a["d"], 3 / 39, places=10)
        self.assertAlmostEqual(a["largest_gap_between_passes"], 2 / 39, places=10)
        self.assertTrue(a["larger_than_pass_gap"])
        self.assertLess(a["p"], 0.05)
        t = rep["metrics"]["log_thinking"]        # thinking is the same everywhere: no difference at all
        self.assertAlmostEqual(t["d"], 0.0, places=10)
        self.assertEqual(t["p"], 1.0)
        self.assertEqual(t["wording_name"], "otherwise")

    def test_no_hour_effect_at_all(self):
        units = fake_data.fake_units()
        rep = T.analyse(fake_data.make_exact_rows(units, d_count=0), V, shuffles=1000, draws=200)
        for m in ("accuracy", "accuracy_bad_as_wrong", "log_thinking"):
            r = rep["metrics"][m]
            self.assertAlmostEqual(r["d"], 0.0, places=10)
            self.assertEqual(r["p"], 1.0)
            self.assertEqual(r["wording_name"], "otherwise")
            self.assertAlmostEqual(r["not_larger_than"], 0.0, places=10)

    def test_no_hour_effect_is_seldom_called_a_difference(self):
        units = fake_data.fake_units()
        counts = {m: {1: 0, 2: 0, 3: 0} for m in ("accuracy", "log_thinking")}
        runs = 20
        for seed in range(100, 100 + runs):
            rep = T.analyse(fake_data.make_main_rows(units, seed=seed), V, shuffles=1000, draws=100)
            for m in counts:
                counts[m][rep["metrics"][m]["wording"]] += 1
        print(f"\n  no hour effect, {runs} made-up runs, wordings 1 clear / 2 points one way / 3 otherwise: {counts}")
        for m, c in counts.items():
            self.assertLessEqual(c[1], 1, m)
            self.assertLessEqual(c[1] + c[2], 4, m)

    def test_a_pass_that_stopped_early_is_left_out_of_the_sign_check(self):
        units = fake_data.fake_units()
        start3 = datetime(2026, 11, 12, 13, 0, tzinfo=UTC)          # pass 3 crosses 14:00 UTC
        rows = fake_data.make_main_rows(units, seed=5, start={3: start3}, blocks_of_pass={3: 6})
        rep = T.analyse(rows, V, shuffles=500, draws=100)
        self.assertEqual(rep["cells_that_count"]["3"], 18)
        a = rep["metrics"]["accuracy"]
        self.assertIn("3", a["parts"])                              # pass 3 has a d of its own here
        self.assertFalse(a["parts"]["3"]["counts_for_sign"])        # and it stays out of the sign check
        self.assertIn("why_not_in_the_sign_check", a["parts"]["3"])
        self.assertTrue(a["parts"]["1"]["counts_for_sign"] and a["parts"]["2"]["counts_for_sign"])
        self.assertEqual(a["parts_in_the_sign_check"], 2)
        # asks inside US working hours on Thursday 12 November: the two limit sentences no longer hold
        self.assertEqual(list(rep["us_days_of_inside_asks"]), ["2026-11-11", "2026-11-12"])
        self.assertIn("2026-11-12", rep["warning"])
        self.assertIn("WARNING", T.report_text(rep))
        # a whole pass 3 that crosses 14:00 UTC has a d of its own as well, reported beside the two parts
        rows = fake_data.make_main_rows(units, seed=5, start={3: start3})
        a = T.analyse(rows, V, shuffles=200, draws=50)["metrics"]["accuracy"]
        self.assertEqual(sorted(a["parts"]), ["1", "2", "3"])
        self.assertFalse(a["parts"]["3"]["counts_for_sign"])
        self.assertEqual(a["parts_in_the_sign_check"], 2)

    def test_a_resent_ask_counts_at_the_time_it_was_resent(self):
        units = fake_data.fake_units()
        rows = fake_data.make_exact_rows(units)
        first = next(r for r in rows if r["pass"] == 3 and r["version"] == "2.1.300")
        self.assertFalse(common.in_us_hours(first["started_at"]))
        first.update(outcome="error", reason="failed", score=None, thinking_tokens=None)
        rows.append({**first, "plan": "F3r", "ask_id": "r3o000001", "outcome": "scored", "reason": None, "score": 1.0,
                     "thinking_tokens": 100, "started_at": "2026-11-12T15:00:00.000+00:00",
                     "resend_of": {"plan": first["plan"], "ask_id": first["ask_id"]}})
        main, _ = common.main_group(rows, V)
        cell = next(c for c in T.cells(main, "accuracy") if c["unit"] == first["unit"] and c["pass"] == 3)
        self.assertAlmostEqual(cell["share_inside"], 1 / 39)

    def test_a_version_the_server_refused_is_out(self):
        units = fake_data.fake_units()
        rows = fake_data.make_main_rows(units, seed=6)
        for r in rows:
            if r["version"] == "2.1.281":
                r.update(outcome="error", reason="min_version", score=None, thinking_tokens=None)
        rep = T.analyse(rows, V, shuffles=200, draws=50)
        self.assertEqual(rep["versions_refused_by_the_server"], ["2.1.281"])
        self.assertEqual(len(rep["versions"]), 38)
        self.assertEqual(rep["cells_that_count"], {"1": 78, "2": 78, "3": 78})

    def test_rehearsal_rows_one_pass_all_outside(self):
        rows = analyze.load_rows([REHEARSAL])
        versions = common.load_versions(None, None)
        rep = T.analyse(rows, versions, shuffles=200, draws=50)
        self.assertEqual(rep["passes"], [1])
        self.assertEqual(rep["cells_that_count"], {"1": 3})
        for m in ("accuracy", "accuracy_bad_as_wrong", "log_thinking"):
            self.assertIsNone(rep["metrics"][m]["wording"])
            self.assertIn("do not vary", rep["metrics"][m]["why"])
        self.assertEqual(rep["accuracy_wording"]["wording_name"], "not computable")
        T.report_text(rep)

    def test_the_program_writes_its_files_and_waits_for_the_run(self):
        units = fake_data.fake_units()
        graded = self.tmp / "graded.jsonl"
        write_jsonl(graded, fake_data.make_main_rows(units, seed=8))
        vf = self.tmp / "versions.json"
        vf.write_text(json.dumps({"versions": V}))
        out = self.tmp / "out"
        self.assertEqual(T.main(["--graded", str(graded), "--versions-file", str(vf), "--out", str(out),
                                 "--shuffles", "200", "--draws", "50"]), 0)
        for name in ("report.json", "report.md", "cells.csv", "hours.csv"):
            self.assertTrue((out / "time_of_day" / name).is_file(), name)
        hours = json.loads((out / "time_of_day" / "report.json").read_text())["metrics"]["accuracy"]["hours"]
        self.assertEqual(len(hours), 24)
        # without --graded: the run's final step has not run (here: the file is not there), so nothing is read
        self.assertEqual(T.main(["--versions-file", str(vf), "--out", str(out)]), 2)


# ------------------------------------------------------------------------------------ Desktop

class DesktopTests(Guarded):
    @classmethod
    def setUpClass(cls):
        from ccversions import items, settings
        s = settings.load(str(common.SETTINGS_FILE))
        cls.inputs = items.load(s.item_file, s.item_file_sha256, s.probe_file)
        cls.u78 = cls.inputs.item_keys()
        cls.u77 = [u for u in cls.u78 if u not in D.NOT_DELIVERABLE]
        cls.score = {u: float(i % 3 != 0) for i, u in enumerate(cls.u78)}
        cls.think = {u: 2 * (50 + i) - 1 for i, u in enumerate(cls.u78)}    # thinking + 1 is even
        rows = fake_data.make_main_rows(cls.u78, seed=7)
        for r in rows:  # main on 2.1.321: the same answer and the same thinking on an item in every pass
            if r["version"] == D.VERSION:
                r.update(outcome="scored", reason=None, score=cls.score[r["unit"]], thinking_tokens=cls.think[r["unit"]])
        cls.main_rows = rows
        cls.shifted = [u for u in cls.u77 if cls.score[u] == 1.0][:10]
        cls.graded_cache = {}

    def records(self, rounds, *, shifted=False, half=False, extra=()):
        out, order = [], 0
        for rnd in rounds:
            t0 = (datetime(2026, 11, 12, 4, 24, tzinfo=UTC) + timedelta(minutes=37 * (rnd - 1)) if rnd < 3
                  else datetime(2026, 11, 12, 14, 5, tzinfo=UTC))
            for n, u in enumerate(self.u77, 1):
                order += 1
                right = 0.0 if (shifted and u in self.shifted) else self.score[u]
                think = (self.think[u] + 1) // 2 - 1 if half else self.think[u]
                out.append(fake_data.desktop_record(self.inputs, u, rnd, n, order, correct=right, thinking=think,
                                                    started=t0 + timedelta(seconds=28 * n), tool_round=(n == 5)))
        for kw in extra:
            order += 1
            out.append(fake_data.desktop_record(self.inputs, order=order, **kw))
        return out

    def graded(self, rounds, **kw):
        key = (tuple(rounds), tuple(sorted(kw.items())))
        if key not in self.graded_cache:
            kept, _ = D.pick(self.records(rounds, **kw))
            self.graded_cache[key] = D.grade_records(kept)
        return self.graded_cache[key]

    def test_desktop_the_same_as_the_command_line(self):
        for rounds in ((1, 2), (1, 2, 3)):
            rep = D.analyse(self.main_rows, self.graded(rounds), V, shuffles=2000, draws=1000)
            self.assertEqual(rep["desktop_rounds"], list(rounds))
            for m in ("accuracy", "accuracy_bad_as_wrong", "log_thinking"):
                r = rep["metrics"][m]
                self.assertEqual(r["items"], 77)
                self.assertAlmostEqual(r["diff"], 0.0, places=12)
                self.assertEqual(r["p"], 1.0)
                self.assertEqual(r["wording_name"], "otherwise", (rounds, m))
                self.assertAlmostEqual(r["not_larger_than"], 0.0, places=12)
            self.assertEqual(rep["accuracy_wording"]["wording_name"], "otherwise")

    def test_a_known_difference_is_found(self):
        for rounds in ((1, 2), (1, 2, 3)):
            rep = D.analyse(self.main_rows, self.graded(rounds, shifted=True, half=True), V)
            a, t = rep["metrics"]["accuracy"], rep["metrics"]["log_thinking"]
            self.assertAlmostEqual(a["diff"], -10 / 77, places=12)          # wrong on 10 items main always gets right
            self.assertAlmostEqual(t["diff"], -math.log(2), places=12)      # half the thinking (tokens + 1) everywhere
            self.assertAlmostEqual(t["diff_shown"], -0.5, places=12)
            self.assertTrue(a["range_95"][0] < -10 / 77 < a["range_95"][1])
            # p of the sign flips: only the flips that give all 10 the same sign reach 10/77, 2 in 1,024
            self.assertLess(a["p"], 0.01)
            self.assertGreater(a["p"], 0.0005)
            for rnd, x in a["rounds"].items():
                self.assertAlmostEqual(x["diff"], -10 / 77, places=12)
            self.assertEqual(a["wording_name"], "clear")
            self.assertEqual(t["wording_name"], "clear")
            self.assertEqual(rep["accuracy_wording"]["wording_name"], "clear")

    def test_the_same_numbers_as_analyze_paired(self):
        g = self.graded((1, 2, 3), shifted=True, half=True)
        main, _ = common.main_group(self.main_rows, V)
        cli = D.main_rows_of(main, D.VERSION)
        for m, effect, _ in common.METRICS:
            mine = D.compare(g, cli, m, effect, shuffles=100, draws=10_000)
            ref = analyze.paired(g, cli, m)
            self.assertAlmostEqual(mine["diff"], ref["diff"], places=12)
            self.assertAlmostEqual(mine["range_95"][0], ref["range_95"][0], places=12)
            self.assertAlmostEqual(mine["range_95"][1], ref["range_95"][1], places=12)

    def test_records_that_do_not_count_are_left_out(self):
        u, w = self.u77[3], self.u77[4]
        t = datetime(2026, 11, 12, 6, 0, tzinfo=UTC)
        extra = [
            dict(unit=u, rnd=1, n=99, correct=1 - self.score[u], thinking=1, started=t, status="text_mismatch", text_ok=False),
            dict(unit=D.NOT_DELIVERABLE[0], rnd=1, n=98, correct=0, thinking=1, started=t),
            dict(unit=w, rnd=3, n=97, correct=1 - self.score[w], thinking=1, started=t, version="2.1.322"),
            dict(unit=w, rnd=2, n=96, correct=1 - self.score[w], thinking=1, started=t),  # a second settled record
            dict(unit=u, rnd=2, n=95, correct=1 - self.score[u], thinking=1, started=t, effort_ok=False,
                 status="effort_mismatch"),
        ]
        recs = self.records((1, 2, 3), extra=extra)
        kept, left = D.pick(recs)
        self.assertEqual(len(kept), 3 * 77)
        whys = sorted(x["why"].split(" (")[0].split(":")[0] for x in left)
        self.assertEqual(len(left), 5)
        self.assertEqual(sum("not settled" in x for x in whys), 2)
        self.assertTrue(any("does not ask" in x for x in whys))
        self.assertTrue(any("2.1.322" in x for x in whys))
        self.assertTrue(any("second settled" in x for x in whys))
        rep = D.analyse(self.main_rows, D.grade_records(kept), V, shuffles=500, draws=200)
        for m in ("accuracy", "log_thinking"):
            self.assertAlmostEqual(rep["metrics"][m]["diff"], 0.0, places=12)

    def test_a_refused_tool_call_still_counts_and_a_timeout_does_not(self):
        g = [dict(r) for r in self.graded((1, 2, 3))]
        tried = [r for r in g if r["tool_rounds"] == 1]
        self.assertEqual(len(tried), 3)
        self.assertTrue(all(r["outcome"] == "scored" and r["num_turns"] == 2 for r in tried))
        # one ask of round 1 timed out, on an item main always gets right
        u = next(x for x in self.u77 if self.score[x] == 1.0)
        rec = self.records((1,))[self.u77.index(u)]
        rec["status"] = "timeout"
        timed = D.grade_records([rec])[0]
        self.assertEqual((timed["outcome"], timed["reason"]), ("error", "timeout"))
        g = [timed if (r["pass"] == 1 and r["unit"] == u) else r for r in g]
        rep = D.analyse(self.main_rows, g, V, shuffles=500, draws=200)
        self.assertAlmostEqual(rep["metrics"]["accuracy"]["diff"], 0.0, places=12)       # left out
        self.assertAlmostEqual(rep["metrics"]["accuracy_bad_as_wrong"]["diff"], -1 / (3 * 77), places=12)

    def test_the_item_desktop_does_not_ask_is_left_out_on_the_command_line_too(self):
        main, _ = common.main_group(self.main_rows, V)
        cli = D.main_rows_of(main, D.VERSION)
        self.assertEqual(len(cli), 3 * 77)
        self.assertNotIn(D.NOT_DELIVERABLE[0], {r["unit"] for r in cli})

    def test_round_three_part_way(self):
        recs = self.records((1, 2, 3))
        kept, _ = D.pick(recs)
        self.assertIsNone(D.rounds_problem(kept))
        self.assertIsNone(D.rounds_problem([r for r in kept if r["pass"] < 3]))
        part = [r for r in kept if r["pass"] < 3 or r["repeat"] == 3 and int(r["ask_id"][3:]) <= 10]
        self.assertIn("10 of 77", D.rounds_problem(part))
        asks = self.tmp / "asks"
        asks.mkdir()
        for r in part:
            (asks / f"{r['ask_id']}.json").write_text(json.dumps(r))
        graded = self.tmp / "graded.jsonl"
        write_jsonl(graded, self.main_rows)
        vf = self.tmp / "versions.json"
        vf.write_text(json.dumps({"versions": V}))
        args = ["--graded", str(graded), "--desktop-asks", str(asks), "--versions-file", str(vf),
                "--out", str(self.tmp / "out"), "--shuffles", "300", "--draws", "100"]
        self.assertEqual(D.main(args), 2)
        self.assertEqual(D.main(args + ["--allow-partial-round3"]), 0)
        for name in ("report.json", "report.md", "per_item.csv", "graded/graded.jsonl", "graded/public_table.csv"):
            self.assertTrue((self.tmp / "out" / "desktop" / name).is_file(), name)
        rep = json.loads((self.tmp / "out" / "desktop" / "report.json").read_text())
        self.assertEqual(rep["desktop_asks_by_round"], {"1": 77, "2": 77, "3": 10})
        # without --graded: the run's final step has not run (here: the file is not there), so nothing is read
        self.assertEqual(D.main(["--desktop-asks", str(asks), "--versions-file", str(vf), "--out", str(self.tmp)]), 2)

    def test_rehearsal_rows_against_made_up_desktop_records(self):
        rows = analyze.load_rows([REHEARSAL])
        versions = common.load_versions(None, None)
        mine = {r["unit"]: r for r in rows if r["group"] == "main" and r["version"] == D.VERSION}
        self.assertEqual(len(mine), 3)
        recs, order = [], 0
        for rnd in (1, 2):
            for n, (u, r) in enumerate(sorted(mine.items()), 1):
                order += 1
                recs.append(fake_data.desktop_record(self.inputs, u, rnd, n, order, correct=r["score"],
                                                     thinking=r["thinking_tokens"],
                                                     started=datetime(2026, 11, 12, 4, 30 + order, tzinfo=UTC)))
        kept, left = D.pick(recs)
        self.assertEqual((len(kept), left), (6, []))
        rep = D.analyse(rows, D.grade_records(kept), versions, shuffles=500, draws=200)
        self.assertEqual(rep["cli_asks"], 3)
        for m in ("accuracy", "accuracy_bad_as_wrong", "log_thinking"):
            self.assertEqual(rep["metrics"][m]["items"], 3)
            self.assertAlmostEqual(rep["metrics"][m]["diff"], 0.0, places=12)
        D.report_text(rep)


if __name__ == "__main__":
    unittest.main()
