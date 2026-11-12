"""The Desktop group against group main on the same version, 2.1.321 (design file 判断标准.md, sections 6, 14
and 15, and the public preregistration, change log, the three entries of 12 November 2026).

    python -B desktop_vs_cli.py [--graded FILE ...] [--desktop-asks FOLDER] [--out FOLDER]
                                [--allow-unfinished] [--allow-partial-round3]

Without --graded it reads every 本机数据/正式跑/graded/*/graded.jsonl, and only once the registered run has
graded all its passes (本机数据/正式跑/final/report.json exists, and that file is never opened here). Without
--desktop-asks it reads 本机数据/Desktop组/asks/*.json, the records dq.py wrote.

Steps:

  pick       a Desktop record counts when dq.py settled it (the question arrived byte for byte, the app sent
             effort high, and it ended in an answer or a timeout), its item is one of the 77, and the app ran
             2.1.321. An ask that was asked again for a wrong text or effort is left out. The ask that settled
             it takes its place. Rounds 1 and 2, and round 3 when it was sent.
  grade      the picked records go through grade.py unchanged (grade_records, the author's graders), so the
             rules of section 1 decide what counts, as for main.
  main side  the asks of main on 2.1.321 in the cells that count (section 1: every version has a record in
             that item and pass), over every pass, on the same 77 items.
  compare    for accuracy twice (errors and voids left out, and counted as wrong) and for thinking
             (log of thinking tokens + 1): for each item, the mean of the Desktop rounds minus the mean of the
             main passes. The difference is the mean over the items both sides have. Range: the items redrawn
             10,000 times (seed 20261111), as analyze.paired does. p: each item's difference given a random
             sign 10,000 times (seed 20261111), p = (1 + flips whose |mean| is at least the real one) /
             (1 + flips). Each Desktop round on its own against the mean of the main passes gives the parts.
  wording    1 clear: p < 0.01, at least 3 points (accuracy) or 10 per cent (thinking), every round with the
             sign of the whole. 2 points one way: p < 0.05 and the size, short of clear. 3 otherwise: "no
             difference larger than X was seen", X from the range.

Outputs in FOLDER/desktop/: report.json, report.md, per_item.csv, and graded/ (grade.py's own outputs for the
Desktop records: graded.jsonl, summary.json, public_table.csv).
"""

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

import common
from common import analyze

sys.path.insert(0, str(common.PROGRAM / "Desktop组"))
import dq  # noqa: E402  (only its constants. Importing it reads and writes nothing)

VERSION = dq.VERSION                     # 2.1.321
NOT_DELIVERABLE = tuple(dq.NOT_DELIVERABLE)
ITEMS_IN_GROUP = 78 - len(NOT_DELIVERABLE)
GROUP = "desktop"
SETTLED_STATUS = ("done", "timeout")     # dq.settled()
CAUSES = (
    "the app wraps the question in a first message of its own (a line naming where it comes from, the author's "
    "two sentences, the question, a line naming a notes folder), while in main the two sentences go into the system "
    "prompt and the question is the whole message",
    "the system prompt has a section saying the session was started from another session",
    "plugins, extensions and connectors installed in the app are visible to the model, with their skills",
    "whether the app's sessions fetch today's remote flags was not checked, and main does not fetch them",
    "the environment variables of the Desktop sessions were not recorded",
    "the Desktop asks were sent one after another over a few hours, on the same account, while the registered "
    "run was going",
    "the hours they were sent: rounds 1 and 2 outside US working hours, round 3 inside them",
)
RETEST = "the same item asked through Desktop and through the command line one right after the other, several times"


# ------------------------------------------------------------------------------------ the Desktop records

def load_records(folder: Path) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(Path(folder).glob("*.json"))]


def pick(records: list[dict], version: str = VERSION) -> tuple[list[dict], list[dict]]:
    """The records that count, and the others with the reason each is left out."""
    kept, left, seen = [], [], {}
    for r in sorted(records, key=lambda r: (r.get("order") or 0, r.get("ask_id") or "")):
        why = None
        if r.get("group") != GROUP:
            why = f"group {r.get('group')!r} (this program reads group {GROUP!r} only)"
        elif not (r.get("text_ok") and r.get("effort_ok") and r.get("status") in SETTLED_STATUS):
            why = (f"not settled (status {r.get('status')}, text_ok {r.get('text_ok')}, effort_ok "
                   f"{r.get('effort_ok')}): asked again")
        elif r.get("unit") in NOT_DELIVERABLE:
            why = "an item this group does not ask"
        elif r.get("version") != version:
            why = f"the app ran Claude Code {r.get('version')} (this comparison is on {version})"
        elif (r.get("pass"), r.get("unit")) in seen:
            why = f"a second settled record of the same ask (the first is {seen[(r.get('pass'), r.get('unit'))]})"
        if why:
            left.append({"ask_id": r.get("ask_id"), "round": r.get("pass"), "unit": r.get("unit"), "why": why})
            continue
        seen[(r.get("pass"), r.get("unit"))] = r.get("ask_id")
        kept.append(r)
    return kept, left


def rounds_problem(kept: list[dict]) -> str | None:
    """Section 15: round 3 is either sent in full or not at all. A round 3 with some asks but not all is most
    likely still being sent, and the final report stays unopened until it is in."""
    n3 = sum(1 for r in kept if r.get("pass") == 3)
    if 0 < n3 < ITEMS_IN_GROUP:
        return (f"round 3 has {n3} of {ITEMS_IN_GROUP} asks. If it is still being sent, wait until it is done. "
                "If it stopped for good, give --allow-partial-round3")
    return None


def grade_records(records: list[dict], settings_file: Path | None = None) -> list[dict]:
    """grade.py on the Desktop records, with the settings of the run (the author's code and the item file)."""
    from ccversions import grade, items as items_mod, settings as settings_mod

    s = settings_mod.load(str(settings_file or common.SETTINGS_FILE))
    author_checks, claudecode = grade.import_author_graders(s.author_repo)
    inputs = items_mod.load(s.item_file, s.item_file_sha256, s.probe_file)
    return grade.grade_records(records, inputs, author_checks, claudecode)


# ------------------------------------------------------------------------------------ the comparison

def main_rows_of(main: "analyze.Main", version: str) -> list[dict]:
    """main's asks on one version in the cells that count, on the items of this group."""
    vi = main.versions.index(version)
    return [main.cell[ui, pi, vi] for ui in range(len(main.units)) for pi in range(len(main.passes))
            if main.complete[ui, pi] and main.units[ui] not in NOT_DELIVERABLE]


def compare(desk: list[dict], cli: list[dict], metric: str, effect: str, *, shuffles: int, draws: int) -> dict:
    D, M = analyze._item_means(desk, metric), analyze._item_means(cli, metric)
    units = sorted(set(D) & set(M))
    out = {"metric": metric, "effect": effect, "items": len(units)}
    if not units:
        return {**out, "wording": None, "wording_name": "not computable", "why": "no item that both sides have"}
    d = np.array([D[u] - M[u] for u in units])
    diff = float(d.mean())
    rng = np.random.default_rng(common.SEED)  # the same draws as analyze.paired
    boot = d[rng.integers(0, len(d), size=(draws, len(d)))].mean(axis=1)
    lo, hi = float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))
    rng = np.random.default_rng(common.SEED)
    signs = rng.integers(0, 2, size=(shuffles, len(d))) * 2 - 1
    flipped = np.abs((signs * d).mean(axis=1))
    hits = int((flipped >= abs(diff) - 1e-12).sum())
    p = (1 + hits) / (1 + shuffles)
    out.update(desktop_mean=float(np.mean([D[u] for u in units])), cli_mean=float(np.mean([M[u] for u in units])),
               diff=diff, diff_shown=common.shown(diff, effect), range_95=[lo, hi],
               range_95_shown=[common.shown(lo, effect), common.shown(hi, effect)], p=p, sign_flips=shuffles,
               desktop_asks_with_a_value=sum(1 for r in desk if not math.isnan(analyze.METRICS[metric](r))),
               cli_asks_with_a_value=sum(1 for r in cli if not math.isnan(analyze.METRICS[metric](r))))
    parts, sign_ok, checked = {}, True, 0
    for rnd in sorted({r["pass"] for r in desk}):
        Dr = analyze._item_means([r for r in desk if r["pass"] == rnd], metric)
        ur = sorted(set(Dr) & set(M))
        if not ur:
            parts[str(rnd)] = {"items": 0, "counts_for_sign": False}
            continue
        dr = float(np.mean([Dr[u] - M[u] for u in ur]))
        # a round with fewer than half the items is left out of the sign check, as in section 3
        counted = len(ur) / len(units) >= common.MIN_SHARE_FOR_SIGN
        parts[str(rnd)] = {"items": len(ur), "diff": dr, "shown": common.shown(dr, effect), "counts_for_sign": counted}
        checked += counted
        if counted and np.sign(dr) != np.sign(diff):
            sign_ok = False
    out["rounds"] = parts
    out["rounds_in_the_sign_check"] = checked
    out["same_sign_every_round"] = bool(sign_ok and checked > 0)
    out["big_enough"] = common.big_enough(diff, effect)
    w = common.wording(p, out["big_enough"], out["same_sign_every_round"])
    out["wording"], out["wording_name"] = w, common.WORDING[w]
    out["not_larger_than"] = common.not_larger_than([lo, hi], effect)
    out["per_item"] = {u: {"desktop": D[u], "cli": M[u], "diff": float(D[u] - M[u])} for u in units}
    return out


def _share_inside(rows: list[dict]) -> dict:
    out = {}
    for r in rows:
        if r.get("started_at"):
            a = out.setdefault(str(r.get("pass")), [0, 0])
            a[0] += common.in_us_hours(r["started_at"])
            a[1] += 1
    return {k: {"asks": n, "inside": i, "share_inside": i / n} for k, (i, n) in sorted(out.items())}


def _outcomes(rows: list[dict]) -> dict:
    out = {}
    for r in rows:
        k = r["outcome"] if r["outcome"] == "scored" else f"{r['outcome']}:{r.get('reason')}"
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


def _zero_thinking(rows: list[dict]) -> dict:
    t = [r.get("thinking_tokens") for r in rows if r.get("outcome") == "scored"]
    known = [x for x in t if x is not None]
    return {"scored": len(t), "with_a_count": len(known), "zero": sum(1 for x in known if x == 0)}


def analyse(main_rows_all: list[dict], desktop_graded: list[dict], versions: list[str], *, version: str = VERSION,
            shuffles: int = common.SHUFFLES, draws: int = common.DRAWS) -> dict:
    main, refused = common.main_group(main_rows_all, versions)
    desk = [r for r in desktop_graded if (r.get("unit") or "").startswith("item:") and r.get("unit") not in NOT_DELIVERABLE]
    rep = {"format": "two-comparisons-desktop-v1", "version": version,
           "rule": {"seed": common.SEED, "shuffles": shuffles, "draws": draws, "clear_p": common.CLEAR_P,
                    "lean_p": common.LEAN_P, "min_diff_accuracy": common.MIN_DIFF_ACCURACY,
                    "min_ratio_thinking": common.MIN_RATIO_THINKING, "items_left_out": list(NOT_DELIVERABLE)},
           "versions_refused_by_the_server": refused, "main_passes": main.passes,
           "desktop_rounds": sorted({r["pass"] for r in desk}),
           "desktop_asks_by_round": {str(k): sum(1 for r in desk if r["pass"] == k) for k in sorted({r["pass"] for r in desk})},
           "desktop_outcomes": _outcomes(desk), "metrics": {}}
    if version not in main.versions:
        rep["why_not_computable"] = (f"{version} is not among main's versions"
                                     + (" (refused by the server)" if version in refused else ""))
        return rep
    cli = main_rows_of(main, version)
    rep["cli_asks"] = len(cli)
    rep["cli_asks_by_pass"] = {str(p): sum(1 for r in cli if r["pass"] == p) for p in main.passes}
    rep["cli_outcomes"] = _outcomes(cli)
    rep["share_inside_us_hours"] = {"desktop_by_round": _share_inside(desk), "cli_by_pass": _share_inside(cli)}
    rep["thinking_counts"] = {"desktop": _zero_thinking(desk), "cli": _zero_thinking(cli)}
    zd, zc = rep["thinking_counts"]["desktop"], rep["thinking_counts"]["cli"]
    if zd["with_a_count"] and zd["zero"] == zd["with_a_count"] and zc["zero"] < zc["with_a_count"]:
        rep["warning"] = ("every scored Desktop ask has 0 thinking tokens while main's do not: the thinking count "
                          "may be missing from the Desktop session files. Check that before reading the thinking "
                          "comparison")
    for metric, effect, name in common.METRICS:
        r = compare(desk, cli, metric, effect, shuffles=shuffles, draws=draws)
        r["name"] = name
        rep["metrics"][metric] = r
    rep["accuracy_wording"] = common.both_ways_of_counting(rep["metrics"]["accuracy"],
                                                           rep["metrics"]["accuracy_bad_as_wrong"])
    t = rep["metrics"]["log_thinking"]
    rep["thinking_wording"] = {"wording": t.get("wording"), "wording_name": t.get("wording_name")}
    rep["causes_to_list_if_clear"] = list(CAUSES)
    rep["test_that_would_tell_them_apart"] = RETEST
    return rep


# ------------------------------------------------------------------------------------ outputs

def report_text(rep: dict) -> str:
    L = [f"# Desktop against the command line on {rep['version']} (group main), {ITEMS_IN_GROUP} items", "",
         f"Desktop rounds {rep['desktop_rounds']} ({rep['desktop_asks_by_round']} asks), outcomes {rep['desktop_outcomes']}.",
         f"Command line: passes {rep['main_passes']}, {rep.get('cli_asks')} asks in the cells that count "
         f"({rep.get('cli_asks_by_pass')}), outcomes {rep.get('cli_outcomes')}.",
         "A small group: differences and ranges only.", ""]
    dr = rep.get("desktop_records")
    if dr:
        why = {}
        for x in dr["left_out"]:
            why[x["why"].split(" (")[0]] = why.get(x["why"].split(" (")[0], 0) + 1
        L += [f"Desktop records read {dr['read']}, kept {dr['kept']}, left out {len(dr['left_out'])}"
              + (f": {why}" if why else "") + ". Each left-out record and why is in report.json.", ""]
    if rep.get("why_not_computable"):
        return "\n".join(L + [f"Not computable: {rep['why_not_computable']}"]) + "\n"
    if rep.get("warning"):
        L += [f"WARNING: {rep['warning']}", ""]
    sh = rep["share_inside_us_hours"]
    L += ["Asks inside US working hours: Desktop " + ", ".join(
        f"round {k} {common.pct(v['share_inside'])}%" for k, v in sh["desktop_by_round"].items())
          + ". Command line " + ", ".join(f"pass {k} {common.pct(v['share_inside'])}%" for k, v in sh["cli_by_pass"].items()), ""]
    for metric, r in rep["metrics"].items():
        unit = "points" if r["effect"] == "diff" else "per cent"
        L.append(f"## {r['name']}")
        if r.get("wording") is None:
            L += [f"- not computable: {r.get('why')}", ""]
            continue
        L += [f"- Desktop minus command line: {common.pct(r['diff_shown'])} {unit} on {r['items']} items "
              f"(95% range {common.pct(r['range_95_shown'][0])} to {common.pct(r['range_95_shown'][1])})",
              f"- p = {r['p']:.4f} over {r['sign_flips']} sign flips",
              "- each Desktop round against the mean of the command line passes: " + ", ".join(
                  f"round {k} {common.pct(x.get('shown'))}" + ("" if x["counts_for_sign"] else " (not in the sign check)")
                  for k, x in r["rounds"].items()),
              f"- size enough: {r['big_enough']}, same sign in every round: {r['same_sign_every_round']}",
              f"- wording: {r['wording_name']}"
              + (f" (no difference larger than {common.pct(r['not_larger_than'])} {unit} was seen)"
                 if r["wording"] == 3 else ""), ""]
    aw = rep["accuracy_wording"]
    L += [f"Accuracy, both ways of counting together: {aw['wording_name']} ({aw.get('note')})",
          f"Thinking: {rep['thinking_wording']['wording_name']}"]
    if aw.get("wording") == 1 or rep["thinking_wording"].get("wording") == 1:
        L += ["", "Clear: the causes this run cannot tell apart:"] + [f"- {x}" for x in rep["causes_to_list_if_clear"]]
        L += [f"A test that would tell them apart: {rep['test_that_would_tell_them_apart']}."]
    return "\n".join(L) + "\n"


def write_outputs(rep: dict, desktop_graded: list[dict], out: Path) -> None:
    from ccversions import grade

    out.mkdir(parents=True, exist_ok=True)
    grade.write_outputs(desktop_graded, out / "graded")
    common.write_json(out / "report.json", rep)
    (out / "report.md").write_text(report_text(rep))
    units = sorted({u for r in rep["metrics"].values() for u in (r.get("per_item") or {})})
    cols = ["unit"] + [f"{m}_{k}" for m, _, _ in common.METRICS for k in ("desktop", "cli", "diff")]
    with open(out / "per_item.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for u in units:
            row = {"unit": u}
            for m, _, _ in common.METRICS:
                x = (rep["metrics"][m].get("per_item") or {}).get(u) or {}
                for k in ("desktop", "cli", "diff"):
                    row[f"{m}_{k}"] = x.get(k)
            w.writerow(row)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--graded", action="append", help="a graded.jsonl of the run (default: every one under 正式跑/graded)")
    ap.add_argument("--desktop-asks", help=f"default: {common.DESKTOP_ASKS}")
    ap.add_argument("--versions-file", help="default: the versions file the settings name")
    ap.add_argument("--settings", help=f"default: {common.SETTINGS_FILE}")
    ap.add_argument("--out", help=f"default: {common.OUT_DEFAULT}")
    ap.add_argument("--version", default=VERSION, help="the version the Desktop app ran")
    ap.add_argument("--shuffles", type=int, default=common.SHUFFLES)
    ap.add_argument("--draws", type=int, default=common.DRAWS)
    ap.add_argument("--allow-unfinished", action="store_true",
                    help="read the run's graded rows although its final step has not run")
    ap.add_argument("--allow-partial-round3", action="store_true",
                    help="go on although round 3 has some asks but not all")
    args = ap.parse_args(argv)
    if args.graded:
        files = [Path(x) for x in args.graded]
    else:
        if not common.formal_finished() and not args.allow_unfinished:
            print(f"not run: {common.FORMAL_FINAL_REPORT} does not exist yet, so the registered run has not graded "
                  "all its passes. Start again when it has, or give --allow-unfinished.")
            return 2
        files = common.default_graded_files()
    if not files:
        print("not run: no graded.jsonl found")
        return 2
    records = load_records(Path(args.desktop_asks) if args.desktop_asks else common.DESKTOP_ASKS)
    kept, left = pick(records, args.version)
    problem = rounds_problem(kept)
    if problem and not args.allow_partial_round3:
        print(f"not run: {problem}")
        return 2
    settings_file = Path(args.settings) if args.settings else None
    graded = grade_records(kept, settings_file)
    versions = common.load_versions(settings_file, Path(args.versions_file) if args.versions_file else None)
    rep = analyse(analyze.load_rows(files), graded, versions, version=args.version, shuffles=args.shuffles,
                  draws=args.draws)
    rep["graded_files"] = [str(f) for f in files]
    rep["desktop_records"] = {"read": len(records), "kept": len(kept), "left_out": left,
                              "partial_round3_allowed": bool(problem)}
    out = Path(args.out) if args.out else common.OUT_DEFAULT
    write_outputs(rep, graded, out / "desktop")
    print(f"written: {out / 'desktop'}")
    if rep.get("why_not_computable"):
        print(f"not computable: {rep['why_not_computable']}")
    else:
        print(f"accuracy: {rep['accuracy_wording']['wording_name']}, thinking: {rep['thinking_wording']['wording_name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
