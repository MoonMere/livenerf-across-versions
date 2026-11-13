"""Tests of rescore.py on made-up rows. No data of any run is read.

    python -B -m unittest test_rescore
"""

import unittest

import analysis as A
import rescore

KEYS = {"sound": ["s1", "s2"], "also_accepted": {"both": "B"}, "replaced": {"num": "932"}, "left_out": ["gone"]}


def row(version, unit, answer, score, pass_=1, group="g"):
    return {"group": group, "version": version, "unit": "item:" + unit, "pass": pass_, "outcome": "scored",
            "answer": answer, "score": score, "thinking_tokens": 10}


def rows_for(answers: dict, passes=(1, 2)) -> list[dict]:
    """answers: {unit: (key, earlier five's answer, later five's answer)}. The score is 1 when the answer is the key."""
    out = []
    for unit, (key, early, late) in answers.items():
        for p in passes:
            for v in A.EARLIER:
                out.append(row(v, unit, early, float(early == key), p))
            for v in A.LATER:
                out.append(row(v, unit, late, float(late == key), p))
    return out


class CorrectedTest(unittest.TestCase):
    def test_the_listed_option_is_right_as_well(self):
        self.assertEqual(rescore.corrected(row("v", "both", "B", 0.0), KEYS), 1.0)

    def test_the_keyed_option_stays_right(self):
        self.assertEqual(rescore.corrected(row("v", "both", "G", 1.0), KEYS), 1.0)

    def test_another_option_stays_wrong(self):
        self.assertEqual(rescore.corrected(row("v", "both", "C", 0.0), KEYS), 0.0)

    def test_no_answer_keeps_its_score(self):
        self.assertEqual(rescore.corrected(row("v", "both", None, 0.0), KEYS), 0.0)

    def test_the_replaced_value_is_right_and_the_old_key_wrong(self):
        self.assertEqual(rescore.corrected(row("v", "num", "932", 0.0), KEYS), 1.0)
        self.assertEqual(rescore.corrected(row("v", "num", " 932 ", 0.0), KEYS), 1.0)
        self.assertEqual(rescore.corrected(row("v", "num", "930", 1.0), KEYS), 0.0)
        self.assertEqual(rescore.corrected(row("v", "num", None, 0.0), KEYS), 0.0)

    def test_other_questions_keep_their_score(self):
        self.assertEqual(rescore.corrected(row("v", "s1", "B", 0.0), KEYS), 0.0)
        self.assertEqual(rescore.corrected(row("v", "s1", "A", 1.0), KEYS), 1.0)
        self.assertEqual(rescore.corrected(row("v", "s2", "932", 0.0), KEYS), 0.0)


class WaysTest(unittest.TestCase):
    def setUp(self):
        # both: the earlier five give the keyed G, the later five the same answer under its other letter B
        # num:  the earlier five give the old key 930, the later five the right 932
        # gone: the earlier five right by the key, the later five wrong, and no right option exists
        # s1:   everybody right. s2: the earlier five right, the later five wrong
        self.asks = rows_for({"both": ("G", "G", "B"), "num": ("930", "930", "932"), "gone": ("A", "A", "C"),
                              "s1": ("A", "A", "A"), "s2": ("A", "A", "D")})
        self.w = rescore.ways(self.asks, KEYS)

    def test_original_is_the_score_on_every_question(self):
        c = self.w["original"]
        self.assertEqual(c["questions"], 5)
        self.assertAlmostEqual(c["difference_points"], (0 + 0 + 0 + 1 + 0 - (1 + 1 + 1 + 1 + 1)) / 5 * 100)

    def test_sound_takes_the_sound_questions_only(self):
        c = self.w["sound"]
        self.assertEqual(c["questions"], 2)
        self.assertAlmostEqual(c["difference_points"], -50.0)

    def test_corrected_leaves_out_and_rescores(self):
        c = self.w["corrected"]
        self.assertEqual(c["questions"], 4)
        # both: 1 against 1. num: later 1 against earlier 0. s1: 1 against 1. s2: 0 against 1
        self.assertAlmostEqual(c["difference_points"], (1 + 1 + 1 + 0 - (1 + 0 + 1 + 1)) / 4 * 100)

    def test_nothing_is_declared(self):
        for c in self.w.values():
            self.assertIsNone(c["declared"])

    def test_original_is_what_analysis_gives(self):
        a = A.one_comparison(self.asks, A.correct, "accuracy")
        for k in ("T", "p", "questions", "difference_points", "range_points"):
            self.assertEqual(self.w["original"][k], a[k])

    def test_the_eleventh_version_has_its_own_figure_and_takes_no_part(self):
        extra = [row(A.ELEVENTH, "s1", "A", 1.0, p) for p in (1, 2)] + [row(A.ELEVENTH, "both", "B", 0.0, p) for p in (1, 2)]
        w = rescore.ways(self.asks + extra, KEYS)
        self.assertAlmostEqual(w["corrected"]["difference_points"], self.w["corrected"]["difference_points"])
        self.assertAlmostEqual(w["corrected"]["version_2_1_323"]["accuracy_per_cent"], 100.0)
        self.assertEqual(w["corrected"]["version_2_1_323"]["questions"], 2)
        self.assertAlmostEqual(w["original"]["version_2_1_323"]["accuracy_per_cent"], 50.0)

    def test_which_ways(self):
        self.assertEqual(list(rescore.ways(self.asks, KEYS, which=("original",))), ["original"])


class ReportTest(unittest.TestCase):
    def test_groups_and_stages(self):
        answers = {"s1": ("A", "A", "A"), "both": ("G", "G", "B")}
        x = [dict(r, group="xhigh_recheck") for r in rows_for(answers, passes=(1, 2, 3, 4, 5))]
        h1 = [dict(r, group="high_recheck") for r in rows_for(answers, passes=range(1, 13))]
        h2 = [dict(r, group="high_recheck") for r in rows_for(answers, passes=range(13, 25))]
        m = [dict(r, group="main") for r in rows_for(answers, passes=(1, 2, 3))]
        rep = rescore.report(x, h1, m, KEYS, ["both"])
        self.assertIn("high_recheck_stage_1", rep)
        self.assertNotIn("high_recheck_both_stages", rep)
        self.assertAlmostEqual(rep["xhigh_recheck"]["original"]["difference_points"], -50.0)
        self.assertAlmostEqual(rep["xhigh_recheck"]["corrected"]["difference_points"], 0.0)
        self.assertEqual(rep["main_on_the_24_seen_before_this_was_written"]["original"]["questions"], 1)
        rep = rescore.report(x, h1 + h2, [], KEYS, ["both"])
        self.assertEqual(rep["high_recheck_both_stages"]["scored_asks_that_count"], 2 * 24 * 10)
        self.assertIn("no declaration", rescore.text_report(rep))


class KeysFileTest(unittest.TestCase):
    def test_the_lists_do_not_overlap(self):
        k = rescore.load_keys()
        groups = [set(k["sound"]), set(k["also_accepted"]), set(k["replaced"]), set(k["left_out"])]
        self.assertEqual([len(g) for g in groups], [40, 7, 1, 4])
        self.assertEqual(len(set().union(*groups)), 52)
        self.assertEqual(set(k["why"]), groups[1] | groups[2] | groups[3])


if __name__ == "__main__":
    unittest.main()
