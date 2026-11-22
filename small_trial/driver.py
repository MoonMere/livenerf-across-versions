"""Sends the passes of one segment of the small trial of 22 November 2026 (设计/小试_两百道新题_规矩_20261122.md).

    python -B driver.py --settings <settings .toml> --config run_old.json --first 1 --last 1
    python -B driver.py --settings <settings .toml> --config run_new.json --first 1 --last 5
    add --plan-only to write the pass plans and send nothing

It adds no way of asking. It is the recheck groups' driver (程序/再验少想/driver.py) with two changes. Each
pass is made and sent by the registered sender (ccversions), through the same steps as the registered run's
driver (ccversions/formal.py, class Driver): plan-arms for the pass, send, then one plan that asks once more
the asks that never reached the model, send. An outage is waited out the same way (a streak of failed asks,
then a cheap probe after 5, 10, 20, 40, 60 ... minutes). Nothing is graded and nothing is analysed here.

The two changes:

  one ask at a time  The config's "parallel" (1) goes into each plan as it is made. The recheck driver's
                     asks_at_once, which raised it after the plan was made, is left out.
  a cap on asks      The config's max_asks_all_parts (1,150 in section 2 of the rules) caps every ask of the
                     small trial: both segments, their resends, the probes before them and the outage
                     probes, i.e. every record under the settings' raw_dir. Before a plan is sent, the asks
                     already recorded plus the asks of that plan not yet recorded must stay within the cap;
                     before an outage probe, the same plus one. Otherwise nothing more is sent and the call
                     ends with exit code 2, for a person to decide. A plan is never cut short to fit.

Exit code: 0 all passes of this call complete; 3 stopped on the weekly line or a usage limit (the asks sent
so far count); 2 stopped for something a person has to look at, the cap included.
"""

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from ccversions import formal, run, settings as settings_mod  # noqa: E402


class CapReached(formal.FormalError):
    pass


def asks_recorded(raw_dir: Path) -> int:
    """Every ask that has a record under raw_dir, of any plan."""
    return sum(1 for _ in raw_dir.glob("*/asks/*.json")) if raw_dir.is_dir() else 0


class CappedDriver(formal.Driver):
    def __init__(self, settings, config_path: Path, **kw):
        super().__init__(settings, config_path, **kw)
        self.cap = int(self.cfg["max_asks_all_parts"])
        self.current: dict | None = None

    def not_recorded(self, p: dict | None) -> int:
        if p is None:
            return 0
        asks = self.run_dir(p["name"]) / "asks"
        done = {x.stem for x in asks.glob("*.json")} if asks.is_dir() else set()
        return sum(1 for a in p["asks"] if a["ask_id"] not in done)

    def check_cap(self, p: dict | None, extra: int = 0, what: str = "plan") -> None:
        have, left = asks_recorded(self.s.raw_dir), self.not_recorded(p)
        if have + left + extra > self.cap:
            name = p["name"] if p else None
            self.log("cap_reached", before=what, plan=name, recorded=have, still_to_send=left, extra=extra, cap=self.cap)
            raise CapReached(f"cap of {self.cap} asks: {have} recorded, {left} still to send in {name}"
                             + (f", plus {extra} {what}" if extra else "") + "; nothing more is sent")

    def send(self, p: dict) -> str:
        self.check_cap(p)
        self.current = p
        try:
            return super().send(p)
        finally:
            self.current = None

    def health_probe(self) -> bool:
        self.check_cap(self.current, extra=1, what="outage probe")
        return super().health_probe()


def run_passes(s, config: Path, first: int, last: int, plan_only: bool = False, **driver_kw) -> int:
    if not 1 <= first <= last:
        raise SystemExit("--first and --last: 1 <= first <= last")
    d = CappedDriver(s, config, **driver_kw)
    line = d.cfg["first_line"]
    if d.cfg.get("passes_first", 2) < last:
        raise SystemExit("passes_first in the config must cover --last (every pass is round 'first')")
    if int(d.cfg.get("parallel", 2)) != 1:
        raise SystemExit("the small trial sends one ask at a time: parallel must be 1")
    d.log("call_start", config=str(d.config_path), first=first, last=last, plan_only=plan_only, line=line,
          cap=d.cap, recorded=asks_recorded(s.raw_dir))
    try:
        for n in range(first, last + 1):
            p = d.pass_plan(n, line)
            if p["spec"].get("parallel") != 1:
                raise formal.FormalError(f"{p['name']}: the plan says parallel {p['spec'].get('parallel')}, not 1")
            if plan_only:
                continue
            for step, plan in ((f"pass{n}", p), (f"resend{n}", None)):
                if plan is None:
                    plan = d.resend_plan(n, line)
                    if plan is None:
                        continue
                how = d.send(plan)
                if how != "complete":
                    d.log("stopped", step=step, how=how)
                    d.log("call_end", how=how)
                    return 3
    except (formal.FormalError, run.RunError) as e:
        d.log("call_end", how="cap" if isinstance(e, CapReached) else "error", error=str(e)[:1000])
        print(f"stopped: {e}", flush=True)
        return 2
    d.log("call_end", how="planned" if plan_only else "done", recorded=asks_recorded(s.raw_dir))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--settings", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--first", type=int, required=True)
    ap.add_argument("--last", type=int, required=True)
    ap.add_argument("--plan-only", action="store_true", help="write the pass plans of this call and send nothing")
    a = ap.parse_args(argv)
    return run_passes(settings_mod.load(a.settings), Path(a.config), a.first, a.last, a.plan_only)


if __name__ == "__main__":
    sys.exit(main())
