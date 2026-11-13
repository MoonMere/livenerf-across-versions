"""The rule that says whether stage 2 of group high_recheck is sent (PREREGISTRATION.md, change log,
entry "two groups sent after the reports were opened", "The rule for stage 2").

    python -B gate.py --settings <settings .toml> --config run_h.json --out <gate .json>

It grades the asks of passes 1 to 12 and of their resend plans with the LiveNerf author's graders
(ccversions.grade, unchanged), and computes one number from the ten versions of the comparison:

    for each version and each of the 24 questions: the share of its scored asks that are right
    for each version: the mean of those 24 shares
    D1 = (mean over 2.1.317, 318, 319, 321, 322) - (mean over 2.1.311, 312, 314, 315, 316), in points

Stage 2 is sent when D1 <= -1.0. 2.1.323 takes no part. The program prints D1, the ten version figures,
how many asks were scored, and the decision. It prints no thinking count and reads no answer text.

It refuses to decide (exit code 2) while a planned ask of passes 1 to 12 has no record, or when a
version has a question without any scored ask.

`decide()` is the rule itself, on plain rows; test_gate.py runs it on made-up rows.
Exit code: 0 stage 2 is sent, 1 stage 2 is not sent, 2 no decision.
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

EARLIER = ("2.1.311", "2.1.312", "2.1.314", "2.1.315", "2.1.316")
LATER = ("2.1.317", "2.1.318", "2.1.319", "2.1.321", "2.1.322")
GROUP = "high_recheck"
STAGE1_PASSES = tuple(range(1, 13))
THRESHOLD_POINTS = -1.0


def version_accuracy(rows: list[dict], versions=EARLIER + LATER, group: str = GROUP) -> tuple[dict, dict]:
    """For each version: the mean over questions of the share of scored asks that are right (0 to 1).
    Also the number of scored asks behind it. Raises ValueError when a version has a question with no
    scored ask while another version has one (the ten must cover the same questions)."""
    cells: dict = {}
    for r in rows:
        if r.get("group") != group or r.get("outcome") != "scored" or r.get("version") not in versions:
            continue
        cells.setdefault(r["version"], {}).setdefault(r["unit"], []).append(float(r["score"]))
    units = sorted({u for v in cells.values() for u in v})
    acc, n = {}, {}
    for v in versions:
        mine = cells.get(v, {})
        missing = [u for u in units if u not in mine]
        if missing or not units:
            raise ValueError(f"version {v} has no scored ask for {len(missing)} of {len(units)} questions")
        acc[v] = sum(sum(x) / len(x) for x in mine.values()) / len(units)
        n[v] = sum(len(x) for x in mine.values())
    return acc, n


def decide(rows: list[dict], threshold_points: float = THRESHOLD_POINTS) -> dict:
    acc, n = version_accuracy(rows)
    earlier = sum(acc[v] for v in EARLIER) / len(EARLIER)
    later = sum(acc[v] for v in LATER) / len(LATER)
    d1 = (later - earlier) * 100
    # the comparison is made on the value rounded to 6 decimals, so a float that prints as -1.000000 counts
    send = round(d1, 6) <= threshold_points
    return {"rule": f"stage 2 is sent when D1 <= {threshold_points} points",
            "version_accuracy_per_cent": {v: round(acc[v] * 100, 3) for v in EARLIER + LATER},
            "scored_asks": n,
            "earlier_five_per_cent": round(earlier * 100, 3), "later_five_per_cent": round(later * 100, 3),
            "D1_points": round(d1, 3), "send_stage_2": bool(send)}


def main(argv=None) -> int:
    from ccversions import formal, plan as plan_mod, settings as settings_mod

    ap = argparse.ArgumentParser()
    ap.add_argument("--settings", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    d = formal.Driver(settings_mod.load(a.settings), Path(a.config))
    missing = []
    for p in STAGE1_PASSES:
        name = f"{d.prefix}{p}"
        if not d.plan_path(name).exists():
            missing.append(f"{name}: no plan")
            continue
        plan = plan_mod.load(d.plan_path(name))
        folder = d.run_dir(name) / "asks"
        done = {x.stem for x in folder.glob("*.json")} if folder.is_dir() else set()
        lacking = [x["ask_id"] for x in plan["asks"] if x["ask_id"] not in done]
        if lacking:
            missing.append(f"{name}: {len(lacking)} of {len(plan['asks'])} asks have no record")
        resend = d.plan_path(f"{name}r")
        if resend.exists():
            rplan = plan_mod.load(resend)
            rfolder = d.run_dir(f"{name}r") / "asks"
            rdone = {x.stem for x in rfolder.glob("*.json")} if rfolder.is_dir() else set()
            rlack = [x["ask_id"] for x in rplan["asks"] if x["ask_id"] not in rdone]
            if rlack:
                missing.append(f"{name}r: {len(rlack)} of {len(rplan['asks'])} asks have no record")
    out = {"what": "the decision about stage 2 of high_recheck", "passes": list(STAGE1_PASSES)}
    if missing:
        out.update(decided=False, why=missing)
        Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
        print(json.dumps(out, indent=1), flush=True)
        return 2
    names = [f"{d.prefix}{p}{suffix}" for p in STAGE1_PASSES for suffix in ("", "r")]
    rows = []
    for f in d.graded(names):
        rows += [json.loads(line) for line in f.read_text().splitlines() if line.strip()]
    try:
        out.update(decided=True, **decide(rows))
    except ValueError as e:
        out.update(decided=False, why=[str(e)])
        Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
        print(json.dumps(out, indent=1), flush=True)
        return 2
    outcomes: dict = {}
    for r in rows:
        if r.get("group") == GROUP:
            outcomes.setdefault(r["version"], {}).setdefault(r.get("outcome"), 0)
            outcomes[r["version"]][r.get("outcome")] += 1
    out["asks_by_version_and_outcome"] = outcomes
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1), flush=True)
    return 0 if out["send_stage_2"] else 1


if __name__ == "__main__":
    sys.exit(main())
