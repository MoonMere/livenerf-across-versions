"""Sends passes of one of the two groups added on 13 November 2026 (PREREGISTRATION.md, change log:
"two groups sent after the reports were opened").

    python -B driver.py --settings <settings .toml> --config run_x.json --first 1 --last 5
    python -B driver.py --settings <settings .toml> --config run_h.json --first 1 --last 12

It adds no way of asking. Each pass is made and sent by the registered sender (ccversions), through the
same steps as the registered run's driver (ccversions/formal.py, class Driver): plan-arms for the pass,
send, then one plan that asks once more the asks that never reached the model, send. An outage is waited
out the same way (a streak of failed asks, then a cheap probe after 5, 10, 20, 40, 60 ... minutes).
Nothing is graded and nothing is analysed here.

Two things differ from the registered run and are written in the change log entry:

  asks_at_once   The registered sender makes plans for at most two asks at a time (modes.MAX_PARALLEL,
                 a module under the fingerprint, not edited). Here the plan is made with two and its
                 "parallel" is then set to the config's asks_at_once before it is sent, as the
                 desktop-prompt group did. The sender still never runs two asks of one version at once,
                 so a config folder never has two asks at a time.
  passes         The config names no third pass and no rule for one: --first and --last say which passes
                 this call sends. Every pass is round "first" of the arms file.

Exit code: 0 all passes of this call complete; 3 stopped on the weekly line or a usage limit (the asks sent
so far count); 2 stopped for something a person has to look at.
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from ccversions import formal, plan as plan_mod, run, settings as settings_mod  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--settings", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--first", type=int, required=True)
    ap.add_argument("--last", type=int, required=True)
    ap.add_argument("--plan-only", action="store_true", help="write the pass plans of this call and send nothing")
    a = ap.parse_args(argv)
    if not 1 <= a.first <= a.last:
        raise SystemExit("--first and --last: 1 <= first <= last")
    s = settings_mod.load(a.settings)
    d = formal.Driver(s, Path(a.config))
    line = d.cfg["first_line"]
    at_once = int(d.cfg["asks_at_once"])
    if d.cfg.get("passes_first", 2) < a.last:
        raise SystemExit("passes_first in the config must cover --last (every pass is round 'first')")

    def with_asks_at_once(p: dict) -> dict:
        if p["spec"].get("parallel") != at_once:
            p["spec"]["parallel"] = at_once
            plan_mod.save(p, d.plan_path(p["name"]))
            d.log("asks_at_once_set", plan=p["name"], asks_at_once=at_once)
        return p

    d.log("call_start", config=str(d.config_path), first=a.first, last=a.last, plan_only=a.plan_only,
          asks_at_once=at_once, line=line)
    try:
        for n in range(a.first, a.last + 1):
            p = with_asks_at_once(d.pass_plan(n, line))
            if a.plan_only:
                continue
            for step, plan in ((f"pass{n}", p), (f"resend{n}", None)):
                if plan is None:
                    plan = d.resend_plan(n, line)
                    if plan is None:
                        continue
                    plan = with_asks_at_once(plan)
                how = d.send(plan)
                if how != "complete":
                    d.log("stopped", step=step, how=how)
                    d.log("call_end", how=how)
                    return 3
    except (formal.FormalError, run.RunError) as e:
        d.log("call_end", how="error", error=str(e)[:1000])
        print(f"stopped: {e}", flush=True)
        return 2
    d.log("call_end", how="planned" if a.plan_only else "done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
