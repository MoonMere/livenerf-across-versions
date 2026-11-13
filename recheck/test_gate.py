"""Tests of gate.decide() on made-up rows. No data of the run is read.

    python -B -m unittest test_gate
"""

import random
import unittest

import gate


def rows_for(acc_by_version: dict, asks: int = 12, units: int = 24, group: str = gate.GROUP) -> list[dict]:
    """Every version gets `asks` asks on each question, the first round(acc * asks) of them right."""
    out = []
    for v, acc in acc_by_version.items():
        for u in range(units):
            right = round(acc * asks)
            for k in range(asks):
                out.append({"group": group, "version": v, "unit": f"item:q{u}", "outcome": "scored",
                            "score": 1.0 if k < right else 0.0})
    return out


class GateTest(unittest.TestCase):
    def test_lower_by_more_than_one_point_sends(self):
        acc = {v: 0.5 for v in gate.EARLIER} | {v: 0.25 for v in gate.LATER}
        r = gate.decide(rows_for(acc))
        self.assertTrue(r["send_stage_2"])
        self.assertAlmostEqual(r["D1_points"], -25.0)

    def test_equal_does_not_send(self):
        acc = {v: 0.5 for v in gate.EARLIER + gate.LATER}
        r = gate.decide(rows_for(acc))
        self.assertFalse(r["send_stage_2"])
        self.assertAlmostEqual(r["D1_points"], 0.0)

    def test_higher_does_not_send(self):
        acc = {v: 0.25 for v in gate.EARLIER} | {v: 0.5 for v in gate.LATER}
        self.assertFalse(gate.decide(rows_for(acc))["send_stage_2"])

    def test_exactly_one_point_sends(self):
        # 100 asks a question: 50% against 49% is exactly one point lower
        acc = {v: 0.50 for v in gate.EARLIER} | {v: 0.49 for v in gate.LATER}
        r = gate.decide(rows_for(acc, asks=100))
        self.assertAlmostEqual(r["D1_points"], -1.0)
        self.assertTrue(r["send_stage_2"])

    def test_just_under_one_point_does_not_send(self):
        # one of the five later versions is two points lower, the others equal: 0.4 points lower in all
        acc = {v: 0.50 for v in gate.EARLIER + gate.LATER}
        acc["2.1.322"] = 0.48
        r = gate.decide(rows_for(acc, asks=100))
        self.assertAlmostEqual(r["D1_points"], -0.4)
        self.assertFalse(r["send_stage_2"])

    def test_the_eleventh_version_and_other_groups_take_no_part(self):
        acc = {v: 0.5 for v in gate.EARLIER + gate.LATER}
        rows = rows_for(acc) + rows_for({"2.1.323": 0.0}) + rows_for({v: 0.0 for v in gate.LATER}, group="other")
        self.assertAlmostEqual(gate.decide(rows)["D1_points"], 0.0)

    def test_unscored_asks_are_left_out(self):
        acc = {v: 0.5 for v in gate.EARLIER + gate.LATER}
        rows = rows_for(acc)
        rows += [{"group": gate.GROUP, "version": v, "unit": "item:q0", "outcome": "void", "score": None}
                 for v in gate.LATER]
        self.assertAlmostEqual(gate.decide(rows)["D1_points"], 0.0)

    def test_questions_weigh_the_same_when_asks_differ(self):
        # a version that lost asks on one question keeps that question's weight
        acc = {v: 0.5 for v in gate.EARLIER + gate.LATER}
        rows = [r for r in rows_for(acc) if not (r["version"] == "2.1.317" and r["unit"] == "item:q0" and r["score"] == 0.0)]
        a, _ = gate.version_accuracy(rows)
        self.assertAlmostEqual(a["2.1.317"], (23 * 0.5 + 1.0) / 24)

    def test_a_question_without_a_scored_ask_stops_the_decision(self):
        acc = {v: 0.5 for v in gate.EARLIER + gate.LATER}
        rows = [r for r in rows_for(acc) if not (r["version"] == "2.1.317" and r["unit"] == "item:q0")]
        with self.assertRaises(ValueError):
            gate.decide(rows)

    def test_random_rows_match_a_direct_count(self):
        rng = random.Random(1)
        rows = []
        for v in gate.EARLIER + gate.LATER:
            for u in range(24):
                for _ in range(12):
                    rows.append({"group": gate.GROUP, "version": v, "unit": f"item:q{u}", "outcome": "scored",
                                 "score": float(rng.random() < 0.4)})
        r = gate.decide(rows)
        share = lambda vs: sum(x["score"] for x in rows if x["version"] in vs) / sum(1 for x in rows if x["version"] in vs)
        self.assertAlmostEqual(r["D1_points"], round((share(gate.LATER) - share(gate.EARLIER)) * 100, 3), places=3)


if __name__ == "__main__":
    unittest.main()
