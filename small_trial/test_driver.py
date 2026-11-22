"""Tests of driver.py against the stand-in program of ../tests/test_send_fake.py. No Claude Code is started,
nothing goes over the network, the real settings and config folders are not used.

    python -B -m unittest test_driver        (from this folder)
"""

import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "tests"))

import driver  # noqa: E402
import test_send_fake as base  # noqa: E402
from ccversions import checks, configdirs, grade, items  # noqa: E402


class DriverTests(unittest.TestCase):
    setUp = base.FakeSendTests.setUp
    tearDown = base.FakeSendTests.tearDown

    def segment(self, item_rows, cap, passes=2, fail_streak_stop=8):
        s = self.settings
        doc = {"format": items.ITEM_FORMAT, "system_prompt": base.SYSTEM, "items": [
            {"id": i, "input": text, "input_sha256": hashlib.sha256(text.encode()).hexdigest(),
             "scorer": "choice", "target": "A", "family": i.split("-")[0]} for i, text in item_rows]}
        s.item_file.write_text(json.dumps(doc))
        object.__setattr__(s, "item_file_sha256", checks.file_sha256(s.item_file))
        configdirs.add_set(s.config_dirs_file, "soff", base.VERSIONS, base.VERSIONS, remote_flags="off")
        (self.tmp / "arms.json").write_text(json.dumps({"format": "ccversions-arms-spec-v1", "name": "t", "groups": [
            {"group": "small_trial_new", "versions": ["2.1.280"], "mode": "stock_blocked", "effort": "high",
             "remote_flags": "off", "repeats": {"first": 1}}]}))
        (self.tmp / "run.json").write_text(json.dumps({
            "name_prefix": "SN", "arms_spec": "arms.json", "seed": "s", "units": ["item:" + i for i, _ in item_rows],
            "block_units": 3, "parallel": 1, "passes_first": passes, "first_line": 0.9, "third_line": 0.9,
            "third_pass": "never", "fail_streak_stop": fail_streak_stop, "max_outage_hours": 6,
            "health_config_set": "soff", "health_probe": "probe:ok", "work_dir": "work", "max_asks_all_parts": cap}))
        self.naps = []
        return self.tmp / "run.json"

    def go(self, config, last, **kw):
        return driver.run_passes(self.settings, config, 1, last, sleep=self.naps.append, **kw)

    def recorded(self):
        return driver.asks_recorded(self.settings.raw_dir)

    def test_two_passes_within_the_cap_one_ask_at_a_time(self):
        cfg = self.segment([(f"mmlupro-{i}", f"Pick {i}. ANSWER=A") for i in range(4)], cap=8)
        self.assertEqual(self.go(cfg, 2), 0)
        self.assertEqual(self.recorded(), 8)
        for name in ("SN1", "SN2"):
            p = json.loads((self.tmp / "work" / "plans" / f"{name}.json").read_text())
            self.assertEqual(p["spec"]["parallel"], 1)
            self.assertEqual(p["spec"]["stop_at_weekly_utilization"], 0.9)
            self.assertEqual(len(grade.load_records(self.settings.raw_dir / name)), 4)
        self.assertEqual(self.go(cfg, 2), 0)  # again: nothing left, nothing sent
        self.assertEqual(self.recorded(), 8)

    def test_plan_only_sends_nothing(self):
        cfg = self.segment([(f"mmlupro-{i}", f"Pick {i}. ANSWER=A") for i in range(4)], cap=8)
        self.assertEqual(self.go(cfg, 2, plan_only=True), 0)
        self.assertEqual(self.recorded(), 0)
        self.assertTrue((self.tmp / "work" / "plans" / "SN2.json").is_file())

    def test_a_pass_that_would_go_over_the_cap_is_not_started(self):
        cfg = self.segment([(f"mmlupro-{i}", f"Pick {i}. ANSWER=A") for i in range(4)], cap=7)
        self.assertEqual(self.go(cfg, 2), 2)
        self.assertEqual(self.recorded(), 4)  # pass 1 went out, pass 2 did not start
        log = json.loads((self.tmp / "work" / "state.json").read_text())["log"]
        self.assertEqual([e for e in log if e["what"] == "cap_reached"][0]["still_to_send"], 4)

    def test_other_records_under_raw_dir_count_too(self):
        cfg = self.segment([(f"mmlupro-{i}", f"Pick {i}. ANSWER=A") for i in range(4)], cap=8)
        probes = self.settings.raw_dir / "SP1" / "asks"
        probes.mkdir(parents=True)
        (probes / "p1b000o00001.json").write_text("{}")  # a probe sent before the segment
        self.assertEqual(self.go(cfg, 2), 2)
        self.assertEqual(self.recorded(), 1 + 4)

    def test_a_resend_that_would_go_over_the_cap_is_not_sent(self):
        rows = [("mmlupro-0", "Pick 0. FAILNOW"), ("mmlupro-1", "Pick 1. FAILNOW")] + \
               [(f"mmlupro-{i}", f"Pick {i}. ANSWER=A") for i in range(2, 5)]
        cfg = self.segment(rows, cap=6, passes=1)
        self.assertEqual(self.go(cfg, 1), 2)
        self.assertEqual(self.recorded(), 5)
        self.assertTrue((self.tmp / "work" / "plans" / "SN1r.json").is_file())
        self.assertFalse((self.settings.raw_dir / "SN1r").exists())

    def test_a_resend_within_the_cap_is_sent(self):
        rows = [("mmlupro-0", "Pick 0. FAILNOW")] + [(f"mmlupro-{i}", f"Pick {i}. ANSWER=A") for i in range(1, 4)]
        cfg = self.segment(rows, cap=5, passes=1)
        self.assertEqual(self.go(cfg, 1), 0)
        self.assertEqual(self.recorded(), 5)  # 4 in the pass, 1 asked once more (it fails again: no outage cure)
        self.assertEqual(len(grade.load_records(self.settings.raw_dir / "SN1r")), 1)

    def test_an_outage_probe_that_would_go_over_the_cap_is_not_sent(self):
        rows = [(f"mmlupro-{i}", f"Pick {i}. FAILNOW") for i in range(6)]
        cfg = self.segment(rows, cap=6, passes=1, fail_streak_stop=2)
        self.assertEqual(self.go(cfg, 1), 2)
        # the streak stopped the pass after two failed asks; after the first wait, 2 recorded + 4 left + 1 probe > 6
        self.assertEqual(self.recorded(), 2)
        self.assertEqual(self.naps, [300])
        self.assertFalse(any(p.name.startswith("SN_health") for p in self.settings.raw_dir.iterdir()))

    def test_an_outage_probe_within_the_cap_is_sent(self):
        rows = [(f"mmlupro-{i}", f"Pick {i}. FAILNOW") for i in range(4)]
        cfg = self.segment(rows, cap=20, passes=1, fail_streak_stop=2)
        healed = self.settings.tmpdir.parent / "healed"
        result = driver.run_passes(self.settings, cfg, 1, 1,
                                   sleep=lambda sec: (self.naps.append(sec), healed.write_text("x")))
        self.assertEqual(result, 0)
        self.assertEqual(self.naps, [300])
        self.assertEqual(len(grade.load_records(self.settings.raw_dir / "SN_health_001")), 1)
        # 2 failed asks, 1 outage probe, the 2 asks of the pass not yet sent, the 2 failed ones asked once more
        self.assertEqual(self.recorded(), 7)


if __name__ == "__main__":
    unittest.main()
