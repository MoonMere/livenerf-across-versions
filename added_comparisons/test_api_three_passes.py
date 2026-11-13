"""Self-tests of api_three_passes.py on made-up rows. Nothing here reads the registered run or the records
of the added pass, and no model is asked.

    python -B test_api_three_passes.py
"""

import math
import random
import sys
import unittest

import api_three_passes as m
from common import analyze

UNITS = [f"item:fake-{i:02d}" for i in range(78)]


def row(group, version, p, unit, *, score, thinking=100, output=300, outcome="scored", plan=None, ask=None):
    return {"group": group, "version": version, "pass": p, "unit": unit, "outcome": outcome,
            "score": score if outcome == "scored" else None, "thinking_tokens": thinking, "output_tokens": output,
            "plan": plan or f"F{p}", "ask_id": ask or f"{group}-{version}-{p}-{unit}", "resend_of": None,
            "tool_calls": 0, "elapsed_seconds": 5.0}


def make(seed=1, *, api_rate=0.7, author_rate=0.6, passes=(1, 2, 3)):
    """Rows of api and author (2.1.280 and 2.1.322) and a few of group main, right or wrong by a fixed draw."""
    rng = random.Random(seed)
    rows = []
    for p in passes:
        for u in UNITS:
            rows.append(row("api", "2.1.322", p, u, score=float(rng.random() < api_rate), thinking=rng.randint(50, 500)))
            rows.append(row("author", "2.1.322", p, u, score=float(rng.random() < author_rate), thinking=rng.randint(50, 500)))
            if p < 3:
                rows.append(row("author", "2.1.280", p, u, score=float(rng.random() < 0.5)))
                rows.append(row("main", "2.1.322", p, u, score=float(rng.random() < 0.5)))
    return rows


class Tests(unittest.TestCase):
    def setUp(self):
        rows = make()
        self.formal = [r for r in rows if r["pass"] < 3]
        self.third = [dict(r, plan="A3") for r in rows if r["pass"] == 3]

    def test_two_passes_is_the_registered_figure(self):
        rep = m.analyse(self.formal, self.third, draws=2000)
        want = analyze.small_groups(analyze.apply_resends(self.formal))["api"]["against_author_same_version"]
        for name in ("accuracy", "accuracy_bad_as_wrong", "thinking", "output"):
            self.assertAlmostEqual(rep["two_passes"][name]["diff"], want[name]["diff"], places=12)
            self.assertEqual(rep["two_passes"][name]["asks_a"], 156)
            self.assertEqual(rep["two_passes"][name]["asks_b"], 156)

    def test_three_passes_by_hand(self):
        rep = m.analyse(self.formal, self.third, draws=2000)
        allrows = self.formal + self.third
        d = []
        for u in UNITS:
            a = [r["score"] for r in allrows if r["group"] == "api" and r["unit"] == u]
            b = [r["score"] for r in allrows if r["group"] == "author" and r["version"] == "2.1.322" and r["unit"] == u]
            self.assertEqual((len(a), len(b)), (3, 3))
            d.append(sum(a) / 3 - sum(b) / 3)
        r = rep["three_passes"]["accuracy"]
        self.assertAlmostEqual(r["diff"], sum(d) / len(d), places=12)
        self.assertEqual((r["items"], r["asks_a"], r["asks_b"]), (78, 234, 234))
        self.assertLessEqual(r["range_95"][0], r["diff"])
        self.assertGreaterEqual(r["range_95"][1], r["diff"])
        self.assertEqual(rep["added_pass_alone"]["accuracy"]["asks_a"], 78)

    def test_author_on_the_other_version_and_other_groups_stay_out(self):
        rep = m.analyse(self.formal, self.third, draws=500)
        self.assertEqual(rep["asks"]["author"]["passes_1_2"], {"pass 1: scored": 78, "pass 2: scored": 78})
        self.assertEqual(rep["groups_in_the_added_pass_not_used"], [])
        third = self.third + [row("fable", "2.1.322", 3, UNITS[0], score=1.0, plan="A3")]
        self.assertEqual(m.analyse(self.formal, third, draws=500)["groups_in_the_added_pass_not_used"], ["fable 2.1.322"])

    def test_thinking_ratio(self):
        formal = [dict(r, thinking_tokens=199 if r["group"] == "api" else 99) for r in self.formal]
        third = [dict(r, thinking_tokens=199 if r["group"] == "api" else 99) for r in self.third]
        r = m.analyse(formal, third, draws=500)["three_passes"]["thinking"]
        self.assertAlmostEqual(r["ratio"], 2.0, places=9)   # log(200) - log(100)

    def test_error_left_out_or_counted_wrong(self):
        third = [dict(r) for r in self.third]
        for r in third:
            if r["group"] == "api" and r["unit"] == UNITS[0]:
                r.update(outcome="error", score=None)
        rep = m.analyse(self.formal, third, draws=500)
        row0 = next(x for x in rep["per_item"] if x["unit"] == UNITS[0])
        a12 = [r["score"] for r in self.formal if r["group"] == "api" and r["unit"] == UNITS[0]]
        self.assertAlmostEqual(row0["accuracy_api"], sum(a12) / 2, places=12)
        self.assertAlmostEqual(row0["accuracy_bad_as_wrong_api"], sum(a12) / 3, places=12)
        self.assertEqual(rep["asks"]["api"]["added_pass"], {"pass 3: error": 1, "pass 3: scored": 77})

    def test_resend_takes_the_place(self):
        third = [dict(r) for r in self.third]
        first = next(r for r in third if r["group"] == "api" and r["unit"] == UNITS[3])
        first.update(outcome="error", score=None)
        third.append(dict(row("api", "2.1.322", 3, UNITS[3], score=1.0, plan="A3r", ask="resent"),
                          resend_of={"plan": "A3", "ask_id": first["ask_id"]}))
        rep = m.analyse(self.formal, third, draws=500)
        self.assertEqual(rep["asks"]["api"]["added_pass"], {"pass 3: scored": 78})

    def test_partial_third_pass_is_refused(self):
        self.assertIsNone(m.third_pass_problem(self.third))
        self.assertIn("77 item asks", m.third_pass_problem(self.third[2:]))
        wrong_pass = [dict(r, **{"pass": 2}) if i == 0 else r for i, r in enumerate(self.third)]
        self.assertIn("not pass 3", m.third_pass_problem(wrong_pass))

    def test_report_text(self):
        rep = m.analyse(self.formal, self.third, draws=500)
        rep.pop("per_item")
        text = m.report_text(rep)
        self.assertIn("Passes 1, 2 and 3 together (added)", text)
        self.assertIn("points (", text)
        self.assertFalse(math.isnan(rep["three_passes"]["output"]["ratio"]))


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    unittest.main(verbosity=1)
